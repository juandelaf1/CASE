"""Live provider integration test for GroqProvider.

Requires: CASE_GROQ_API_KEY environment variable.
Skipped automatically when not configured.

This test exercises the full CASE pipeline with a real LLM provider.
It is intentionally separated from deterministic unit tests.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import time

import pytest

sys.path.insert(0, "src")

GROQ_API_KEY = os.environ.get("CASE_GROQ_API_KEY", "")
REQUIRES_GROQ = pytest.mark.skipif(
    not GROQ_API_KEY,
    reason="CASE_GROQ_API_KEY not set — skipping live provider test",
)


@pytest.fixture
def groq_provider():
    from case_core.providers.groq import GroqProvider

    return GroqProvider(api_key=GROQ_API_KEY)


@pytest.fixture
def case_engine():
    from case_core.composition import create_app_dependencies

    os.environ["CASE_PROVIDER"] = "groq"
    deps = create_app_dependencies()
    os.environ.pop("CASE_PROVIDER", None)
    return deps.engine


@REQUIRES_GROQ
class TestGroqLiveHealthCheck:
    @pytest.mark.asyncio
    async def test_health_check(self, groq_provider):
        healthy = await groq_provider.health_check()
        assert healthy is True

    def test_provider_identity(self, groq_provider):
        assert groq_provider.name == "groq"
        assert groq_provider.model == "qwen/qwen3.8-27b"


@REQUIRES_GROQ
class TestGroqLiveComplete:
    @pytest.mark.asyncio
    async def test_basic_completion(self, groq_provider):
        from case_core.contracts.llm import DecodingParameters, LLMRequest

        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a JSON assistant. Return only valid JSON."},
                {"role": "user", "content": 'Return: {"status": "ok", "value": 42}'},
            ],
            response_schema={},
            decoding_parameters=DecodingParameters(temperature=0.0, max_tokens=100),
        )

        response = await groq_provider.complete(request)

        assert response.raw_output != ""
        assert response.provider == "groq"
        assert response.model == "qwen/qwen3.8-27b"
        assert response.latency_ms > 0
        assert response.finish_reason == "stop"
        assert response.usage.total_tokens > 0

    @pytest.mark.asyncio
    async def test_structured_output(self, groq_provider):
        from case_core.contracts.llm import DecodingParameters, LLMRequest

        schema = {
            "type": "object",
            "properties": {
                "decision": {"type": "string", "enum": ["approve", "reject", "escalate"]},
                "reason": {"type": "string"},
                "urgency": {"type": "string", "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"]},
                "confidence": {"type": "number"},
                "evidence_summary": {"type": "string"},
            },
            "required": ["decision", "reason", "urgency", "confidence", "evidence_summary"],
        }

        request = LLMRequest(
            messages=[
                {"role": "system", "content": "You are a CASE triage assistant. Analyze the case and return a structured decision."},
                {"role": "user", "content": "Minor pothole on Main St. Photo evidence attached. Urgency: LOW."},
            ],
            response_schema=schema,
            decoding_parameters=DecodingParameters(temperature=0.0, max_tokens=200),
        )

        response = await groq_provider.complete(request)

        assert response.raw_output != ""
        assert response.finish_reason == "stop"
        assert response.parsed is not None
        assert "decision" in response.parsed
        assert response.parsed["decision"] in ["approve", "reject", "escalate"]
        assert "reason" in response.parsed
        assert "urgency" in response.parsed
        assert isinstance(response.parsed["confidence"], (int, float))


@REQUIRES_GROQ
class TestGroqLivePipeline:
    @pytest.mark.asyncio
    async def test_triage_moderate_case(self, case_engine):
        from case_core.contracts.operational_case import OperationalCase

        case = OperationalCase(
            case_id="LIVE-TEST-001",
            report_text="Minor pothole on Main St. Photo evidence confirms small pothole.",
            domain="urban_operations",
            urgency="LOW",
            evidence=[
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Photo confirms small pothole",
                    "source": "test",
                    "confidence": 0.9,
                    "extracted_at": "2026-09-15T00:00:00Z",
                }
            ],
        )

        result = await case_engine.execute(case)

        assert result.decision is not None
        assert result.decision.action in ["approve", "reject", "escalate"]
        assert result.decision.urgency in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
        assert 0 <= result.decision.confidence <= 1
        assert result.decision.processing_time_ms is not None
        assert result.decision.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_triage_critical_case(self, case_engine):
        from case_core.contracts.operational_case import OperationalCase

        case = OperationalCase(
            case_id="LIVE-TEST-002",
            report_text="Structural crack on bridge over highway. Emergency inspection needed.",
            domain="urban_operations",
            urgency="CRITICAL",
            evidence=[
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Inspection report flags load-bearing concern",
                    "source": "inspection",
                    "confidence": 0.95,
                    "extracted_at": "2026-09-15T00:00:00Z",
                }
            ],
        )

        result = await case_engine.execute(case)

        assert result.decision is not None
        assert result.decision.action in ["approve", "reject", "escalate"]
        assert result.decision.processing_time_ms > 0

    @pytest.mark.asyncio
    async def test_triage_no_evidence_rejects(self, case_engine):
        from case_core.contracts.operational_case import OperationalCase

        case = OperationalCase(
            case_id="LIVE-TEST-003",
            report_text="Illegal dumping reported in alley.",
            domain="urban_operations",
            urgency="LOW",
            evidence=[],
        )

        result = await case_engine.execute(case)

        assert result.decision is None
        assert result.error is not None
        assert "domain_validation" in result.error.category.value
        assert result.processing_lifecycle.value == "terminal_failure"
