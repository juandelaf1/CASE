"""SQLite idempotency store with consumer/tenant/operation scoping.

Provides replay/conflict detection for evaluate operations when a security context is present.
In dev/autonomous mode without context, callers may skip persistent enforcement.

Recovery safety:
- `completed`: replay allowed when request hash matches.
- `in_progress`: blocks retries to prevent duplicate execution (may require reconciliation).
- `recovery_required` / `failed`: blocked (fail-closed) until explicitly reconciled.
Reconciliation must not release/re-execute blindly when business side effects may exist.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_DEFAULT_CONSUMER = "local-autonomous"
_DEFAULT_TENANT = "local"

BLOCKING_STATUSES = {"in_progress", "recovery_required", "failed", "reconciling"}


@dataclass
class IdempotencyRecord:
    status: str
    request_hash: str
    response_json: str | None
    status_code: int | None
    created_at: str | None = None
    updated_at: str | None = None
    operation_id: str | None = None
    correlation_id: str | None = None
    case_id: str | None = None
    decision_id: str | None = None


class SQLiteIdempotencyStore:
    def __init__(self, db_path: str = "case_audit.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                consumer_id TEXT NOT NULL,
                tenant_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                idempotency_key TEXT NOT NULL,
                request_hash TEXT NOT NULL,
                status TEXT NOT NULL,
                response_json TEXT,
                status_code INTEGER,
                recovery_note TEXT DEFAULT '',
                recovery_actor TEXT DEFAULT '',
                recovery_at TEXT,
                operation_id TEXT DEFAULT '',
                correlation_id TEXT DEFAULT '',
                case_id TEXT DEFAULT '',
                decision_id TEXT DEFAULT '',
                result_ref_json TEXT DEFAULT '',
                request_context_json TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (consumer_id, tenant_id, operation, idempotency_key)
            )
            """
        )
        self._ensure_columns(conn)
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_idem_consumer_tenant ON idempotency_keys(consumer_id, tenant_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_idem_status_updated ON idempotency_keys(status, updated_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_idem_operation_id ON idempotency_keys(operation_id)"
        )
        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_columns(conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(idempotency_keys)").fetchall()}
        for col, coldef in [
            ("recovery_note", "TEXT DEFAULT ''"),
            ("recovery_actor", "TEXT DEFAULT ''"),
            ("recovery_at", "TEXT"),
            ("operation_id", "TEXT DEFAULT ''"),
            ("correlation_id", "TEXT DEFAULT ''"),
            ("case_id", "TEXT DEFAULT ''"),
            ("decision_id", "TEXT DEFAULT ''"),
            ("result_ref_json", "TEXT DEFAULT ''"),
            ("request_context_json", "TEXT DEFAULT ''"),
        ]:
            if col not in cols:
                conn.execute(f"ALTER TABLE idempotency_keys ADD COLUMN {col} {coldef}")

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("SELECT 1 FROM idempotency_keys LIMIT 1")
            self._ensure_columns(conn)
            conn.commit()
        except sqlite3.OperationalError:
            conn.close()
            self._init_db()
            return
        conn.close()

    @staticmethod
    def hash_request(payload: Any) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _ctx_ids(security_context: Any) -> tuple[str, str]:
        if security_context is None:
            return _DEFAULT_CONSUMER, _DEFAULT_TENANT
        consumer = getattr(security_context, "storage_consumer_id", None) or getattr(security_context, "consumer_id", None) or _DEFAULT_CONSUMER
        tenant = getattr(security_context, "storage_tenant_id", None) or getattr(security_context, "tenant_id", None) or _DEFAULT_TENANT
        return str(consumer), str(tenant)

    def get(self, security_context: Any, operation: str, idempotency_key: str) -> IdempotencyRecord | None:
        self._ensure_tables()
        consumer_id, tenant_id = self._ctx_ids(security_context)
        conn = sqlite3.connect(self._db_path)
        row = conn.execute(
            """SELECT status, request_hash, response_json, status_code, created_at, updated_at,
                      operation_id, correlation_id, case_id, decision_id
               FROM idempotency_keys WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=?""",
            (consumer_id, tenant_id, operation, idempotency_key),
        ).fetchone()
        conn.close()
        if not row:
            return None
        return IdempotencyRecord(
            status=row[0], request_hash=row[1], response_json=row[2], status_code=row[3],
            created_at=row[4], updated_at=row[5],
            operation_id=row[6] or None, correlation_id=row[7] or None,
            case_id=row[8] or None, decision_id=row[9] or None,
        )

    def begin(
        self,
        security_context: Any,
        operation: str,
        idempotency_key: str,
        request_hash: str,
        operation_id: str | None = None,
        correlation_id: str | None = None,
        request_context: dict[str, Any] | None = None,
    ) -> tuple[bool, IdempotencyRecord | None]:
        """Try to start processing. Returns (acquired, record).

        - acquired=True: new in_progress record created; returned record contains operation_id.
        - acquired=False: existing record returned (conflict/replay/in-progress/recovery state).
        """
        self._ensure_tables()
        consumer_id, tenant_id = self._ctx_ids(security_context)
        if not operation_id:
            operation_id = f"op-{hashlib.sha256(f'{consumer_id}:{tenant_id}:{operation}:{idempotency_key}:{request_hash}'.encode()).hexdigest()[:24]}"
        conn = sqlite3.connect(self._db_path)
        req_ctx_json = json.dumps(request_context or {}, sort_keys=True, separators=(",", ":"), default=str)
        try:
            conn.execute(
                """INSERT INTO idempotency_keys
                   (consumer_id, tenant_id, operation, idempotency_key, request_hash, status, operation_id, correlation_id, request_context_json)
                   VALUES (?,?,?,?,?,?,?,?,?)""",
                (consumer_id, tenant_id, operation, idempotency_key, request_hash, "in_progress", operation_id, correlation_id or "", req_ctx_json),
            )
            conn.commit()
            conn.close()
            return True, IdempotencyRecord(
                status="in_progress", request_hash=request_hash, response_json=None, status_code=None,
                operation_id=operation_id, correlation_id=correlation_id or None,
            )
        except sqlite3.IntegrityError:
            conn.rollback()
            row = conn.execute(
                """SELECT status, request_hash, response_json, status_code, created_at, updated_at,
                          operation_id, correlation_id, case_id, decision_id
                   FROM idempotency_keys WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=?""",
                (consumer_id, tenant_id, operation, idempotency_key),
            ).fetchone()
            conn.close()
            if not row:
                return False, None
            return False, IdempotencyRecord(
                status=row[0], request_hash=row[1], response_json=row[2], status_code=row[3],
                created_at=row[4], updated_at=row[5],
                operation_id=row[6] or None, correlation_id=row[7] or None,
                case_id=row[8] or None, decision_id=row[9] or None,
            )

    def complete(
        self,
        security_context: Any,
        operation: str,
        idempotency_key: str,
        response_json: str,
        status_code: int = 200,
        case_id: str | None = None,
        decision_id: str | None = None,
        result_ref: dict[str, Any] | None = None,
    ) -> None:
        self._ensure_tables()
        consumer_id, tenant_id = self._ctx_ids(security_context)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """UPDATE idempotency_keys
               SET status='completed', response_json=?, status_code=?, case_id=COALESCE(NULLIF(?, ''), case_id),
                   decision_id=COALESCE(NULLIF(?, ''), decision_id),
                   result_ref_json=CASE WHEN ? IS NOT NULL AND ? != '' THEN ? ELSE result_ref_json END,
                   updated_at=CURRENT_TIMESTAMP
               WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=?""",
            (
                response_json, status_code, case_id or "", decision_id or "",
                result_ref is not None, json.dumps(result_ref) if result_ref is not None else "",
                json.dumps(result_ref) if result_ref is not None else "",
                consumer_id, tenant_id, operation, idempotency_key,
            ),
        )
        conn.commit()
        conn.close()

    def release(self, security_context: Any, operation: str, idempotency_key: str) -> None:
        """Release in-progress marker on failure so retries can proceed (best-effort).

        Safety: only removes `in_progress` records. Never releases completed or recovery states.
        Callers must not use this after business side effects may have been persisted.
        """
        self._ensure_tables()
        consumer_id, tenant_id = self._ctx_ids(security_context)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "DELETE FROM idempotency_keys WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=? AND status='in_progress'",
            (consumer_id, tenant_id, operation, idempotency_key),
        )
        conn.commit()
        conn.close()

    def mark_recovery_required(self, consumer_id: str, tenant_id: str, operation: str, idempotency_key: str, actor: str, note: str) -> bool:
        """Fail-closed transition for stuck/incomplete records: blocks retries until reconciled.

        CAS-like: only transitions allowed source states.
        """
        self._ensure_tables()
        conn = sqlite3.connect(self._db_path)
        cur = conn.execute(
            """
            UPDATE idempotency_keys
            SET status='recovery_required', recovery_actor=?, recovery_note=?, recovery_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
            WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=? AND status IN ('in_progress','reconciling','failed')
            """,
            (actor, note, consumer_id, tenant_id, operation, idempotency_key),
        )
        conn.commit()
        changed = cur.rowcount > 0
        conn.close()
        return changed

    def get_by_key(self, consumer_id: str, tenant_id: str, operation: str, idempotency_key: str) -> dict[str, Any] | None:
        """Return raw idempotency record by scoped key for evidence inspection (operator/internal use)."""
        self._ensure_tables()
        conn = sqlite3.connect(self._db_path)
        row = conn.execute(
            """SELECT consumer_id, tenant_id, operation, idempotency_key, request_hash, status,
                      response_json, status_code, operation_id, correlation_id, case_id, decision_id,
                      result_ref_json, request_context_json, recovery_note, recovery_actor, recovery_at, created_at, updated_at
               FROM idempotency_keys WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=?""",
            (consumer_id, tenant_id, operation, idempotency_key),
        ).fetchone()
        conn.close()
        if not row:
            return None
        keys = [
            "consumer_id","tenant_id","operation","idempotency_key","request_hash","status",
            "response_json","status_code","operation_id","correlation_id","case_id","decision_id",
            "result_ref_json","request_context_json","recovery_note","recovery_actor","recovery_at","created_at","updated_at",
        ]
        rec = dict(zip(keys, row, strict=False))
        try:
            rec["result_ref"] = json.loads(rec.get("result_ref_json") or "{}") if rec.get("result_ref_json") else {}
        except Exception:
            rec["result_ref"] = {}
        try:
            rec["request_context"] = json.loads(rec.get("request_context_json") or "{}") if rec.get("request_context_json") else {}
        except Exception:
            rec["request_context"] = {}
        return rec

    def _find_decision_evidence(self, consumer_id: str, tenant_id: str, operation_id: str, case_id: str = "") -> dict[str, Any] | None:
        """Best-effort lookup of persisted decision by operation_id in same DB/context (evidence-based)."""
        if not operation_id:
            return None
        conn = sqlite3.connect(self._db_path)
        try:
            # Check table exists
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='decisions'").fetchone() is None:
                return None
            cols = {r[1] for r in conn.execute("PRAGMA table_info(decisions)").fetchall()}
            # Try by operation_id + consumer/tenant
            if "operation_id" in cols:
                row = conn.execute(
                    """SELECT decision_id, case_id, domain, action, reason, urgency, confidence, evidence_summary,
                              decision_rationale, decision_factors, summary, lifecycle, processing_time_ms, metadata,
                              operation_id, correlation_id, consumer_id, tenant_id
                       FROM decisions
                       WHERE operation_id=? AND consumer_id=? AND tenant_id=?
                       ORDER BY created_at DESC LIMIT 1""",
                    (operation_id, consumer_id, tenant_id),
                ).fetchone()
                if row:
                    return {
                        "decision_id": row[0], "case_id": row[1], "domain": row[2], "action": row[3],
                        "reason": row[4], "urgency": row[5], "confidence": row[6], "evidence_summary": row[7],
                        "decision_rationale": row[8], "decision_factors": row[9], "summary": row[10],
                        "lifecycle": row[11], "processing_time_ms": row[12], "metadata": row[13],
                        "operation_id": row[14], "correlation_id": row[15], "consumer_id": row[16], "tenant_id": row[17],
                    }
            # Fallback: by case_id if provided and context matches
            if case_id:
                row = conn.execute(
                    """SELECT decision_id, case_id, domain, action, reason, urgency, confidence, evidence_summary,
                              decision_rationale, decision_factors, summary, lifecycle, processing_time_ms, metadata,
                              COALESCE(operation_id,''), COALESCE(correlation_id,''), COALESCE(consumer_id,''), COALESCE(tenant_id,'')
                       FROM decisions
                       WHERE case_id=? AND consumer_id=? AND tenant_id=?
                       ORDER BY created_at DESC LIMIT 1""",
                    (case_id, consumer_id, tenant_id),
                ).fetchone()
                if row:
                    return {
                        "decision_id": row[0], "case_id": row[1], "domain": row[2], "action": row[3],
                        "reason": row[4], "urgency": row[5], "confidence": row[6], "evidence_summary": row[7],
                        "decision_rationale": row[8], "decision_factors": row[9], "summary": row[10],
                        "lifecycle": row[11], "processing_time_ms": row[12], "metadata": row[13],
                        "operation_id": row[14], "correlation_id": row[15], "consumer_id": row[16], "tenant_id": row[17],
                    }
            return None
        finally:
            conn.close()

    def _has_audit_evidence(self, case_id: str, consumer_id: str, tenant_id: str) -> bool:
        """Check if audit events exist for case in same context (supporting evidence)."""
        if not case_id:
            return False
        conn = sqlite3.connect(self._db_path)
        try:
            if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='audit_events'").fetchone() is None:
                return False
            row = conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE case_id=? AND consumer_id=? AND tenant_id=?",
                (case_id, consumer_id, tenant_id),
            ).fetchone()
            return bool(row and int(row[0]) > 0)
        finally:
            conn.close()

    def _reconstruct_response_from_decision(self, rec: dict[str, Any], dec: dict[str, Any]) -> str | None:
        """Reconstruct evaluate response from persisted decision + stored request context.

        Returns JSON string only when reconstruction is deterministic from persisted evidence.
        """
        req_ctx = rec.get("request_context") or {}
        if not isinstance(req_ctx, dict) or not req_ctx:
            return None
        try:
            factors = json.loads(dec.get("decision_factors") or "[]")
        except Exception:
            factors = []
        if not isinstance(factors, list):
            factors = []
        try:
            dec_meta = json.loads(dec.get("metadata") or "{}") if isinstance(dec.get("metadata"), str) else (dec.get("metadata") or {})
        except Exception:
            dec_meta = {}
        if not isinstance(dec_meta, dict):
            dec_meta = {}
        lifecycle = str(dec.get("lifecycle") or "")
        requires_human_review = lifecycle in {"AI_PROPOSED", "UNDER_REVIEW", "PENDING_REVIEW", "ai_proposed", "under_review"}
        status = "pending_review" if requires_human_review else "ok"
        operation_id = rec.get("operation_id") or dec.get("operation_id") or ""
        correlation_id = rec.get("correlation_id") or req_ctx.get("correlation_id") or dec.get("correlation_id") or ""
        idem_key = rec.get("idempotency_key")
        out: dict[str, Any] = {
            "contract_version": req_ctx.get("contract_version") or "case-eval/v0.1-draft",
            "capability_id": req_ctx.get("capability_id") or "case.evaluate",
            "correlation_id": correlation_id,
            "idempotency_key": idem_key,
            "operation_id": operation_id,
            "status": status,
            "data_status": req_ctx.get("data_status") or "derived",
            "provenance": {
                **(req_ctx.get("provenance") or {}),
                "provider": "case",
                "mapping": "recovered_from_decision_evidence",
                "upstream_lifecycle": lifecycle,
                "recovery": "evidence_based",
            },
            "result": {
                "decision_type": "recommendation",
                "case_ref": dec.get("case_id"),
                "decision_id": dec.get("decision_id"),
                "action": dec.get("action"),
                "urgency": dec.get("urgency"),
                "confidence": float(dec.get("confidence") or 0.0),
                "risks": [],
                "decision_factors": list(factors),
                "evidence_summary": dec.get("evidence_summary") or "",
                "requires_human_review": requires_human_review,
                "lifecycle_hint": lifecycle,
                "reason": dec.get("reason") or "",
                "summary": dec.get("summary") or "",
                "decision_rationale": dec.get("decision_rationale") or "",
                "processing_time_ms": float(dec.get("processing_time_ms") or 0.0),
                "operation_id": operation_id,
            },
            "warnings": [],
            "errors": [],
        }
        # Preserve additional decision metadata traceability without fabricating business fields
        if dec_meta.get("provider_info"):
            out["provider_info"] = dec_meta.get("provider_info")
        return json.dumps(out, sort_keys=True, separators=(",", ":"), default=str)

    def complete_reconciled_from_evidence(
        self,
        consumer_id: str,
        tenant_id: str,
        operation: str,
        idempotency_key: str,
        actor: str,
        note: str,
        expected_request_hash: str | None = None,
        expected_operation_id: str | None = None,
        expected_status: str | None = "recovery_required",
    ) -> tuple[bool, str]:
        """Evidence-based reconciliation completion.

        Recovers by:
        1) persisted idempotency response_json (verified), or
        2) deterministic reconstruction from persisted decision evidence linked by operation_id/context
           when response_json is missing but decision (and supporting evidence) is verifiable.

        Does not accept operator-supplied response content. CAS on expected status.
        Returns (ok, reason_code).
        """
        self._ensure_tables()
        rec = self.get_by_key(consumer_id, tenant_id, operation, idempotency_key)
        if not rec:
            return False, "NOT_FOUND"
        if expected_request_hash and rec.get("request_hash") != expected_request_hash:
            return False, "REQUEST_HASH_MISMATCH"
        if expected_operation_id and (rec.get("operation_id") or "") != expected_operation_id:
            return False, "OPERATION_ID_MISMATCH"
        status = rec.get("status")
        if expected_status and status != expected_status:
            return False, f"STATUS_MISMATCH:{status}"
        if status == "completed":
            return True, "ALREADY_COMPLETED"

        response_json = rec.get("response_json")
        reconstructed = False
        decision_evidence: dict[str, Any] | None = None

        if not response_json:
            op_id = rec.get("operation_id") or ""
            if not op_id:
                return False, "UNCERTAIN_NO_OPERATION_ID"
            decision_evidence = self._find_decision_evidence(consumer_id, tenant_id, op_id, rec.get("case_id") or "")
            if not decision_evidence:
                # No verifiable persisted business result linked to operation -> uncertain/incomplete, fail-closed
                return False, "NO_VERIFIABLE_DECISION_EVIDENCE"
            # Verify linkage consistency
            dec_op = str(decision_evidence.get("operation_id") or "")
            if dec_op and dec_op != op_id:
                return False, "DECISION_OPERATION_MISMATCH"
            if (decision_evidence.get("consumer_id") or "") != consumer_id or (decision_evidence.get("tenant_id") or "") != tenant_id:
                return False, "DECISION_CONTEXT_MISMATCH"
            # Require supporting audit evidence for stronger coherence (conservative)
            if not self._has_audit_evidence(str(decision_evidence.get("case_id") or ""), consumer_id, tenant_id):
                return False, "INSUFFICIENT_AUDIT_EVIDENCE"
            response_json = self._reconstruct_response_from_decision(rec, decision_evidence)
            if not response_json:
                return False, "CANNOT_RECONSTRUCT_DETERMINISTIC_RESPONSE"
            reconstructed = True

        try:
            parsed = json.loads(response_json)
        except Exception:
            return False, "PERSISTED_RESPONSE_INVALID"
        if not isinstance(parsed, dict):
            return False, "PERSISTED_RESPONSE_INVALID"

        stored_case = rec.get("case_id") or (decision_evidence.get("case_id") if decision_evidence else "") or ""
        stored_op = rec.get("operation_id") or ""
        resp_case = ""
        resp_op = ""
        try:
            resp_case = str((parsed.get("result") or {}).get("case_ref") or parsed.get("case_ref") or "")
            resp_op = str(parsed.get("operation_id") or (parsed.get("result") or {}).get("operation_id") or "")
        except Exception:
            pass
        if stored_case and resp_case and stored_case != resp_case:
            return False, "CASE_ID_EVIDENCE_MISMATCH"
        if stored_op and resp_op and stored_op != resp_op:
            return False, "OPERATION_ID_EVIDENCE_MISMATCH"

        case_id = stored_case or resp_case or (decision_evidence.get("case_id") if decision_evidence else "") or ""
        decision_id = rec.get("decision_id") or (parsed.get("result") or {}).get("decision_id") or (decision_evidence.get("decision_id") if decision_evidence else "") or ""
        result_ref = {
            "case_ref": case_id,
            "decision_id": decision_id,
            "correlation_id": rec.get("correlation_id"),
            "operation_id": stored_op,
            "reconstructed": reconstructed,
        }
        conn = sqlite3.connect(self._db_path)
        if reconstructed:
            cur = conn.execute(
                """
                UPDATE idempotency_keys
                SET status='completed', response_json=?, status_code=200, case_id=?, decision_id=?, result_ref_json=?,
                    recovery_actor=?, recovery_note=?, recovery_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=? AND status=?
                """,
                (
                    response_json, case_id, decision_id, json.dumps(result_ref, sort_keys=True, default=str),
                    actor, note or "evidence-based reconstruction", consumer_id, tenant_id, operation, idempotency_key, status,
                ),
            )
        else:
            cur = conn.execute(
                """
                UPDATE idempotency_keys
                SET status='completed', recovery_actor=?, recovery_note=?, recovery_at=CURRENT_TIMESTAMP, updated_at=CURRENT_TIMESTAMP
                WHERE consumer_id=? AND tenant_id=? AND operation=? AND idempotency_key=? AND status=? AND response_json IS NOT NULL
                """,
                (actor, note or "evidence-based reconciliation", consumer_id, tenant_id, operation, idempotency_key, status),
            )
        conn.commit()
        changed = cur.rowcount > 0
        conn.close()
        if not changed:
            return False, "CAS_CONFLICT"
        return (True, "COMPLETED_FROM_DECISION_EVIDENCE" if reconstructed else "COMPLETED_FROM_PERSISTED_EVIDENCE")

    def complete_reconciled(self, consumer_id: str, tenant_id: str, operation: str, idempotency_key: str, response_json: str, actor: str, note: str, status_code: int = 200) -> bool:
        """Legacy unsafe path disabled. Use complete_reconciled_from_evidence."""
        raise RuntimeError(
            "Unverified reconciliation completion is not permitted. "
            "Use evidence-based recovery (complete_reconciled_from_evidence) from verified persisted evidence."
        )

    def list_stale_in_progress(self, older_than_seconds: int = 300) -> list[dict[str, Any]]:
        """List in_progress records older than threshold for operator review (no automatic release)."""
        self._ensure_tables()
        conn = sqlite3.connect(self._db_path)
        rows = conn.execute(
            """
            SELECT consumer_id, tenant_id, operation, idempotency_key, request_hash, status, created_at, updated_at
            FROM idempotency_keys
            WHERE status='in_progress' AND (julianday('now') - julianday(updated_at)) * 86400 >= ?
            ORDER BY updated_at ASC
            """,
            (float(older_than_seconds),),
        ).fetchall()
        conn.close()
        return [
            {
                "consumer_id": r[0],
                "tenant_id": r[1],
                "operation": r[2],
                "idempotency_key": r[3],
                "request_hash": r[4],
                "status": r[5],
                "created_at": r[6],
                "updated_at": r[7],
            }
            for r in rows
        ]

