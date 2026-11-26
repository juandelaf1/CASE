"""Strict-mode AuthN/AuthZ matrix coverage for registered business routes.

Focus: 401 without credentials and 403 with authenticated but insufficient scope.
Uses valid request shapes so handler-level scope checks are exercised (not schema 422).
"""

from __future__ import annotations

import os
import sys

from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CASE_PROVIDER", "mock")
sys.path.insert(0, "src")


def _build_strict_app(scopes: str) -> FastAPI:
    import case_api.api.v1.app as appmod
    from case_api.api.v1.auth import APIKeyAuthMiddleware
    from case_api.api.v1.security import load_security_config

    cfg = load_security_config(
        {
            "CASE_SECURITY_MODE": "shared",
            "CASE_API_KEY": "k-matrix",
            "CASE_CONSUMER_ID": "c1",
            "CASE_TENANT_ID": "t1",
            "CASE_API_SCOPES": scopes,
        }
    )
    a = FastAPI()
    a.state.security_config = cfg
    a.add_middleware(APIKeyAuthMiddleware, config=cfg)

    # Register protected business routes (exempt routes intentionally omitted)
    a.post("/api/v1/evaluate")(appmod.evaluate_case)
    a.post("/api/v1/triage")(appmod.triage)
    a.get("/api/v1/cases")(appmod.list_cases)
    a.get("/api/v1/cases/{case_id}")(appmod.get_case)
    a.get("/api/v1/audit/{case_id}")(appmod.get_audit_events)
    a.get("/api/v1/hitl/pending")(appmod.list_pending_review)
    a.get("/api/v1/hitl/{decision_id}")(appmod.get_decision)
    a.post("/api/v1/hitl/{decision_id}/under-review")(appmod.start_review)
    a.post("/api/v1/hitl/{decision_id}/approve")(appmod.approve_decision)
    a.post("/api/v1/hitl/{decision_id}/reject")(appmod.reject_decision)
    a.post("/api/v1/hitl/{decision_id}/escalate")(appmod.escalate_decision)
    a.post("/api/v1/hitl/{decision_id}/modify")(appmod.modify_decision)
    a.post("/api/v1/comparison")(appmod.compare)
    a.get("/domains")(appmod.list_domains)
    a.get("/api/v1/providers")(appmod.list_providers)
    a.get("/api/v1/seismic/events")(appmod.get_seismic_events)
    a.get("/api/v1/seismic/health")(appmod.seismic_health)
    return a


EVAL_BODY = {
    "contract_version": "case-eval/v0.1-draft",
    "capability_id": "case.evaluate",
    "correlation_id": "corr-matrix",
    "data_status": "synthetic",
    "payload": {
        "domain": "logistics",
        "summary": "Synthetic matrix test",
        "urgency": "MEDIUM",
        "evidence": [
            {
                "id": "e1",
                "type": "text",
                "content": "synthetic",
                "source": "test",
                "confidence": 0.5,
            }
        ],
        "provider": "mock",
        "metadata": {"synthetic": "true"},
    },
}

TRIAGE_BODY = {
    "domain": "logistics",
    "report_text": "Synthetic triage for matrix test",
    "urgency": "MEDIUM",
    "evidence": [
        {
            "id": "e1",
            "type": "text",
            "content": "synthetic",
            "source": "test",
            "confidence": 0.5,
            "extracted_at": "2026-11-11T00:00:00Z",
        }
    ],
    "provider": "mock",
}

COMPARISON_BODY = {
    "report_text": "synthetic comparison",
    "domain": "logistics",
    "providers": [],
    "evidence": [],
}

HITL_ACTION_BODY = {"actor": "tester", "notes": "", "justification": "test"}
HITL_ESCALATE_BODY = {"actor": "tester", "justification": "test", "escalate_to": "supervisor"}
HITL_MODIFY_BODY = {
    "action": "approve",
    "reason": "test",
    "urgency": "MEDIUM",
    "confidence": 0.5,
    "evidence_summary": "synthetic",
    "actor": "tester",
    "notes": "",
    "justification": "test",
}


CASES = [
    ("POST", "/api/v1/evaluate", EVAL_BODY),
    ("POST", "/api/v1/triage", TRIAGE_BODY),
    ("GET", "/api/v1/cases", None),
    ("GET", "/api/v1/cases/case-x", None),
    ("GET", "/api/v1/audit/case-x", None),
    ("GET", "/api/v1/hitl/pending", None),
    ("GET", "/api/v1/hitl/dec-x", None),
    ("POST", "/api/v1/hitl/dec-x/under-review", HITL_ACTION_BODY),
    ("POST", "/api/v1/hitl/dec-x/approve", HITL_ACTION_BODY),
    ("POST", "/api/v1/hitl/dec-x/reject", HITL_ACTION_BODY),
    ("POST", "/api/v1/hitl/dec-x/escalate", HITL_ESCALATE_BODY),
    ("POST", "/api/v1/hitl/dec-x/modify", HITL_MODIFY_BODY),
    ("POST", "/api/v1/comparison", COMPARISON_BODY),
    ("GET", "/domains", None),
    ("GET", "/api/v1/providers", None),
    ("GET", "/api/v1/seismic/events", None),
    ("GET", "/api/v1/seismic/health", None),
]


class TestStrictAuthzMatrix:
    def test_all_protected_routes_require_credentials(self):
        app = _build_strict_app(scopes="none:useful")
        c = TestClient(app, raise_server_exceptions=False)
        for method, path, body in CASES:
            r = c.request(method, path, json=body) if body is not None else c.request(method, path)
            assert r.status_code == 401, (method, path, r.status_code, r.text)

    def test_all_protected_routes_reject_insufficient_scope(self):
        # Authenticated identity with unrelated scope
        app = _build_strict_app(scopes="other:scope")
        c = TestClient(app, raise_server_exceptions=False)
        h = {"X-API-Key": "k-matrix"}
        for method, path, body in CASES:
            r = (
                c.request(method, path, json=body, headers=h)
                if body is not None
                else c.request(method, path, headers=h)
            )
            # Some handlers may return 404 after authz in certain designs, but scope checks run first here;
            # strict insufficient scope must be denied (403), never allowed as 2xx.
            assert r.status_code == 403, (method, path, r.status_code, r.text)
