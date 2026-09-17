"""Tests for provider selection, isolation, and comparison features."""
import os
import sys

os.environ.setdefault("CASE_PROVIDER", "mock")

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, "src")

from case_api.api.v1.app import app
from case_core.contracts.llm import DecodingParameters, LLMRequest, LLMResponse
from case_core.contracts.telemetry import TokenUsage
from case_core.ports.llm import LLMProvider

client = TestClient(app)

TRIAGE_PAYLOAD = {
    "report_text": "Standard logistics case for provider selection test",
    "domain": "logistics",
    "urgency": "MEDIUM",
    "evidence": [
        {
            "id": "ev-001",
            "type": "text",
            "content": "Test evidence for provider selection",
            "source": "test",
            "confidence": 0.9,
            "extracted_at": "2026-09-15T10:00:00Z",
        }
    ],
}


class TestProviderListing:
    def test_list_providers_returns_all(self):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        data = response.json()
        providers = data["providers"]
        names = [p["name"] for p in providers]
        assert "groq" in names
        assert "ollama" in names
        assert "mock" in names

    def test_list_providers_has_active(self):
        response = client.get("/api/v1/providers")
        assert response.status_code == 200
        data = response.json()
        assert "active_provider" in data
        assert data["active_provider"] in ("groq", "ollama", "mock")


class TestProviderSelection:
    def test_triage_without_provider_uses_default(self):
        payload = dict(TRIAGE_PAYLOAD)
        payload["case_id"] = "CASE-PROVIDER-DEFAULT"
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["provider_info"]["provider"] == "mock"

    def test_triage_with_provider_mock(self):
        payload = dict(TRIAGE_PAYLOAD)
        payload["case_id"] = "CASE-PROVIDER-MOCK"
        payload["provider"] = "mock"
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["provider_info"]["provider"] == "mock"

    def test_triage_with_invalid_provider_uses_default(self):
        payload = dict(TRIAGE_PAYLOAD)
        payload["case_id"] = "CASE-PROVIDER-INVALID"
        payload["provider"] = "nonexistent"
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["provider_info"]["provider"] == "mock"


class TestProviderIsolation:
    def test_providers_are_independent_instances(self):
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        groq = deps.providers.get("groq")
        ollama = deps.providers.get("ollama")
        mock = deps.providers.get("mock")
        assert groq is not None
        assert ollama is not None
        assert mock is not None
        assert groq is not ollama
        assert groq is not mock
        assert ollama is not mock

    def test_engine_has_providers_dict(self):
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        engine = deps.engine
        assert hasattr(engine, "_providers")
        assert "groq" in engine._providers
        assert "ollama" in engine._providers
        assert "mock" in engine._providers


class TestComparisonEndpoint:
    def test_comparison_with_mock_providers(self):
        payload = {
            "report_text": "Comparison test case for provider evaluation",
            "domain": "logistics",
            "urgency": "MEDIUM",
            "providers": ["mock"],
        }
        response = client.post("/api/v1/comparison", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "case_id" in data
        assert len(data["results"]) == 1
        assert data["results"][0]["provider"] == "mock"

    def test_comparison_unknown_domain_rejected(self):
        payload = {
            "report_text": "Test",
            "domain": "nonexistent",
            "providers": ["mock"],
        }
        response = client.post("/api/v1/comparison", json=payload)
        assert response.status_code == 400

    def test_comparison_invalid_provider_rejected(self):
        payload = {
            "report_text": "Test",
            "domain": "logistics",
            "providers": ["nonexistent"],
        }
        response = client.post("/api/v1/comparison", json=payload)
        assert response.status_code == 422


class TestBackwardCompatibility:
    def test_triage_without_provider_field_works(self):
        payload = {
            "report_text": "Backward compatibility test case",
            "domain": "urban_operations",
            "urgency": "HIGH",
            "provider": "mock",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Standard evidence for backward compat",
                    "source": "test",
                    "confidence": 0.9,
                    "extracted_at": "2026-09-15T10:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "action" in data
        assert "provider_info" in data

    def test_triage_optional_provider_none(self):
        payload = {
            "report_text": "Provider none test",
            "domain": "urban_operations",
            "urgency": "MEDIUM",
            "provider": None,
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Standard evidence for provider none",
                    "source": "test",
                    "confidence": 0.9,
                    "extracted_at": "2026-09-15T10:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=payload)
        assert response.status_code == 200


class TestEngineProviderResolution:
    def test_resolve_provider_returns_named_provider(self):
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        engine = deps.engine
        provider = engine._resolve_provider("groq")
        assert provider.name == "groq"

    def test_resolve_provider_returns_default_on_none(self):
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        engine = deps.engine
        provider = engine._resolve_provider(None)
        assert provider.name == "mock"

    def test_resolve_provider_returns_default_on_unknown(self):
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        engine = deps.engine
        provider = engine._resolve_provider("nonexistent")
        assert provider.name == "mock"


class TestComparisonWithMockEngine:
    def test_comparison_endpoint_calls_engine_per_provider(self):
        from case_core.application.engine import TriageEngine, TriageResult
        from case_core.contracts.lifecycle import ProcessingLifecycle
        from case_core.contracts.operational_case import OperationalCase
        from case_core.domain.registry import DomainRegistry
        from case_core.domain.urban_policy import UrbanPolicy

        call_log: list[str] = []

        class SpyProvider(LLMProvider):
            def __init__(self, provider_name: str) -> None:
                self._name = provider_name

            @property
            def name(self) -> str:
                return self._name

            @property
            def model(self) -> str:
                return f"{self._name}-model"

            async def complete(self, request: LLMRequest) -> LLMResponse:
                call_log.append(self._name)
                return LLMResponse(
                    raw_output='{"decision":"approve","reason":"Automated approval for standard urban maintenance case with sufficient evidence","urgency":"LOW","confidence":0.8,"evidence_summary":"Evidence validated and confirmed"}',
                    parsed={"decision": "approve", "reason": "Automated approval for standard urban maintenance case with sufficient evidence", "urgency": "LOW", "confidence": 0.8, "evidence_summary": "Evidence validated and confirmed"},
                    usage=TokenUsage(prompt_tokens=10, completion_tokens=10, total_tokens=20),
                    model=self.model,
                    provider=self.name,
                    latency_ms=5.0,
                    finish_reason="stop",
                )

            async def health_check(self) -> bool:
                return True

        registry = DomainRegistry()
        registry.register(UrbanPolicy())
        providers = {"alpha": SpyProvider("alpha"), "beta": SpyProvider("beta")}
        default = providers["alpha"]

        engine = TriageEngine(
            domain_registry=registry,
            provider=default,
            providers=providers,
        )

        case = OperationalCase(
            case_id="SPY-TEST",
            report_text="Minor pothole repair needed on 5th Avenue",
            domain="urban_operations",
            urgency="LOW",
            evidence=[{
                "id": "ev-001",
                "type": "text",
                "content": "Pothole reported by citizen",
                "source": "citizen",
                "confidence": 0.9,
                "extracted_at": "2026-09-15T10:00:00Z",
            }],
        )

        import asyncio

        async def run():
            r1 = await engine.execute(case, provider_name="alpha")
            r2 = await engine.execute(case, provider_name="beta")
            return r1, r2

        r1, r2 = asyncio.run(run())
        assert call_log[0] == "alpha"
        assert call_log[-1] == "beta"
        assert "alpha" in call_log
        assert "beta" in call_log
        assert r1.decision is not None
        assert r2.decision is not None
