"""Verify that denied/unauthorized requests do not produce unauthorized business side effects.

Strict-mode tests using isolated temporary DBs. Assertions focus on persisted decisions,
audit events, and idempotency records where applicable.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CASE_PROVIDER", "mock")
sys.path.insert(0, "src")


def _count(db_path: str, table: str, where: str = "", params: tuple = ()) -> int:
    if not Path(db_path).exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone() is None:
            return 0
        q = f"SELECT COUNT(*) FROM {table}"
        if where:
            q += f" WHERE {where}"
        return int(conn.execute(q, params).fetchone()[0])
    finally:
        conn.close()


def _snapshot(tmp: str) -> dict[str, int]:
    dec = os.path.join(tmp, "decisions.db")
    aud = os.path.join(tmp, "audit.db")
    return {
        "decisions": _count(dec, "decisions"),
        "audit_events": _count(aud, "audit_events"),
        "idempotency": _count(dec, "idempotency_keys") + _count(aud, "idempotency_keys"),
    }


def _build_strict_app_with_db(tmp: str, scopes: str, active: bool = True):
    import case_api.api.v1.app as appmod
    from case_api.api.v1.auth import APIKeyAuthMiddleware
    from case_api.api.v1.security import load_security_config
    from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
    from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository
    from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

    dec_db = os.path.join(tmp, "decisions.db")
    aud_db = os.path.join(tmp, "audit.db")

    # Save state to restore after test (prevents cross-test contamination)
    saved_env = os.environ.get("CASE_DB_PATH")
    saved = (
        appmod.decision_repo,
        appmod.audit_adapter,
        appmod.engine._decision_repository,
        appmod.engine._audit_port,
        appmod._idempotency_store,
    )

    os.environ["CASE_DB_PATH"] = dec_db

    cfg = load_security_config(
        {
            "CASE_SECURITY_MODE": "shared",
            "CASE_API_KEYS": json.dumps(
                {
                    "k-valid": {
                        "consumer_id": "c1",
                        "tenant_id": "t1",
                        "scopes": scopes.split(",") if scopes else [],
                        "active": active,
                    }
                }
            ),
        }
    )
    a = FastAPI()
    a.state.security_config = cfg
    a.add_middleware(APIKeyAuthMiddleware, config=cfg)

    # Register protected business routes
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

    # Bind repos to isolated DBs for this test app context
    appmod.decision_repo = SQLiteDecisionRepository(dec_db)
    appmod.audit_adapter = SQLiteAuditAdapter(aud_db)
    appmod.engine._decision_repository = appmod.decision_repo
    appmod.engine._audit_port = appmod.audit_adapter
    # Idempotency store is module-level in app; point it to isolated DB
    appmod._idempotency_store = SQLiteIdempotencyStore(dec_db)

    def restore() -> None:
        (
            appmod.decision_repo,
            appmod.audit_adapter,
            appmod.engine._decision_repository,
            appmod.engine._audit_port,
            appmod._idempotency_store,
        ) = saved
        if saved_env is None:
            os.environ.pop("CASE_DB_PATH", None)
        else:
            os.environ["CASE_DB_PATH"] = saved_env

    return a, dec_db, aud_db, restore


EVAL_BODY = {
    "contract_version": "case-eval/v0.1-draft",
    "capability_id": "case.evaluate",
    "correlation_id": "corr-deny",
    "idempotency_key": "idem-deny",
    "data_status": "synthetic",
    "payload": {
        "domain": "logistics",
        "summary": "Synthetic denial-effect test",
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
    "report_text": "Synthetic triage denial-effect test",
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
HITL_ESCALATE_BODY = {
    "actor": "tester",
    "justification": "test",
    "escalate_to": "supervisor",
}
HITL_MODIFY_BODY = {
    "action": "approve",
    "reason": "test reason long enough",
    "urgency": "MEDIUM",
    "confidence": 0.5,
    "evidence_summary": "synthetic evidence",
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


@pytest.mark.integration
class TestDeniedRequestsHaveNoUnauthorizedSideEffects:
    def test_401_no_credentials_leaves_persistence_untouched(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app_with_db(
                tmp, scopes="other:scope"
            )
            try:
                c = TestClient(app, raise_server_exceptions=False)
                before = _snapshot(tmp)
                for method, path, body in CASES:
                    r = (
                        c.request(method, path, json=body)
                        if body is not None
                        else c.request(method, path)
                    )
                    assert r.status_code == 401, (method, path, r.status_code, r.text)
                after = _snapshot(tmp)
                assert after == before, (before, after)
            finally:
                restore()

    def test_403_insufficient_scope_leaves_persistence_untouched(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app_with_db(
                tmp, scopes="other:scope"
            )
            try:
                c = TestClient(app, raise_server_exceptions=False)
                h = {"X-API-Key": "k-valid"}
                before = _snapshot(tmp)
                for method, path, body in CASES:
                    r = (
                        c.request(method, path, json=body, headers=h)
                        if body is not None
                        else c.request(method, path, headers=h)
                    )
                    assert r.status_code == 403, (method, path, r.status_code, r.text)
                after = _snapshot(tmp)
                assert after == before, (before, after)
            finally:
                restore()

    def test_403_revoked_consumer_leaves_persistence_untouched(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app_with_db(
                tmp,
                scopes="case:evaluate,case:read,case:triage,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read,case:compare,case:admin",
                active=False,
            )
            try:
                c = TestClient(app, raise_server_exceptions=False)
                h = {"X-API-Key": "k-valid"}
                before = _snapshot(tmp)
                for method, path, body in CASES:
                    r = (
                        c.request(method, path, json=body, headers=h)
                        if body is not None
                        else c.request(method, path, headers=h)
                    )
                    assert r.status_code == 403, (method, path, r.status_code, r.text)
                after = _snapshot(tmp)
                assert after == before, (before, after)
            finally:
                restore()

    def test_invalid_credentials_leave_persistence_untouched(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app_with_db(
                tmp, scopes="case:evaluate,case:admin"
            )
            try:
                c = TestClient(app, raise_server_exceptions=False)
                h = {"X-API-Key": "wrong-key"}
                before = _snapshot(tmp)
                for method, path, body in CASES:
                    r = (
                        c.request(method, path, json=body, headers=h)
                        if body is not None
                        else c.request(method, path, headers=h)
                    )
                    assert r.status_code == 401, (method, path, r.status_code, r.text)
                after = _snapshot(tmp)
                assert after == before, (before, after)
            finally:
                restore()
