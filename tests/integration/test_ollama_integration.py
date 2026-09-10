import asyncio
import json
import sys

import httpx
import pytest

sys.path.insert(0, "src")

from case_core.contracts.llm import DecodingParameters, LLMRequest
from case_core.providers.ollama import OllamaProvider


OLLAMA_AVAILABLE = False
try:
    r = httpx.get("http://localhost:11434/api/tags", timeout=2.0)
    OLLAMA_AVAILABLE = r.status_code == 200
except Exception:
    OLLAMA_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not OLLAMA_AVAILABLE,
    reason="Ollama server not available at localhost:11434",
)


def _make_request(text: str = "test") -> LLMRequest:
    return LLMRequest(
        messages=[{"role": "user", "content": text}],
        response_schema={
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["approve", "reject", "escalate"]},
                "reason": {"type": "string"},
                "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "confidence": {"type": "number"},
                "evidence_summary": {"type": "string"},
            },
            "required": ["decision", "reason", "urgency", "confidence", "evidence_summary"],
        },
        decoding_parameters=DecodingParameters(temperature=0.0, max_tokens=512),
    )


@pytest.mark.integration
class TestOllamaIntegration:
    @pytest.mark.asyncio
    async def test_health_check(self):
        p = OllamaProvider()
        result = await p.health_check()
        assert result is True

    @pytest.mark.asyncio
    async def test_get_model_info(self):
        p = OllamaProvider()
        info = await p.get_model_info()
        assert info is not None
        assert "modelfile" in info or "details" in info

    @pytest.mark.asyncio
    async def test_complete_returns_valid_response(self):
        p = OllamaProvider()
        req = _make_request("Respond with a JSON object: {\"decision\": \"approve\"}")
        resp = await p.complete(req)
        assert resp.raw_output is not None
        assert resp.provider == "ollama"
        assert resp.latency_ms >= 0
        assert resp.usage.total_tokens >= 0

    @pytest.mark.asyncio
    async def test_complete_parsed_json(self):
        p = OllamaProvider()
        req = _make_request("Respond ONLY with this JSON: {\"decision\": \"approve\", \"reason\": \"test\", \"urgency\": \"LOW\", \"confidence\": 0.9, \"evidence_summary\": \"test\"}")
        resp = await p.complete(req)
        if resp.parsed is not None:
            assert "decision" in resp.parsed

    @pytest.mark.asyncio
    async def test_usage_metadata(self):
        p = OllamaProvider()
        req = _make_request("Hello")
        resp = await p.complete(req)
        assert resp.usage.prompt_tokens >= 0
        assert resp.usage.completion_tokens >= 0
        assert resp.usage.total_tokens == resp.usage.prompt_tokens + resp.usage.completion_tokens

    @pytest.mark.asyncio
    async def test_finish_reason_stop(self):
        p = OllamaProvider()
        req = _make_request("Say hello")
        resp = await p.complete(req)
        assert resp.finish_reason in ["stop", "length"]

    @pytest.mark.asyncio
    async def test_metadata_fields(self):
        p = OllamaProvider()
        req = _make_request("Test")
        resp = await p.complete(req)
        assert "total_duration_ns" in resp.metadata
        assert "done" in resp.metadata