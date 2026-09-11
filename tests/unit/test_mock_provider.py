import asyncio
import json
import sys

import pytest

sys.path.insert(0, "src")

from case_core.contracts.llm import DecodingParameters, LLMRequest
from case_core.providers.mock import TEST_MOCK_RESPONSES, MockProvider


def _make_request(text: str = "test") -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": text}],
        response_schema={"type": "object"},
        decoding_parameters=DecodingParameters(temperature=0.0),
    )


class TestMockProviderInterface:
    def test_implements_llm_provider(self):
        from case_core.ports.llm import LLMProvider
        assert issubclass(MockProvider, LLMProvider)

    def test_name_and_model(self):
        p = MockProvider()
        assert p.name == "mock"
        assert p.model == "mock-v1"


class TestMockProviderDeterminism:
    def test_same_input_same_output(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: test case")
        r1 = asyncio.run(p.complete(req))
        r2 = asyncio.run(p.complete(req))
        assert r1.raw_output == r2.raw_output
        assert r1.usage.total_tokens == r2.usage.total_tokens

    def test_different_inputs_different_outputs(self):
        p = MockProvider()
        r1 = asyncio.run(p.complete(_make_request("TEST-MOCK-01")))
        r2 = asyncio.run(p.complete(_make_request("TEST-MOCK-02")))
        d1 = json.loads(r1.raw_output)
        d2 = json.loads(r2.raw_output)
        assert d1["decision"] != d2["decision"]


class TestMockProviderScenarios:
    @pytest.mark.parametrize("mock_id", list(TEST_MOCK_RESPONSES.keys()))
    def test_all_mock_scenarios_return_valid_json(self, mock_id: str):
        p = MockProvider()
        req = _make_request(f"{mock_id}: test case")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed is not None
        assert "decision" in resp.parsed
        assert "reason" in resp.parsed
        assert "urgency" in resp.parsed
        assert "confidence" in resp.parsed
        assert "evidence_summary" in resp.parsed
        assert resp.parsed["decision"] in ["approve", "reject", "escalate"]

    def test_mock_01_approve(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: standard case")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed["decision"] == "approve"
        assert resp.parsed["urgency"] == "MEDIUM"

    def test_mock_02_reject(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-02: insufficient evidence")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed["decision"] == "reject"

    def test_mock_03_escalate(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-03: high urgency")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed["decision"] == "escalate"
        assert resp.parsed["urgency"] == "HIGH"


class TestMockProviderInvalidResponses:
    def test_invalid_json(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-INVALID-JSON: test")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed is None
        assert resp.finish_reason == "error"

    def test_invalid_schema(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-INVALID-SCHEMA: test")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed is None
        assert resp.finish_reason == "error"

    def test_rate_limit_raises_timeout(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-RATE-LIMIT: test")
        with pytest.raises(TimeoutError):
            asyncio.run(p.complete(req))


class TestMockProviderHealth:
    def test_health_check_returns_true(self):
        p = MockProvider()
        assert asyncio.run(p.health_check()) is True


class TestMockProviderResponseFormat:
    def test_response_has_raw_output(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: test")
        resp = asyncio.run(p.complete(req))
        assert resp.raw_output is not None
        assert isinstance(resp.raw_output, str)

    def test_response_has_parsed(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: test")
        resp = asyncio.run(p.complete(req))
        assert resp.parsed is not None
        assert isinstance(resp.parsed, dict)

    def test_response_has_provider(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: test")
        resp = asyncio.run(p.complete(req))
        assert resp.provider == "mock"

    def test_response_has_latency_ms(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: test")
        resp = asyncio.run(p.complete(req))
        assert resp.latency_ms >= 0

    def test_finish_reason_is_stop(self):
        p = MockProvider()
        req = _make_request("TEST-MOCK-01: test")
        resp = asyncio.run(p.complete(req))
        assert resp.finish_reason == "stop"
