"""Circuit breaker wrapper for LLM providers.

Adds fault tolerance to provider calls without modifying provider implementations.
"""
from __future__ import annotations

import time
from typing import Any

from case_core.contracts.llm import LLMRequest, LLMResponse
from case_core.ports.llm import LLMProvider
from case_core.production import CircuitBreaker


class CircuitBreakerProvider(LLMProvider):
    """Wrapper that adds circuit breaker to any LLMProvider."""

    def __init__(
        self,
        provider: LLMProvider,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 30,
    ) -> None:
        self._provider = provider
        self._circuit = CircuitBreaker(
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout_seconds,
        )
        self._last_failure_time: float = 0.0

    @property
    def name(self) -> str:
        return f"{self._provider.name}_circuit_breaker"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if self._circuit.is_open():
            if not self._recovery_expired():
                raise ConnectionError(
                    f"Circuit breaker open for {self._provider.name}. "
                    f"Recovery in {self._recovery_remaining():.0f}s"
                )
            self._circuit._is_open = False
            self._circuit._failure_count = 0

        try:
            response = await self._provider.complete(request)
            self._circuit.record_success()
            return response
        except Exception:
            self._circuit.record_failure()
            self._last_failure_time = time.time()
            raise

    def _recovery_expired(self) -> bool:
        if self._last_failure_time == 0:
            return True
        elapsed = time.time() - self._last_failure_time
        return elapsed >= self._circuit.recovery_timeout

    def _recovery_remaining(self) -> float:
        if self._last_failure_time == 0:
            return 0.0
        elapsed = time.time() - self._last_failure_time
        remaining = self._circuit.recovery_timeout - elapsed
        return max(0.0, remaining)

    def get_state(self) -> dict[str, Any]:
        state = self._circuit.get_state()
        state["provider"] = self._provider.name
        state["recovery_timeout"] = self._circuit.recovery_timeout
        state["recovery_remaining"] = self._recovery_remaining()
        return state
