import sys

import pytest

sys.path.insert(0, "src")

from case_core.contracts.llm import DecodingParameters, LLMRequest
from case_core.ports.llm import LLMProvider
from case_core.providers.ollama import OllamaProvider


def _make_request(text: str = "test") -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": text}],
        response_schema={
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["approve", "reject", "escalate"]},
            },
            "required": ["decision"],
        },
        decoding_parameters=DecodingParameters(temperature=0.0, max_tokens=256),
    )


class TestOllamaProviderContract:
    def test_implements_llm_provider(self):
        assert issubclass(OllamaProvider, LLMProvider)

    def test_name(self):
        p = OllamaProvider()
        assert p.name == "ollama"

    def test_model_default(self):
        p = OllamaProvider()
        assert p.model == "llama3.2"

    def test_model_custom(self):
        p = OllamaProvider(model="mistral")
        assert p.model == "mistral"

    def test_base_url_custom(self):
        p = OllamaProvider(base_url="http://custom:8080")
        assert p._base_url == "http://custom:8080"


class TestOllamaProviderErrorMapping:
    @pytest.mark.asyncio
    async def test_timeout_returns_timeout_response(self):
        p = OllamaProvider(base_url="http://localhost:19999", timeout_seconds=0.1)
        req = _make_request()
        resp = await p.complete(req)
        assert resp.finish_reason == "timeout"
        assert resp.parsed is None
        assert resp.provider == "ollama"

    @pytest.mark.asyncio
    async def test_connection_error_returns_unavailable(self):
        p = OllamaProvider(base_url="http://localhost:19999")
        req = _make_request()
        resp = await p.complete(req)
        assert resp.finish_reason == "provider_unavailable"
        assert resp.parsed is None

    @pytest.mark.asyncio
    async def test_health_check_returns_false_when_unavailable(self):
        p = OllamaProvider(base_url="http://localhost:19999")
        result = await p.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_get_model_info_returns_none_when_unavailable(self):
        p = OllamaProvider(base_url="http://localhost:19999")
        result = await p.get_model_info()
        assert result is None

    @pytest.mark.asyncio
    async def test_timeout_response_has_latency(self):
        p = OllamaProvider(base_url="http://localhost:19999", timeout_seconds=0.1)
        req = _make_request()
        resp = await p.complete(req)
        assert resp.latency_ms >= 0

    @pytest.mark.asyncio
    async def test_timeout_response_has_metadata(self):
        p = OllamaProvider(base_url="http://localhost:19999", timeout_seconds=0.1)
        req = _make_request()
        resp = await p.complete(req)
        assert "error" in resp.metadata


class TestOllamaProviderResponseFormat:
    @pytest.mark.asyncio
    async def test_response_fields_present(self):
        p = OllamaProvider(base_url="http://localhost:19999", timeout_seconds=0.1)
        req = _make_request()
        resp = await p.complete(req)
        assert hasattr(resp, "raw_output")
        assert hasattr(resp, "parsed")
        assert hasattr(resp, "usage")
        assert hasattr(resp, "model")
        assert hasattr(resp, "provider")
        assert hasattr(resp, "latency_ms")
        assert hasattr(resp, "finish_reason")
        assert hasattr(resp, "metadata")

    @pytest.mark.asyncio
    async def test_no_domain_policy_in_request(self):
        req = _make_request()
        assert not hasattr(req, "domain_policy")
