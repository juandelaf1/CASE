import os
import sys

os.environ.setdefault("CASE_PROVIDER", "mock")

from fastapi.testclient import TestClient

sys.path.insert(0, "src")

from case_api.api.v1.app import app

client = TestClient(app)


class TestEvaluateEndpoint:
    def test_evaluate_success_envelope(self):
        request = {
            "contract_version": "case-eval/v0.1-draft",
            "capability_id": "case.evaluate",
            "correlation_id": "corr-eval-1",
            "idempotency_key": "idem-eval-1",
            "scopes": ["case:evaluate"],
            "data_status": "synthetic",
            "payload": {
                "case_id": "CASE-SYNTH-1",
                "domain": "logistics",
                "summary": "Synthetic delay report",
                "urgency": "MEDIUM",
                "evidence": [
                    {
                        "id": "e1",
                        "type": "text",
                        "content": "Synthetic delay report",
                        "source": "test",
                        "confidence": 0.7,
                    }
                ],
                "metadata": {"synthetic": "true"},
                "provider": "mock",
            },
        }
        response = client.post("/api/v1/evaluate", json=request)
        assert response.status_code == 200
        data = response.json()
        assert data["contract_version"] == "case-eval/v0.1-draft"
        assert data["capability_id"] == "case.evaluate"
        assert data["correlation_id"] == "corr-eval-1"
        assert data["status"] in {"ok", "pending_review", "degraded"}
        assert data["result"]["decision_type"] == "recommendation"
        assert "requires_human_review" in data["result"]
        assert data["result"]["case_ref"]

    def test_evaluate_requires_scope_when_scopes_provided(self):
        request = {
            "contract_version": "case-eval/v0.1-draft",
            "capability_id": "case.evaluate",
            "correlation_id": "corr-eval-noscope",
            "scopes": ["other:scope"],
            "payload": {
                "domain": "logistics",
                "summary": "Synthetic delay report",
                "evidence": [{"id": "e1", "type": "text", "content": "x", "source": "t", "confidence": 0.5}],
            },
        }
        response = client.post("/api/v1/evaluate", json=request)
        assert response.status_code == 403
        detail = response.json().get("detail", {})
        assert detail.get("code") == "AUTHZ_SCOPE_MISSING"

    def test_evaluate_rejects_empty_summary(self):
        request = {
            "contract_version": "case-eval/v0.1-draft",
            "capability_id": "case.evaluate",
            "correlation_id": "corr-eval-empty",
            "scopes": ["case:evaluate"],
            "payload": {
                "domain": "logistics",
                "summary": "   ",
                "evidence": [{"id": "e1", "type": "text", "content": "x", "source": "t", "confidence": 0.5}],
            },
        }
        response = client.post("/api/v1/evaluate", json=request)
        assert response.status_code == 400
        detail = response.json().get("detail", {})
        assert detail.get("code") == "VALIDATION_MISSING_FIELD"
