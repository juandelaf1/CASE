import sys
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

sys.path.insert(0, "src")

from streamlit_app.client import CASEClient


@pytest.fixture
def client():
    return CASEClient(base_url="http://test-api:8000", timeout_seconds=5.0)


def _async_client_mock(response: MagicMock) -> MagicMock:
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=response)
    mock_client.post = AsyncMock(return_value=response)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


def _sync_client_mock(response: MagicMock) -> MagicMock:
    mock_client = MagicMock()
    mock_client.get = MagicMock(return_value=response)
    mock_client.post = MagicMock(return_value=response)
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    return mock_client


class TestCaseClientConstruction:
    def test_default_url(self):
        with patch.dict("os.environ", {"CASE_API_BASE_URL": "http://env-api:9000"}):
            c = CASEClient()
            assert c.base_url == "http://env-api:9000"

    def test_custom_url(self):
        c = CASEClient(base_url="http://custom:3000")
        assert c.base_url == "http://custom:3000"

    def test_strips_trailing_slash(self):
        c = CASEClient(base_url="http://api:8000/")
        assert c.base_url == "http://api:8000"

    def test_env_var_fallback(self):
        with patch.dict("os.environ", {"CASE_API_BASE_URL": "http://from-env:8080"}):
            c = CASEClient()
            assert c.base_url == "http://from-env:8080"


class TestCaseClientHealth:
    @pytest.mark.asyncio
    async def test_health_success(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "version": "0.1.0"}
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.health()
            assert result["status"] == "ok"

    def test_health_sync_success(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "ok", "version": "0.1.0"}
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _sync_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.Client", return_value=mock_httpx):
            result = client.health_sync()
            assert result["status"] == "ok"


class TestCaseClientDomains:
    @pytest.mark.asyncio
    async def test_list_domains(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"domains": ["urban_operations", "logistics"]}
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.list_domains()
            assert result == ["urban_operations", "logistics"]

    def test_list_domains_sync(self, client):
        mock_response = MagicMock()
        mock_response.json.return_value = {"domains": ["urban_operations", "logistics"]}
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _sync_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.Client", return_value=mock_httpx):
            result = client.list_domains_sync()
            assert result == ["urban_operations", "logistics"]


class TestCaseClientTriage:
    @pytest.mark.asyncio
    async def test_triage_success(self, client):
        triage_response = {
            "decision_id": "dec-001",
            "case_id": "case-001",
            "domain": "urban_operations",
            "action": "approve",
            "reason": "Standard case",
            "urgency": "MEDIUM",
            "confidence": 0.85,
            "evidence_summary": "Evidence validated",
            "lifecycle": "APPROVED",
            "processing_time_ms": 150.0,
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = triage_response
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.triage(
                case_id="case-001",
                report_text="Test report",
                domain="urban_operations",
            )
            assert result["error"] is False
            assert result["data"]["action"] == "approve"

    @pytest.mark.asyncio
    async def test_triage_422_returns_error(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "detail": {
                "error": "Validation failed",
                "category": "schema_validation",
                "recoverable": True,
                "retryable": True,
                "requires_manual_review": False,
            }
        }

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.triage(
                case_id="case-001",
                report_text="Test",
                domain="urban_operations",
            )
            assert result["error"] is True
            assert result["detail"]["category"] == "schema_validation"

    @pytest.mark.asyncio
    async def test_triage_manual_review(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_response.json.return_value = {
            "detail": {
                "error": "Terminal failure",
                "category": "schema_validation",
                "recoverable": False,
                "retryable": False,
                "requires_manual_review": True,
            }
        }

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.triage(
                case_id="case-001",
                report_text="Test",
                domain="urban_operations",
            )
            assert result["error"] is True
            assert result["detail"]["requires_manual_review"] is True

    def test_triage_sync_success(self, client):
        triage_response = {
            "decision_id": "dec-001",
            "case_id": "case-001",
            "domain": "urban_operations",
            "action": "approve",
            "reason": "Standard case",
            "urgency": "MEDIUM",
            "confidence": 0.85,
            "evidence_summary": "Evidence validated",
            "lifecycle": "APPROVED",
            "processing_time_ms": 150.0,
        }
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = triage_response
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _sync_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.Client", return_value=mock_httpx):
            result = client.triage_sync(
                case_id="case-001",
                report_text="Test report",
                domain="urban_operations",
            )
            assert result["error"] is False
            assert result["data"]["action"] == "approve"


class TestCaseClientAudit:
    @pytest.mark.asyncio
    async def test_get_audit_events(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "case_id": "case-001",
            "events": [{"event_type": "CASE_RECEIVED", "timestamp": "2026-09-08T12:00:00Z"}],
            "count": 1,
        }
        mock_response.raise_for_status = MagicMock()

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.get_audit_events("case-001")
            assert result["count"] == 1

    @pytest.mark.asyncio
    async def test_get_audit_events_404_returns_empty(self, client):
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_httpx = _async_client_mock(mock_response)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            result = await client.get_audit_events("nonexistent")
            assert result["events"] == []
            assert result["count"] == 0


class TestCaseClientErrorHandling:
    @pytest.mark.asyncio
    async def test_connection_error_propagates(self, client):
        mock_httpx = AsyncMock()
        mock_httpx.get = AsyncMock(side_effect=httpx.ConnectError("refused"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            with pytest.raises(httpx.ConnectError):
                await client.health()

    @pytest.mark.asyncio
    async def test_timeout_propagates(self, client):
        mock_httpx = AsyncMock()
        mock_httpx.get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_httpx.__aenter__ = AsyncMock(return_value=mock_httpx)
        mock_httpx.__aexit__ = AsyncMock(return_value=False)

        with patch("streamlit_app.client.httpx.AsyncClient", return_value=mock_httpx):
            with pytest.raises(httpx.TimeoutException):
                await client.health()
