import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, "src")

from case_api.api.v1.app import app


client = TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["version"] == "0.1.0"


class TestDomainsEndpoint:
    def test_list_domains(self):
        response = client.get("/domains")
        assert response.status_code == 200
        domains = response.json()["domains"]
        assert "urban_operations" in domains
        assert "logistics" in domains
        assert "infrastructure" in domains


class TestTriageEndpoint:
    def test_triage_success(self):
        request = {
            "case_id": "case-001",
            "report_text": "Falla en farola de la calle principal",
            "domain": "urban_operations",
            "urgency": "HIGH",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Falla reportada por ciudadano",
                    "source": "citizen_report",
                    "confidence": 0.9,
                    "extracted_at": "2026-09-08T12:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == "case-001"
        assert data["action"] in ["approve", "reject", "escalate"]
        assert data["domain"] == "urban_operations"
        assert 0.0 <= data["confidence"] <= 1.0

    def test_triage_unknown_domain(self):
        request = {
            "case_id": "case-002",
            "report_text": "Test",
            "domain": "unknown_domain",
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 400

    def test_triage_mock_01(self):
        request = {
            "case_id": "case-mock-01",
            "report_text": "[TEST-MOCK-01] Standard case",
            "domain": "urban_operations",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Standard evidence",
                    "source": "test",
                    "confidence": 0.9,
                    "extracted_at": "2026-09-08T12:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "approve"

    def test_triage_mock_02_reject(self):
        request = {
            "case_id": "case-mock-02",
            "report_text": "[TEST-MOCK-02] Insufficient evidence case",
            "domain": "urban_operations",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Weak evidence",
                    "source": "test",
                    "confidence": 0.5,
                    "extracted_at": "2026-09-08T12:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "reject"

    def test_triage_mock_03_escalate(self):
        request = {
            "case_id": "case-mock-03",
            "report_text": "[TEST-MOCK-03] High urgency case",
            "domain": "urban_operations",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Emergency evidence",
                    "source": "test",
                    "confidence": 0.8,
                    "extracted_at": "2026-09-08T12:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["action"] == "escalate"
        assert data["urgency"] == "HIGH"

    def test_triage_minimal_request(self):
        request = {
            "case_id": "case-minimal",
            "report_text": "Minimal test case with evidence",
            "domain": "logistics",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Shipment status update",
                    "source": "system",
                    "confidence": 0.8,
                    "extracted_at": "2026-09-08T12:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["case_id"] == "case-minimal"

    def test_triage_invalid_json_terminal_failure(self):
        request = {
            "case_id": "case-invalid",
            "report_text": "[TEST-MOCK-INVALID-JSON] This will cause parse error",
            "domain": "urban_operations",
            "evidence": [
                {
                    "id": "ev-001",
                    "type": "text",
                    "content": "Test evidence",
                    "source": "test",
                    "confidence": 0.9,
                    "extracted_at": "2026-09-08T12:00:00Z",
                }
            ],
        }
        response = client.post("/api/v1/triage", json=request)
        assert response.status_code == 422
        data = response.json()["detail"]
        assert data["requires_manual_review"] is True
        assert data["processing_lifecycle"] == "terminal_failure"


class TestAuditEndpoint:
    def test_get_audit_events(self):
        response = client.get("/api/v1/audit/case-001")
        assert response.status_code == 200
        data = response.json()
        assert "case_id" in data
        assert "events" in data
        assert "count" in data

    def test_get_audit_events_empty(self):
        response = client.get("/api/v1/audit/nonexistent")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 0