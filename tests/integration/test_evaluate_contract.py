import os
import sys
from pathlib import Path

import jsonschema

os.environ.setdefault("CASE_PROVIDER", "mock")

from fastapi.testclient import TestClient

sys.path.insert(0, "src")

from case_api.api.v1.app import app

client = TestClient(app)

# Minimal contract shapes aligned with POOLAR_ECOSYSTEM_GOVERNANCE/18_contracts (case-eval/v0.1-draft)
REQUEST_SCHEMA = {
    "type": "object",
    "required": ["contract_version", "capability_id", "correlation_id", "payload"],
    "properties": {
        "contract_version": {"const": "case-eval/v0.1-draft"},
        "capability_id": {"const": "case.evaluate"},
        "correlation_id": {"type": "string", "minLength": 1},
        "scopes": {"type": "array", "items": {"type": "string"}},
        "payload": {
            "type": "object",
            "required": ["domain", "summary"],
            "properties": {
                "domain": {"type": "string"},
                "summary": {"type": "string", "minLength": 1},
                "evidence": {"type": "array"},
            },
        },
    },
}

RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["contract_version", "capability_id", "correlation_id", "status", "result"],
    "properties": {
        "contract_version": {"const": "case-eval/v0.1-draft"},
        "capability_id": {"const": "case.evaluate"},
        "correlation_id": {"type": "string"},
        "status": {"type": "string", "enum": ["ok", "pending_review", "degraded", "rejected", "error"]},
        "result": {
            "type": "object",
            "required": ["decision_type", "requires_human_review"],
            "properties": {
                "decision_type": {"const": "recommendation"},
                "requires_human_review": {"type": "boolean"},
                "case_ref": {"type": ["string", "null"]},
                "action": {"type": "string"},
            },
        },
        "warnings": {"type": "array"},
        "errors": {"type": "array"},
    },
}


class TestEvaluateContract:
    def _sample_request(self):
        return {
            "contract_version": "case-eval/v0.1-draft",
            "capability_id": "case.evaluate",
            "correlation_id": "corr-contract-1",
            "scopes": ["case:evaluate"],
            "data_status": "synthetic",
            "payload": {
                "case_id": "CASE-SYNTH-1",
                "domain": "logistics",
                "summary": "Synthetic delay report",
                "urgency": "MEDIUM",
                "evidence": [{"id": "e1", "type": "text", "content": "delay", "source": "test", "confidence": 0.7}],
            },
        }

    def test_request_matches_min_contract_shape(self):
        jsonschema.validate(instance=self._sample_request(), schema=REQUEST_SCHEMA)

    def test_response_matches_min_contract_shape(self):
        req = self._sample_request()
        response = client.post("/api/v1/evaluate", json=req)
        assert response.status_code == 200
        data = response.json()
        jsonschema.validate(instance=data, schema=RESPONSE_SCHEMA)
        assert data["correlation_id"] == req["correlation_id"]
        assert data["result"]["decision_type"] == "recommendation"

    def test_error_response_keeps_envelope_on_upstream_failure(self):
        # invalid domain triggers upstream error mapping in adapter
        req = self._sample_request()
        req["correlation_id"] = "corr-contract-err"
        req["payload"]["domain"] = "unknown_domain_contract_test"
        response = client.post("/api/v1/evaluate", json=req)
        assert response.status_code == 200
        data = response.json()
        assert data["contract_version"] == "case-eval/v0.1-draft"
        assert data["capability_id"] == "case.evaluate"
        assert data["correlation_id"] == "corr-contract-err"
        assert data["status"] == "error"
        assert isinstance(data.get("errors"), list)
        assert data["result"]["decision_type"] == "recommendation"
        assert data["result"]["requires_human_review"] is True
