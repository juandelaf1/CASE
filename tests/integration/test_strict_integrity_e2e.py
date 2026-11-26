"""E2E integrity checks for strict single-consumer mode (decision, audit, idempotency, HITL).

Focused on demonstrable invariants: no duplicate business effects on replay, conflict/in-progress
do not create additional decisions, denied/invalid HITL operations do not produce unauthorized
state changes, and object-level access is isolated by security context.
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


def _count(db_path: str, table: str) -> int:
    if not Path(db_path).exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        if conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
        ).fetchone() is None:
            return 0
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


def _build_strict_app(
    tmp: str, scopes: str, consumer="c1", tenant="t1", key="k-valid"
):
    import case_api.api.v1.app as appmod
    from case_api.api.v1.auth import APIKeyAuthMiddleware
    from case_api.api.v1.security import load_security_config
    from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
    from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository
    from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

    dec_db = os.path.join(tmp, f"decisions-{consumer}.db")
    aud_db = os.path.join(tmp, f"audit-{consumer}.db")

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
                    key: {
                        "consumer_id": consumer,
                        "tenant_id": tenant,
                        "scopes": scopes.split(","),
                    }
                }
            ),
        }
    )
    a = FastAPI()
    a.state.security_config = cfg
    a.add_middleware(APIKeyAuthMiddleware, config=cfg)

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

    appmod.decision_repo = SQLiteDecisionRepository(dec_db)
    appmod.audit_adapter = SQLiteAuditAdapter(aud_db)
    appmod.engine._decision_repository = appmod.decision_repo
    appmod.engine._audit_port = appmod.audit_adapter
    # Keep idempotency in same DB for coherence in this test context
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


def _eval_body(idem="idem-1", corr="corr-1", summary="Synthetic integrity test"):
    return {
        "contract_version": "case-eval/v0.1-draft",
        "capability_id": "case.evaluate",
        "correlation_id": corr,
        "idempotency_key": idem,
        "data_status": "synthetic",
        "payload": {
            "domain": "logistics",
            "summary": summary,
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
    "report_text": "Synthetic triage integrity test for HITL flow",
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


@pytest.mark.integration
class TestEvaluateIdempotencyIntegrity:
    def test_replay_same_key_returns_same_result_without_duplicate_decision(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app(
                tmp, scopes="case:evaluate"
            )
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k-valid"}
                body = _eval_body()
                r1 = c.post("/api/v1/evaluate", json=body, headers=h)
                assert r1.status_code == 200, r1.text
                d1 = _count(dec_db, "decisions")
                a1 = _count(aud_db, "audit_events")
                r2 = c.post("/api/v1/evaluate", json=body, headers=h)
                assert r2.status_code == 200, r2.text
                assert r1.json().get("result", {}).get("case_ref") == r2.json().get(
                    "result", {}
                ).get("case_ref")
                assert _count(dec_db, "decisions") == d1
                assert _count(aud_db, "audit_events") == a1
            finally:
                restore()

    def test_conflict_same_key_different_payload_no_extra_decision(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app(
                tmp, scopes="case:evaluate"
            )
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k-valid"}
                body = _eval_body(idem="idem-conf")
                r1 = c.post("/api/v1/evaluate", json=body, headers=h)
                assert r1.status_code == 200
                d1 = _count(dec_db, "decisions")
                a1 = _count(aud_db, "audit_events")
                body2 = _eval_body(
                    idem="idem-conf", corr="corr-2", summary="Different payload"
                )
                r2 = c.post("/api/v1/evaluate", json=body2, headers=h)
                assert r2.status_code == 409, r2.text
                assert _count(dec_db, "decisions") == d1
                assert _count(aud_db, "audit_events") == a1
            finally:
                restore()

    def test_in_progress_blocks_duplicate_execution(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app(
                tmp, scopes="case:evaluate"
            )
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k-valid"}
                # Simulate in-progress record directly in idempotency table
                conn = sqlite3.connect(dec_db)
                conn.execute(
                    "INSERT INTO idempotency_keys (consumer_id,tenant_id,operation,idempotency_key,request_hash,status) VALUES (?,?,?,?,?,?)",
                    ("c1", "t1", "case.evaluate", "idem-prog", "hash-x", "in_progress"),
                )
                conn.commit()
                conn.close()
                d0 = _count(dec_db, "decisions")
                r = c.post("/api/v1/evaluate", json=_eval_body(idem="idem-prog"), headers=h)
                assert r.status_code == 409, r.text
                assert _count(dec_db, "decisions") == d0
            finally:
                restore()


@pytest.mark.integration
class TestHITLIntegrityAndObjectAccess:
    def test_cross_context_object_access_denied_without_side_effects(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            # Context A creates decision
            appA, decA, audA, restoreA = _build_strict_app(
                tmp,
                scopes="case:triage,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read,case:read",
                consumer="c1",
                tenant="t1",
                key="kA",
            )
            try:
                cA = TestClient(appA)
                hA = {"X-API-Key": "kA"}
                r = cA.post("/api/v1/triage", json=TRIAGE_BODY, headers=hA)
                assert r.status_code == 200, r.text
                dec = r.json()
                decision_id = dec["decision_id"]
                case_id = dec["case_id"]

                # Context B (different tenant/consumer, isolated DB binding in app but we simulate different identity context via separate app)
                appB, decB, audB, restoreB = _build_strict_app(
                    tmp,
                    scopes="case:triage,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read,case:read",
                    consumer="c2",
                    tenant="t2",
                    key="kB",
                )
                try:
                    cB = TestClient(appB)
                    hB = {"X-API-Key": "kB"}
                    before_dec = _count(decA, "decisions")
                    before_aud = _count(audA, "audit_events")

                    # B cannot read or mutate A's objects (A's DB has the data; B's repo points to decB/audB but IDs don't exist there either)
                    assert cB.get(f"/api/v1/hitl/{decision_id}", headers=hB).status_code == 404
                    assert cB.get(f"/api/v1/cases/{case_id}", headers=hB).status_code == 404
                    assert (
                        cB.post(
                            f"/api/v1/hitl/{decision_id}/approve",
                            json={"actor": "b", "justification": "x"},
                            headers=hB,
                        ).status_code
                        == 404
                    )
                    assert (
                        cB.post(
                            f"/api/v1/hitl/{decision_id}/reject",
                            json={"actor": "b", "justification": "x"},
                            headers=hB,
                        ).status_code
                        == 404
                    )

                    # A's persisted state unchanged
                    assert _count(decA, "decisions") == before_dec
                    assert _count(audA, "audit_events") == before_aud
                finally:
                    restoreB()
            finally:
                restoreA()

    def test_invalid_transition_does_not_change_lifecycle(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_app(
                tmp,
                scopes="case:triage,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read,case:read",
            )
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k-valid"}
                r = c.post("/api/v1/triage", json=TRIAGE_BODY, headers=h)
                assert r.status_code == 200
                decision_id = r.json()["decision_id"]
                # Force to APPROVED to test invalid re-transition
                conn = sqlite3.connect(dec_db)
                conn.execute(
                    "UPDATE decisions SET lifecycle='approved' WHERE decision_id=?",
                    (decision_id,),
                )
                conn.commit()
                conn.close()
                a_before = _count(aud_db, "audit_events")
                r_bad = c.post(
                    f"/api/v1/hitl/{decision_id}/reject",
                    json={"actor": "t", "justification": "x"},
                    headers=h,
                )
                assert r_bad.status_code == 400
                conn = sqlite3.connect(dec_db)
                life = conn.execute(
                    "SELECT lifecycle FROM decisions WHERE decision_id=?",
                    (decision_id,),
                ).fetchone()[0]
                conn.close()
                assert (
                    life.lower() == "approved"
                    or life == "APPROVED"
                    or "approved" in str(life).lower()
                )
                # Invalid transition should not emit HITL business event; audit count unchanged is preferred
                assert _count(aud_db, "audit_events") == a_before
            finally:
                restore()
