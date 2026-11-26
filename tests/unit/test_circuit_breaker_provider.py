"""Tests for CircuitBreakerProvider wrapper."""
from __future__ import annotations

import pytest

from case_core.contracts.llm import DecodingParameters, LLMRequest, LLMResponse
from case_core.ports.llm import LLMProvider
from case_core.providers.circuit_breaker import CircuitBreakerProvider


class FakeProvider(LLMProvider):
    def __init__(self, name: str = "fake", model: str = "fake-model") -> None:
        self._name = name
        self._model = model
        self._call_count = 0
        self._should_fail = False
        self._fail_exception: Exception = ConnectionError("provider down")

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self._call_count += 1
        if self._should_fail:
            raise self._fail_exception
        return LLMResponse(
            raw_output="ok",
            model=self._model,
            provider=self._name,
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            latency_ms=10.0,
            finish_reason="stop",
        )

    async def health_check(self) -> bool:
        return not self._should_fail


def _make_request() -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": "hi"}],
        response_schema={"type": "object"},
        decoding_parameters=DecodingParameters(),
    )


class TestCircuitBreakerProvider:
    def test_name(self) -> None:
        provider = FakeProvider(name="groq")
        cb = CircuitBreakerProvider(provider)
        assert cb.name == "groq_circuit_breaker"

    def test_model(self) -> None:
        provider = FakeProvider(model="test-model")
        cb = CircuitBreakerProvider(provider)
        assert cb.model == "test-model"

    async def test_success_passes_through(self) -> None:
        provider = FakeProvider()
        cb = CircuitBreakerProvider(provider)
        request = _make_request()
        response = await cb.complete(request)
        assert response.raw_output == "ok"
        assert provider._call_count == 1

    async def test_failure_increments_count(self) -> None:
        provider = FakeProvider()
        provider._should_fail = True
        cb = CircuitBreakerProvider(provider, failure_threshold=3)
        request = _make_request()

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.complete(request)

        state = cb.get_state()
        assert state["failure_count"] == 2
        assert state["is_open"] is False

    async def test_opens_after_threshold(self) -> None:
        provider = FakeProvider()
        provider._should_fail = True
        cb = CircuitBreakerProvider(provider, failure_threshold=3)
        request = _make_request()

        for _ in range(3):
            with pytest.raises(ConnectionError):
                await cb.complete(request)

        state = cb.get_state()
        assert state["is_open"] is True

    async def test_blocks_when_open(self) -> None:
        provider = FakeProvider()
        provider._should_fail = True
        cb = CircuitBreakerProvider(provider, failure_threshold=2, recovery_timeout_seconds=60)
        request = _make_request()

        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.complete(request)

        provider._should_fail = False
        with pytest.raises(ConnectionError, match="Circuit breaker open"):
            await cb.complete(request)

    async def test_recovery_after_timeout(self) -> None:
        provider = FakeProvider()
        cb = CircuitBreakerProvider(provider, failure_threshold=2, recovery_timeout_seconds=0)
        request = _make_request()

        provider._should_fail = True
        for _ in range(2):
            with pytest.raises(ConnectionError):
                await cb.complete(request)

        assert cb.get_state()["is_open"] is True

        provider._should_fail = False
        response = await cb.complete(request)
        assert response.raw_output == "ok"
        assert cb.get_state()["is_open"] is False

    async def test_success_resets_failure_count(self) -> None:
        provider = FakeProvider()
        cb = CircuitBreakerProvider(provider, failure_threshold=5)
        request = _make_request()

        provider._should_fail = True
        with pytest.raises(ConnectionError):
            await cb.complete(request)
        with pytest.raises(ConnectionError):
            await cb.complete(request)

        provider._should_fail = False
        await cb.complete(request)

        state = cb.get_state()
        assert state["failure_count"] == 0
        assert state["is_open"] is False

    async def test_health_check_delegates(self) -> None:
        provider = FakeProvider()
        cb = CircuitBreakerProvider(provider)
        assert await cb.health_check() is True

        provider._should_fail = False
        provider._should_fail = True
        assert await cb.health_check() is False

    async def test_get_state_includes_provider_info(self) -> None:
        provider = FakeProvider(name="groq")
        cb = CircuitBreakerProvider(provider, recovery_timeout_seconds=30)
        state = cb.get_state()
        assert state["provider"] == "groq"
        assert state["recovery_timeout"] == 30
        assert "recovery_remaining" in state

    async def test_exception_propagation(self) -> None:
        provider = FakeProvider()
        provider._should_fail = True
        provider._fail_exception = ValueError("custom error")
        cb = CircuitBreakerProvider(provider, failure_threshold=10)
        request = _make_request()

        with pytest.raises(ValueError, match="custom error"):
            await cb.complete(request)
