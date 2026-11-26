"""Idempotency recovery behavior (safe, fail-closed)."""

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


def _build_strict_eval_app(tmp: str, scopes: str = "case:evaluate", consumer="c1", tenant="t1", key="k-valid"):
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

    appmod.decision_repo = SQLiteDecisionRepository(dec_db)
    appmod.audit_adapter = SQLiteAuditAdapter(aud_db)
    appmod.engine._decision_repository = appmod.decision_repo
    appmod.engine._audit_port = appmod.audit_adapter
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


def _eval_body(idem="idem-r1", corr="corr-r1", summary="Synthetic recovery test"):
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
            "evidence": [{"id": "e1", "type": "text", "content": "synthetic", "source": "test", "confidence": 0.5}],
            "provider": "mock",
            "metadata": {"synthetic": "true"},
        },
    }


def _bound_hash_for_strict_request(body: dict, consumer="c1", tenant="t1", scopes=("case:evaluate",)):
    """Compute idempotency hash as strict server-bound evaluate request will."""
    from case_api.api.v1.app import EvaluateEnvelopeRequest
    from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

    req = EvaluateEnvelopeRequest(**body)
    bound = req.model_copy(
        update={
            "caller": {"consumer_id": consumer, **(req.caller or {})},
            "scopes": sorted(scopes),
            "tenant_context": {"tenant_id": tenant} if tenant else None,
            "organization_context": None,
        }
    )
    return SQLiteIdempotencyStore.hash_request(bound.model_dump(mode="json"))


def _count(db_path: str, table: str) -> int:
    if not Path(db_path).exists():
        return 0
    conn = sqlite3.connect(db_path)
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
            return 0
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


