"""Tests for V3 ecosystem integrations.

Covers:
- Real Estate domain registration in composition
- USGS seismic API endpoints
- Rate limiter middleware
- Health endpoint enhancements
- AuditEvent correlation_id
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from case_core.contracts.audit import AuditEvent

# ---------------------------------------------------------------------------
# Real Estate Registration
# ---------------------------------------------------------------------------

class TestRealEstateRegistration:
    """Verify Real Estate domain is registered in composition."""

    def test_real_estate_in_registry(self) -> None:
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        assert "real_estate" in deps.registry.list_domains()

    def test_real_estate_policy_retrievable(self) -> None:
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        policy = deps.registry.get("real_estate")
        assert policy is not None
        assert policy.domain_name == "real_estate"

    def test_real_estate_automation_policy_wired(self) -> None:
        from case_core.composition import _resolve_automation_policy
        policy = _resolve_automation_policy("real_estate")
        assert policy is not None

    def test_five_domains_registered(self) -> None:
        from case_core.composition import create_app_dependencies
        deps = create_app_dependencies()
        domains = deps.registry.list_domains()
        assert len(domains) == 5
        assert "urban_operations" in domains
        assert "logistics" in domains
        assert "infrastructure" in domains
        assert "seismic_risk" in domains
        assert "real_estate" in domains


# ---------------------------------------------------------------------------
# Correlation ID in AuditEvent
# ---------------------------------------------------------------------------

class TestAuditEventCorrelationId:
    """Verify correlation_id field in AuditEvent."""

    def test_correlation_id_default_empty(self) -> None:
        event = AuditEvent(
            event_id="test-1",
            case_id="CASE-001",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
        )
        assert event.correlation_id == ""

    def test_correlation_id_settable(self) -> None:
        event = AuditEvent(
            event_id="test-2",
            case_id="CASE-002",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
            correlation_id="corr-abc-123",
        )
        assert event.correlation_id == "corr-abc-123"

    def test_correlation_id_in_model_dump(self) -> None:
        event = AuditEvent(
            event_id="test-3",
            case_id="CASE-003",
            event_type="TEST",
            timestamp="2026-01-01T00:00:00Z",
            correlation_id="corr-xyz",
        )
        data = event.model_dump()
        assert "correlation_id" in data
        assert data["correlation_id"] == "corr-xyz"

    def test_correlation_id_backward_compatible(self) -> None:
        data = {
            "event_id": "test-4",
            "case_id": "CASE-004",
            "event_type": "TEST",
            "timestamp": "2026-01-01T00:00:00Z",
        }
        event = AuditEvent(**data)
        assert event.correlation_id == ""


# ---------------------------------------------------------------------------
# Rate Limiter Middleware
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    """Verify RateLimitMiddleware behavior."""

    def test_disabled_by_default(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)
        assert not middleware.is_configured
        assert middleware._max_rps == 0

    def test_configured_via_env(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        with patch.dict("os.environ", {"CASE_RATE_LIMIT": "10"}):
            middleware = RateLimitMiddleware(mock_app)
            assert middleware.is_configured
            assert middleware._max_rps == 10

    def test_configured_via_constructor(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, max_requests_per_second=50)
        assert middleware.is_configured
        assert middleware._max_rps == 50

    def test_no_rate_limit_when_disabled(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app)
        assert not middleware._is_rate_limited("127.0.0.1")

    def test_rate_limit_exceeded(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, max_requests_per_second=100)
        middleware._window_seconds = 1.0  # 1 second window
        client_ip = "10.0.0.1"
        # max_requests = 100 * 1 = 100
        for _ in range(100):
            assert not middleware._is_rate_limited(client_ip)
        assert middleware._is_rate_limited(client_ip)

    def test_get_usage(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, max_requests_per_second=10)
        usage = middleware.get_usage("127.0.0.1")
        assert "current_requests" in usage
        assert "max_requests" in usage
        assert usage["is_configured"] is True

    def test_exempt_paths_bypass_rate_limit(self) -> None:
        from case_api.api.v1.rate_limit import RateLimitMiddleware
        mock_app = MagicMock()
        middleware = RateLimitMiddleware(mock_app, max_requests_per_second=1)
        assert "/health" in middleware.EXEMPT_PATHS
        assert "/docs" in middleware.EXEMPT_PATHS
        assert "/" in middleware.EXEMPT_PATHS


# ---------------------------------------------------------------------------
# Health Endpoint Enhancements
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    """Verify enhanced health endpoint structure."""

    def test_health_includes_domains(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "domains" in data
        assert "domain_count" in data
        assert data["domain_count"] >= 4

    def test_health_includes_providers(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert "providers" in data
        assert "active_provider" in data
        assert isinstance(data["providers"], list)

    def test_health_includes_version(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app
        client = TestClient(app)
        response = client.get("/health")
        data = response.json()
        assert "version" in data
        assert "status" in data


# ---------------------------------------------------------------------------
# USGS Seismic Endpoints
# ---------------------------------------------------------------------------

class TestSeismicEndpoints:
    """Verify USGS seismic API endpoints."""

    def test_seismic_health_endpoint_exists(self) -> None:
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app
        client = TestClient(app)
        with patch("usgs_adapter.client.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            response = client.get("/api/v1/seismic/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "api" in data
        assert "reachable" in data

    def test_seismic_events_endpoint_exists(self) -> None:
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
        with patch("usgs_adapter.client.httpx.Client") as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"features": [mock_feature]}
            mock_response.raise_for_status = MagicMock()
            mock_client.return_value.__enter__.return_value.get.return_value = mock_response
            response = client.get("/api/v1/seismic/events")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "count" in data
        assert "total_available" in data
