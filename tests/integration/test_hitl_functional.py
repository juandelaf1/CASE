"""HITL functional closure tests for single-consumer consolidation.

Covers: allowed/forbidden transitions, repetition, unauthorized/foreign context,
and incompatible concurrent actions (CAS protection, no silent overwrite).
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
import threading
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CASE_PROVIDER", "mock")
sys.path.insert(0, "src")


def _build_app(tmp: str, consumer="c1", tenant="t1", key="k1", scopes="case:evaluate,case:read,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read,case:admin"):
    import case_api.api.v1.app as appmod
    from case_api.api.v1.auth import APIKeyAuthMiddleware
    from case_api.api.v1.security import load_security_config
    from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
    from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository
    from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

    dec_db = os.path.join(tmp, "decisions.db")
    aud_db = os.path.join(tmp, "audit.db")
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
            "CASE_API_KEYS": json.dumps({key: {"consumer_id": consumer, "tenant_id": tenant, "scopes": scopes.split(",")}}),
        }
    )
    a = FastAPI()
    a.state.security_config = cfg
    a.add_middleware(APIKeyAuthMiddleware, config=cfg)
    a.post("/api/v1/evaluate")(appmod.evaluate_case)
    a.get("/api/v1/hitl/pending")(appmod.list_pending_review)
    a.get("/api/v1/hitl/{decision_id}")(appmod.get_decision)
    a.post("/api/v1/hitl/{decision_id}/under-review")(appmod.start_review)
    a.post("/api/v1/hitl/{decision_id}/approve")(appmod.approve_decision)
    a.post("/api/v1/hitl/{decision_id}/reject")(appmod.reject_decision)
    a.post("/api/v1/hitl/{decision_id}/escalate")(appmod.escalate_decision)
    a.post("/api/v1/hitl/{decision_id}/modify")(appmod.modify_decision)

    appmod.decision_repo = SQLiteDecisionRepository(dec_db)
    appmod.audit_adapter = SQLiteAuditAdapter(aud_db)
    appmod.engine._decision_repository = appmod.decision_repo
    appmod.engine._audit_port = appmod.audit_adapter
    appmod._idempotency_store = SQLiteIdempotencyStore(dec_db)

    def restore():
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


def _eval_body(corr="c", idem="i"):
    return {
        "contract_version": "case-eval/v0.1-draft",
        "capability_id": "case.evaluate",
        "correlation_id": corr,
        "idempotency_key": idem,
        "data_status": "synthetic",
        "payload": {
            "domain": "logistics",
            "summary": "Synthetic HITL test",
            "urgency": "MEDIUM",
            "evidence": [{"id": "e1", "type": "text", "content": "x", "source": "t", "confidence": 0.5}],
            "provider": "mock",
        },
    }


def _create_decision(client, headers, idem="i1", corr="c1"):
    r = client.post("/api/v1/evaluate", json=_eval_body(corr=corr, idem=idem), headers=headers)
    assert r.status_code == 200, r.text
    body = r.json()
    case_ref = (body.get("result") or {}).get("case_ref")
    assert case_ref
    return case_ref


def _get_decision_row(dec_db, case_ref):
    conn = sqlite3.connect(dec_db)
    try:
        row = conn.execute("SELECT decision_id, lifecycle FROM decisions WHERE case_id=? ORDER BY created_at DESC LIMIT 1", (case_ref,)).fetchone()
        assert row, f"decision not found for case {case_ref}"
        return row[0], row[1]
    finally:
        conn.close()


def _set_lifecycle(dec_db, decision_id, lifecycle):
    conn = sqlite3.connect(dec_db)
    try:
        conn.execute("UPDATE decisions SET lifecycle=? WHERE decision_id=?", (lifecycle, decision_id))
        conn.commit()
    finally:
        conn.close()


def _count_hitl_audits(aud_db, decision_id):
    if not Path(aud_db).exists():
        return 0
    conn = sqlite3.connect(aud_db)
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_events'").fetchone() is None:
            return 0
        return int(conn.execute("SELECT COUNT(*) FROM audit_events WHERE decision_id=? AND event_type LIKE 'HITL_%'", (decision_id,)).fetchone()[0])
    finally:
        conn.close()


@pytest.mark.integration
class TestHITLFunctional:
    def test_allowed_transitions_and_audit(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_app(tmp)
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k1"}
                case_ref = _create_decision(c, h, idem="i-allow", corr="c-allow")
                dec_id, lc = _get_decision_row(dec_db, case_ref)
                # ensure AI_PROPOSED -> UNDER_REVIEW -> APPROVED path is testable
                _set_lifecycle(dec_db, dec_id, "ai_proposed")
                r1 = c.post(f"/api/v1/hitl/{dec_id}/under-review", json={"actor": "h", "justification": "review"}, headers=h)
                assert r1.status_code == 200, r1.text
                _, lc = _get_decision_row(dec_db, case_ref)
                assert lc == "under_review"
                r2 = c.post(f"/api/v1/hitl/{dec_id}/approve", json={"actor": "h", "justification": "ok"}, headers=h)
                assert r2.status_code == 200, r2.text
                _, lc = _get_decision_row(dec_db, case_ref)
                assert lc == "approved"
                assert _count_hitl_audits(aud_db, dec_id) >= 2
            finally:
                restore()

    def test_forbidden_transitions_repetition_and_no_side_effects(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_app(tmp)
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k1"}
                case_ref = _create_decision(c, h, idem="i-forbid", corr="c-forbid")
                dec_id, _ = _get_decision_row(dec_db, case_ref)
                _set_lifecycle(dec_db, dec_id, "ai_proposed")
                assert c.post(f"/api/v1/hitl/{dec_id}/approve", json={"actor": "h", "justification": "ok"}, headers=h).status_code == 200
                audits_after = _count_hitl_audits(aud_db, dec_id)
                r1 = c.post(f"/api/v1/hitl/{dec_id}/approve", json={"actor": "h", "justification": "again"}, headers=h)
                r2 = c.post(f"/api/v1/hitl/{dec_id}/reject", json={"actor": "h", "justification": "no"}, headers=h)
                r3 = c.post(f"/api/v1/hitl/{dec_id}/under-review", json={"actor": "h", "justification": "back"}, headers=h)
                r4 = c.post(f"/api/v1/hitl/{dec_id}/modify", json={
                    "action": "reject", "reason": "reason text long enough", "urgency": "LOW", "confidence": 0.5,
                    "evidence_summary": "evidence", "actor": "h", "justification": "x",
                }, headers=h)
                assert r1.status_code in (400, 409)
                assert r2.status_code in (400, 409)
                assert r3.status_code in (400, 409)
                assert r4.status_code in (400, 409)
                _, lc = _get_decision_row(dec_db, case_ref)
                assert lc == "approved"
                assert _count_hitl_audits(aud_db, dec_id) == audits_after
            finally:
                restore()

    def test_unauthorized_scope_and_foreign_context(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, _aud_db, restore = _build_app(tmp, consumer="c1", tenant="t1", key="k-owner")
            try:
                c = TestClient(app)
                case_ref = _create_decision(c, {"X-API-Key": "k-owner"}, idem="i-ctx", corr="c-ctx")
                dec_id, _ = _get_decision_row(dec_db, case_ref)
                _set_lifecycle(dec_db, dec_id, "ai_proposed")
            finally:
                restore()
            # no-scope key (read only)
            app2, _dec_db2, _aud_db2, restore2 = _build_app(tmp, consumer="c1", tenant="t1", key="k-noscope", scopes="case:read")
            try:
                c2 = TestClient(app2)
                r = c2.post(f"/api/v1/hitl/{dec_id}/approve", json={"actor": "h", "justification": "x"}, headers={"X-API-Key": "k-noscope"})
                assert r.status_code in (401, 403)
            finally:
                restore2()
            # foreign consumer/tenant cannot access/modify (404 isolation)
            app3, _dec_db3, _aud_db3, restore3 = _build_app(tmp, consumer="c2", tenant="t2", key="k-foreign")
            try:
                c3 = TestClient(app3)
                r = c3.post(f"/api/v1/hitl/{dec_id}/approve", json={"actor": "h", "justification": "x"}, headers={"X-API-Key": "k-foreign"})
                assert r.status_code == 404
                _, lc = _get_decision_row(dec_db, case_ref)
                assert lc == "ai_proposed"
            finally:
                restore3()

    def test_two_incompatible_actions_no_silent_overwrite(self):
        """Concurrent/incompatible actions must not both succeed; final state consistent (CAS)."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_app(tmp)
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k1"}
                case_ref = _create_decision(c, h, idem="i-race", corr="c-race")
                dec_id, _ = _get_decision_row(dec_db, case_ref)
                _set_lifecycle(dec_db, dec_id, "ai_proposed")

                results = []
                def do_approve():
                    results.append(("approve", c.post(f"/api/v1/hitl/{dec_id}/approve", json={"actor": "h1", "justification": "a"}, headers=h).status_code))
                def do_reject():
                    results.append(("reject", c.post(f"/api/v1/hitl/{dec_id}/reject", json={"actor": "h2", "justification": "r"}, headers=h).status_code))

                t1 = threading.Thread(target=do_approve)
                t2 = threading.Thread(target=do_reject)
                t1.start()
                t2.start()
                t1.join()
                t2.join()

                codes = sorted([code for _, code in results])
                assert 200 in codes
                assert codes.count(200) == 1
                assert all(code in (200, 400, 409) for _, code in results)
                _, lc = _get_decision_row(dec_db, case_ref)
                assert lc in ("approved", "rejected")
                assert _count_hitl_audits(aud_db, dec_id) >= 1
            finally:
                restore()
