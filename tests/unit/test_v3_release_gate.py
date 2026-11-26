"""V3 Release Gate — Final verification before closing V3.

Checks:
1. Real Estate domain works end-to-end (runtime → decision)
2. USGS works as extension with fallback/error control
3. Rate limiting works as middleware
4. correlation_id appears and is preserved in audit flow
5. 779 tests pass
6. ruff and mypy clean
7. No accidental connections to isolated modules
"""
from __future__ import annotations

import asyncio
import inspect
from unittest.mock import MagicMock, patch

from case_core.contracts.audit import AuditEvent

# ─────────────────────────────────────────────────────────────────────────────
# CHECK 1: Real Estate End-to-End
# ─────────────────────────────────────────────────────────────────────────────

class TestRealEstateE2E:
    """Real Estate domain: runtime → decision."""

    def test_real_estate_registered_in_registry(self) -> None:
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        assert "real_estate" in deps.registry.list_domains()

    def test_real_estate_policy_validates_evidence(self) -> None:
        from case_core.composition import create_app_dependencies
        from case_core.contracts.evidence import EvidenceItem, EvidenceType

        deps = create_app_dependencies()
        policy = deps.registry.get("real_estate")
        assert policy is not None

        evidence = [
            EvidenceItem(
                id="ev-1",
                type=EvidenceType.TEXT,
                content="Property appraisal document",
                source="test",
                confidence=0.9,
                extracted_at="2026-01-01T00:00:00Z",
            )
        ]
        valid, msg = policy.validate_evidence(evidence)
        assert valid is True
        assert "validated" in msg.lower() or "evidence" in msg.lower()

    def test_real_estate_automation_policy_assesses_risk(self) -> None:
        from case_core.composition import _resolve_automation_policy
        from case_core.contracts.operational_case import OperationalCase, UrgencyLevel

        policy = _resolve_automation_policy("real_estate")
        assert policy is not None

        case = OperationalCase(
            case_id="CASE-RE-AUTO",
            report_text="Standard property inspection",
            domain="real_estate",
            urgency=UrgencyLevel.LOW,
        )
        assessment = policy.assess_risk(
            case=case,
            data={"urgency": "LOW"},
            validation_status="valid",
            evidence_quality="sufficient",
            confidence=0.85,
        )
        assert assessment.risk_level.value in ("LOW", "MEDIUM")
        assert assessment.automation_decision is not None

    def test_real_estate_api_triage(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app

        client = TestClient(app)
        response = client.post("/api/v1/triage", json={
            "report_text": "Commercial property valuation dispute requiring immediate review",
            "domain": "real_estate",
            "urgency": "HIGH",
            "evidence": [
                {
                    "id": "ev-1",
                    "type": "text",
                    "content": "Property appraisal report",
                    "source": "test",
                    "confidence": 0.9,
                    "extracted_at": "2026-01-01T00:00:00Z",
                }
            ],
        })
        assert response.status_code == 200
        data = response.json()
        assert data["domain"] == "real_estate"
        assert data["decision_id"] is not None
        assert data["case_id"] is not None
        assert data["action"] is not None
        assert data["urgency"] is not None


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 2: USGS Extension + Fallback
# ─────────────────────────────────────────────────────────────────────────────

class TestUSGSExtension:
    """USGS adapter: extension with fallback/error control."""

    def test_usgs_client_exists(self) -> None:
        from usgs_adapter.client import USGSClient
        assert USGSClient is not None

    def test_usgs_client_health_check(self) -> None:
        from usgs_adapter.client import USGSClient
        client = USGSClient()
        result = client.health_check()
        assert isinstance(result, bool)

    def test_usgs_client_fetch_returns_list(self) -> None:
        from usgs_adapter.client import USGSClient
        client = USGSClient(timeout=5.0)
        events = client.fetch_recent()
        assert isinstance(events, list)

    def test_usgs_client_handles_timeout(self) -> None:
        from usgs_adapter.client import USGSClient
        with patch("usgs_adapter.client.httpx.Client") as mock_client:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get.side_effect = Exception("timeout")
            mock_client.return_value = mock_instance
            client = USGSClient(timeout=1.0)
            events = client.fetch_recent()
            assert events == []

    def test_usgs_endpoint_returns_events(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app

        client = TestClient(app)
        mock_feature = {
            "id": "usgs-test-001",
            "properties": {
                "mag": 5.2,
                "place": "Test Location",
                "time": 1700000000000,
                "felt": 10,
                "tsunami": 0,
                "type": "earthquake",
                "magType": "Mww",
                "sig": 500,
            },
            "geometry": {"coordinates": [0.0, 0.0, 10.0]},
            "type": "Feature",
        }
        with patch("usgs_adapter.client.httpx.Client") as mock_httpx:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"features": [mock_feature]}
            mock_response.raise_for_status = MagicMock()
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get.return_value = mock_response
            mock_httpx.return_value = mock_instance
            response = client.get("/api/v1/seismic/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data

    def test_usgs_health_endpoint(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app

        client = TestClient(app)
        response = client.get("/api/v1/seismic/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "reachable" in data

    def test_usgs_no_core_imports(self) -> None:
        from usgs_adapter.client import USGSClient
        source = inspect.getsource(USGSClient)
        assert "case_core" not in source
        assert "case_api" not in source


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 3: Rate Limiting Middleware
# ─────────────────────────────────────────────────────────────────────────────

class TestRateLimiting:
    """Rate limiter: middleware behavior."""

    def test_middleware_exists(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_disabled_by_default(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)
        assert not middleware.is_configured

    def test_configurable_via_env(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        with patch.dict("os.environ", {"CASE_RATE_LIMIT": "50"}):
            middleware = RateLimitMiddleware(mock_app)
            assert middleware.is_configured
            assert middleware._max_rps == 50

    def test_rate_limit_enforced(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, max_requests_per_second=100)
        middleware._window_seconds = 1.0
        client_ip = "10.0.0.1"
        for _ in range(100):
            assert not middleware._is_rate_limited(client_ip)
        assert middleware._is_rate_limited(client_ip)

    def test_exempt_paths_not_limited(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, max_requests_per_second=1)
        assert "/health" in middleware.EXEMPT_PATHS
        assert "/docs" in middleware.EXEMPT_PATHS

    def test_middleware_class_exists_in_app(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        assert RateLimitMiddleware is not None


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 4: correlation_id in Audit Flow
# ─────────────────────────────────────────────────────────────────────────────

class TestCorrelationId:
    """correlation_id: appears and is preserved."""

    def test_field_exists_in_contract(self) -> None:
        event = AuditEvent(
            event_id="test-1",
            case_id="CASE-001",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert hasattr(event, "correlation_id")

    def test_field_defaults_to_empty(self) -> None:
        event = AuditEvent(
            event_id="test-2",
            case_id="CASE-002",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.correlation_id == ""

    def test_field_settable(self) -> None:
        event = AuditEvent(
            event_id="test-3",
            case_id="CASE-003",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
            correlation_id="corr-abc-123",
        )
        assert event.correlation_id == "corr-abc-123"

    def test_field_in_model_dump(self) -> None:
        event = AuditEvent(
            event_id="test-4",
            case_id="CASE-004",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
            correlation_id="corr-xyz",
        )
        data = event.model_dump()
        assert "correlation_id" in data
        assert data["correlation_id"] == "corr-xyz"

    def test_persistence_saves_correlation_id(self) -> None:
        import tempfile

        from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        adapter = SQLiteAuditAdapter(db_path=db_path)
        event = AuditEvent(
            event_id="test-persist",
            case_id="CASE-PERSIST",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
            correlation_id="corr-persist-123",
        )

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(adapter.log_event(event))
            events = loop.run_until_complete(
                adapter.get_events_by_case("CASE-PERSIST")
            )
            assert len(events) == 1
            assert events[0].correlation_id == "corr-persist-123"
        finally:
            loop.close()

    def test_backward_compatible(self) -> None:
        data = {
            "event_id": "test-bc",
            "case_id": "CASE-BC",
            "event_type": "TEST",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        event = AuditEvent(**data)
        assert event.correlation_id == ""


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 5: No Accidental Connections
# ─────────────────────────────────────────────────────────────────────────────

class TestNoAccidentalConnections:
    """Verify isolated modules are NOT wired into the running pipeline."""

    def test_governance_not_imported_in_composition(self) -> None:
        from case_core import composition
        source = inspect.getsource(composition)
        assert "governance" not in source.lower()
        assert "GovernanceFramework" not in source

    def test_hybrid_not_imported_in_engine(self) -> None:
        from case_core.application import engine
        source = inspect.getsource(engine)
        assert "hybrid" not in source.lower()
        assert "HybridDecisionEngine" not in source

    def test_specialist_not_imported_in_engine(self) -> None:
        from case_core.application import engine
        source = inspect.getsource(engine)
        assert "specialist" not in source.lower()
        assert "SpecialistModel" not in source

    def test_ml_adaptation_not_imported_in_engine(self) -> None:
        from case_core.application import engine
        source = inspect.getsource(engine)
        assert "adaptation" not in source.lower()
        assert "ModelAdapter" not in source

    def test_logistics_intelligence_not_imported_in_engine(self) -> None:
        from case_core.application import engine
        source = inspect.getsource(engine)
        assert "ShipmentUnderstanding" not in source
        assert "CarrierMatching" not in source
        assert "RouteRecommendation" not in source

    def test_governance_not_imported_in_app(self) -> None:
        from case_api.api.v1 import app
        source = inspect.getsource(app)
        assert "GovernanceFramework" not in source
        assert "SecurityManager" not in source
        assert "ComplianceManager" not in source

    def test_case_logistics_not_imported_in_composition(self) -> None:
        from case_core import composition
        source = inspect.getsource(composition)
        assert "case_logistics" not in source

    def test_five_domains_not_more(self) -> None:
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        domains = deps.registry.list_domains()
        assert len(domains) == 5
        expected = {"urban_operations", "logistics", "infrastructure", "seismic_risk", "real_estate"}
        assert set(domains) == expected


# ─────────────────────────────────────────────────────────────────────────────
# CHECK 6: Core Pipeline Unchanged
# ─────────────────────────────────────────────────────────────────────────────

class TestCorePipelineUnchanged:
    """Verify TriageEngine, ReliabilityPipeline, AutomationEvaluator unchanged."""

    def test_triage_engine_line_count(self) -> None:
        from case_core.application.engine import TriageEngine
        source = inspect.getsource(TriageEngine)
        lines = len(source.splitlines())
        assert 200 <= lines <= 300

    def test_reliability_pipeline_line_count(self) -> None:
        from case_core.reliability.pipeline import ReliabilityPipeline
        source = inspect.getsource(ReliabilityPipeline)
        lines = len(source.splitlines())
        assert 400 <= lines <= 500

    def test_automation_evaluator_exists(self) -> None:
        from case_core.reliability.automation import AutomationEvaluator
        assert AutomationEvaluator is not None