@pytest.mark.integration
class TestIdempotencyRecovery:
    def test_recovery_required_blocks_retry_without_duplicate_execution(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _build_strict_eval_app(tmp)
            try:
                c = TestClient(app)
                h = {"X-API-Key": "k-valid"}
                body = _eval_body(idem="idem-rec")
                req_hash = _bound_hash_for_strict_request(body)
                conn = sqlite3.connect(dec_db)
                conn.execute(
                    "INSERT INTO idempotency_keys (consumer_id,tenant_id,operation,idempotency_key,request_hash,status) VALUES (?,?,?,?,?,?)",
                    ("c1", "t1", "case.evaluate", "idem-rec", req_hash, "recovery_required"),
                )
                conn.commit()
                conn.close()
                before = _count(dec_db, "decisions")
                r = c.post("/api/v1/evaluate", json=body, headers=h)
                assert r.status_code == 409, r.text
                assert r.json().get("detail", {}).get("code") == "IDEMPOTENCY_RECOVERY_REQUIRED"
                assert _count(dec_db, "decisions") == before
            finally:
                restore()

    def test_store_marks_stale_in_progress_as_recovery_required(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "idem.db")
            from case_core.contracts.security import SecurityContext
            from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

            store = SQLiteIdempotencyStore(db)
            ctx = SecurityContext(consumer_id="c1", tenant_id="t1", mode="shared")
            store.begin(ctx, "case.evaluate", "k1", "h1")
            # force old timestamp
            conn = sqlite3.connect(db)
            conn.execute("UPDATE idempotency_keys SET updated_at=datetime('now','-1 hour')")
            conn.commit()
            conn.close()
            stale = store.list_stale_in_progress(older_than_seconds=60)
            assert len(stale) == 1
            ok = store.mark_recovery_required("c1", "t1", "case.evaluate", "k1", "operator", "stale")
            assert ok is True
            rec = store.get(ctx, "case.evaluate", "k1")
            assert rec is not None and rec.status == "recovery_required"

    def test_unverified_completion_is_refused(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "idem.db")
            from case_core.contracts.security import SecurityContext
            from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

            store = SQLiteIdempotencyStore(db)
            ctx = SecurityContext(consumer_id="c1", tenant_id="t1", mode="shared")
            store.begin(ctx, "case.evaluate", "k1", "h1")
            with pytest.raises(RuntimeError, match="Unverified reconciliation completion is not permitted"):
                store.complete_reconciled(
                    "c1",
                    "t1",
                    "case.evaluate",
                    "k1",
                    response_json="{}",
                    actor="operator",
                    note="fabricated",
                )
            # Record remains non-completed (still in_progress) and cannot be replayed as completed
            rec = store.get(ctx, "case.evaluate", "k1")
            assert rec is not None and rec.status == "in_progress"
    def test_evidence_based_completion_recovers_from_persisted_response(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "idem.db")
            from case_core.contracts.security import SecurityContext
            from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

            store = SQLiteIdempotencyStore(db)
            ctx = SecurityContext(consumer_id="c1", tenant_id="t1", mode="shared")
            store.begin(ctx, "case.evaluate", "k1", "h1", operation_id="op-1", correlation_id="corr-1")
            # simulate: response persisted but completion transition failed (evidence exists)
            conn = sqlite3.connect(db)
            conn.execute(
                "UPDATE idempotency_keys SET status='recovery_required', response_json=?, case_id=?, decision_id=? WHERE idempotency_key='k1'",
                (json.dumps({"operation_id": "op-1", "result": {"case_ref": "case-1", "operation_id": "op-1"}}), "case-1", "dec-1"),
            )
            conn.commit()
            conn.close()
            ok, reason = store.complete_reconciled_from_evidence("c1", "t1", "case.evaluate", "k1", actor="op", note="verified", expected_request_hash="h1", expected_operation_id="op-1")
            assert ok is True, reason
            assert reason in ("COMPLETED_FROM_PERSISTED_EVIDENCE", "ALREADY_COMPLETED")
            rec = store.get(ctx, "case.evaluate", "k1")
            assert rec is not None and rec.status == "completed" and rec.operation_id == "op-1"

    def test_evidence_based_completion_fails_without_persisted_response(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "idem.db")
            from case_core.contracts.security import SecurityContext
            from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

            store = SQLiteIdempotencyStore(db)
            ctx = SecurityContext(consumer_id="c1", tenant_id="t1", mode="shared")
            store.begin(ctx, "case.evaluate", "k1", "h1")
            store.mark_recovery_required("c1", "t1", "case.evaluate", "k1", "op", "stale")
            ok, reason = store.complete_reconciled_from_evidence("c1", "t1", "case.evaluate", "k1", actor="op", note="x")
            assert ok is False
            assert reason in ("NO_PERSISTED_RESPONSE_EVIDENCE", "NO_VERIFIABLE_DECISION_EVIDENCE", "UNCERTAIN_NO_OPERATION_ID")
            rec = store.get(ctx, "case.evaluate", "k1")
            assert rec is not None and rec.status == "recovery_required"
    def test_evidence_based_completion_reconstructs_from_persisted_decision(self):
        """P0: when idempotency has no response_json but decision+audit are persisted with matching operation_id/context, recover deterministically."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            db = os.path.join(tmp, "case.db")
            from case_core.contracts.audit import AuditEvent
            from case_core.contracts.decision import TriageDecision
            from case_core.contracts.lifecycle import DecisionLifecycle
            from case_core.contracts.security import SecurityContext
            from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
            from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository
            from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

            store = SQLiteIdempotencyStore(db)
            dec_repo = SQLiteDecisionRepository(db)
            audit = SQLiteAuditAdapter(db)
            ctx = SecurityContext(consumer_id="c1", tenant_id="t1", mode="shared")
            op_id = "op-rec-dec-1"
            corr = "corr-rec-dec-1"
            case_id = "CASE-REC1"
            dec_id = "dec-CASE-REC1"
            req_ctx = {
                "contract_version": "case-eval/v0.1-draft",
                "capability_id": "case.evaluate",
                "correlation_id": corr,
                "idempotency_key": "k-dec",
                "data_status": "synthetic",
                "provenance": {"source": "test"},
            }
            store.begin(ctx, "case.evaluate", "k-dec", "h-dec", operation_id=op_id, correlation_id=corr, request_context=req_ctx)
            # persist decision and audit evidence (as if evaluation completed but idempotency complete failed)
            import asyncio
            async def _seed():
                decision = TriageDecision(
                    decision_id=dec_id,
                    case_id=case_id,
                    domain="logistics",
                    action="approve",
                    reason="evidence-based recovery test decision reason",
                    urgency="MEDIUM",
                    confidence=0.8,
                    evidence_summary="synthetic evidence summary",
                    decision_rationale="rationale for recovery test",
                    decision_factors=["factor1"],
                    summary="decision summary for recovery test case",
                    lifecycle=DecisionLifecycle.AI_PROPOSED,
                    processing_time_ms=12.3,
                    metadata={"operation_id": op_id, "correlation_id": corr},
                    operation_id=op_id,
                )
                await dec_repo.save_decision(decision, security_context=ctx)
                await audit.log_event(AuditEvent(
                    event_id="ae-rec-1", case_id=case_id, decision_id=dec_id, event_type="FINAL_DECISION",
                    timestamp="2026-11-11T00:00:00Z", details={"ok": True}, actor="c1", correlation_id=corr, operation_id=op_id,
                ), security_context=ctx)
            asyncio.run(_seed())
            # mark recovery_required (stuck in_progress scenario)
            store.mark_recovery_required("c1", "t1", "case.evaluate", "k-dec", "operator", "stuck after persist")
            ok, reason = store.complete_reconciled_from_evidence(
                "c1", "t1", "case.evaluate", "k-dec", actor="operator", note="recovered from decision",
                expected_request_hash="h-dec", expected_operation_id=op_id,
            )
            assert ok is True, reason
            assert reason == "COMPLETED_FROM_DECISION_EVIDENCE"
            rec = store.get_by_key("c1", "t1", "case.evaluate", "k-dec")
            assert rec is not None and rec["status"] == "completed"
            assert rec.get("response_json")
            resp = json.loads(rec["response_json"])
            assert resp.get("operation_id") == op_id
            assert resp.get("correlation_id") == corr
            assert (resp.get("result") or {}).get("case_ref") == case_id
            assert (resp.get("result") or {}).get("decision_id") == dec_id
            assert (resp.get("result") or {}).get("action") == "approve"
