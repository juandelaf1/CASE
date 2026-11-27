import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from case_core.contracts.decision import AIProposal, HumanOverride, TriageDecision
from case_core.contracts.error import CASEError
from case_core.contracts.lifecycle import DecisionLifecycle
from case_core.ports.decision_repository import DecisionRepositoryPort

_DEFAULT_CONSUMER = "local-autonomous"
_DEFAULT_TENANT = "local"

_DECISION_COLS = [
    "decision_id", "case_id", "domain", "action", "reason", "urgency", "confidence",
    "evidence_summary", "decision_rationale", "decision_factors", "summary", "error",
    "lifecycle", "processing_time_ms", "metadata", "original_ai_proposal", "human_override",
    "consumer_id", "tenant_id", "organization_id", "operation_id", "correlation_id",
    "created_at", "updated_at",
]


class SQLiteDecisionRepository(DecisionRepositoryPort):
    def __init__(self, db_path: str = "case_audit.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                domain TEXT NOT NULL,
                action TEXT NOT NULL,
                reason TEXT NOT NULL,
                urgency TEXT NOT NULL,
                confidence REAL NOT NULL,
                evidence_summary TEXT NOT NULL,
                decision_rationale TEXT DEFAULT '',
                decision_factors TEXT DEFAULT '[]',
                summary TEXT DEFAULT '',
                error TEXT,
                lifecycle TEXT NOT NULL DEFAULT 'ai_proposed',
                processing_time_ms REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}',
                original_ai_proposal TEXT DEFAULT '{}',
                human_override TEXT,
                consumer_id TEXT DEFAULT '',
                tenant_id TEXT DEFAULT '',
                organization_id TEXT DEFAULT '',
                operation_id TEXT DEFAULT '',
                correlation_id TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._ensure_columns(conn)
        conn.execute(
            "UPDATE decisions SET consumer_id = ? WHERE consumer_id IS NULL OR consumer_id = ''",
            (_DEFAULT_CONSUMER,),
        )
        conn.execute(
            "UPDATE decisions SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''",
            (_DEFAULT_TENANT,),
        )
        self._ensure_indexes(conn)
        conn.commit()
        conn.close()

    @staticmethod
    def _ensure_columns(conn: sqlite3.Connection) -> None:
        cols = {row[1] for row in conn.execute("PRAGMA table_info(decisions)").fetchall()}
        for col, coldef in [
            ("original_ai_proposal", "TEXT DEFAULT '{}'"),
            ("human_override", "TEXT"),
            ("decision_rationale", "TEXT DEFAULT ''"),
            ("decision_factors", "TEXT DEFAULT '[]'"),
            ("summary", "TEXT DEFAULT ''"),
            ("error", "TEXT"),
            ("consumer_id", "TEXT DEFAULT ''"),
            ("tenant_id", "TEXT DEFAULT ''"),
            ("organization_id", "TEXT DEFAULT ''"),
            ("operation_id", "TEXT DEFAULT ''"),
            ("correlation_id", "TEXT DEFAULT ''"),
        ]:
            if col not in cols:
                try:
                    conn.execute(f"ALTER TABLE decisions ADD COLUMN {col} {coldef}")
                except sqlite3.OperationalError:
                    pass

    @staticmethod
    def _ensure_indexes(conn: sqlite3.Connection) -> None:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_case_id ON decisions(case_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_lifecycle ON decisions(lifecycle)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_consumer_tenant ON decisions(consumer_id, tenant_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_tenant_case ON decisions(tenant_id, case_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_operation_id ON decisions(operation_id)")

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("SELECT 1 FROM decisions LIMIT 1")
            self._ensure_columns(conn)
            conn.execute("UPDATE decisions SET consumer_id = ? WHERE consumer_id IS NULL OR consumer_id = ''", (_DEFAULT_CONSUMER,))
            conn.execute("UPDATE decisions SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''", (_DEFAULT_TENANT,))
            self._ensure_indexes(conn)
            conn.commit()
        except sqlite3.OperationalError:
            conn.close()
            self._init_db()
            return
        conn.close()

    @staticmethod
    def _ctx_ids(security_context: Any) -> tuple[str, str, str]:
        if security_context is None:
            return _DEFAULT_CONSUMER, _DEFAULT_TENANT, ""
        consumer = getattr(security_context, "storage_consumer_id", None) or getattr(security_context, "consumer_id", None) or _DEFAULT_CONSUMER
        tenant = getattr(security_context, "storage_tenant_id", None) or getattr(security_context, "tenant_id", None) or _DEFAULT_TENANT
        org = getattr(security_context, "storage_organization_id", None) or getattr(security_context, "organization_id", None) or ""
        return str(consumer), str(tenant), str(org)

    @staticmethod
    def _context_filter(security_context: Any) -> tuple[str, tuple[Any, ...]]:
        if security_context is None:
            return "", ()
        consumer, tenant, _ = SQLiteDecisionRepository._ctx_ids(security_context)
        return " AND consumer_id = ? AND tenant_id = ?", (consumer, tenant)

    async def save_decision(self, decision: TriageDecision, security_context: Any = None) -> None:
        self._ensure_tables()
        consumer_id, tenant_id, organization_id = self._ctx_ids(security_context)
        original_ai = json.dumps(decision.original_ai_proposal.model_dump()) if decision.original_ai_proposal else '{}'
        human_override = json.dumps(decision.human_override.model_dump()) if decision.human_override else None
        error_data = json.dumps(decision.error.model_dump()) if decision.error else None
        metadata = dict(decision.metadata or {})
        op_id = getattr(decision, "operation_id", "") or str(metadata.get("operation_id") or "")
        corr_id = str(metadata.get("correlation_id") or "")
        metadata.setdefault("_security", {})
        if isinstance(metadata["_security"], dict):
            sec = metadata["_security"]
            sec.update({"consumer_id": consumer_id, "tenant_id": tenant_id, "organization_id": organization_id})
            if op_id:
                sec["operation_id"] = op_id
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        created_at = decision.created_at or ""
        conn = sqlite3.connect(self._db_path)
        if not created_at:
            row = conn.execute(
                "SELECT created_at FROM decisions WHERE decision_id = ?", (decision.decision_id,)
            ).fetchone()
            created_at = str(row[0]) if row and row[0] else now
        conn.execute(
            """INSERT OR REPLACE INTO decisions
               (decision_id, case_id, domain, action, reason, urgency, confidence,
                evidence_summary, decision_rationale, decision_factors, summary, error,
                lifecycle, processing_time_ms, metadata, original_ai_proposal, human_override,
                consumer_id, tenant_id, organization_id, operation_id, correlation_id, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                decision.decision_id,
                decision.case_id,
                decision.domain,
                decision.action,
                decision.reason,
                decision.urgency,
                decision.confidence,
                decision.evidence_summary,
                decision.decision_rationale,
                json.dumps(decision.decision_factors),
                decision.summary,
                error_data,
                decision.lifecycle.value,
                decision.processing_time_ms,
                json.dumps(metadata),
                original_ai,
                human_override,
                consumer_id,
                tenant_id,
                organization_id,
                op_id,
                corr_id,
                created_at,
                now,
            ),
        )
        conn.commit()
        conn.close()

    def _select_sql(self, where: str = "") -> str:
        cols = ", ".join(_DECISION_COLS)
        base = f"SELECT {cols} FROM decisions"
        return base + (f" {where}" if where else "")

    async def get_decision(self, decision_id: str, security_context: Any = None) -> TriageDecision | None:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            self._select_sql(f"WHERE decision_id = ?{filt}"),
            (decision_id, *params),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_decision(row)

    async def get_decision_by_case(self, case_id: str, security_context: Any = None) -> TriageDecision | None:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            self._select_sql(f"WHERE case_id = ?{filt} ORDER BY created_at DESC LIMIT 1"),
            (case_id, *params),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_decision(row)

    async def get_decision_by_operation(self, operation_id: str, security_context: Any = None) -> TriageDecision | None:
        """Evidence-based correlation helper: find decision by operation_id within authorized context."""
        if not operation_id:
            return None
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            self._select_sql(f"WHERE operation_id = ?{filt} ORDER BY created_at DESC LIMIT 1"),
            (operation_id, *params),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_decision(row)

    async def list_pending_review(self, limit: int = 100, security_context: Any = None) -> list[TriageDecision]:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            self._select_sql(f"WHERE lifecycle = ?{filt} ORDER BY created_at DESC LIMIT ?"),
            (DecisionLifecycle.UNDER_REVIEW.value, *params, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_decision(row) for row in rows]

    async def list_decisions(self, limit: int = 50, offset: int = 0, security_context: Any = None) -> list[TriageDecision]:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        if filt:
            cursor = conn.execute(
                self._select_sql(f"WHERE 1=1{filt} ORDER BY created_at DESC LIMIT ? OFFSET ?"),
                (*params, limit, offset),
            )
        else:
            cursor = conn.execute(
                self._select_sql("ORDER BY created_at DESC LIMIT ? OFFSET ?"),
                (limit, offset),
            )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_decision(row) for row in rows]

    async def count_decisions(self, security_context: Any = None) -> int:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        if filt:
            cursor = conn.execute(f"SELECT COUNT(*) FROM decisions WHERE 1=1{filt}", params)
        else:
            cursor = conn.execute("SELECT COUNT(*) FROM decisions")
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row else 0

    async def update_lifecycle(self, decision_id: str, lifecycle: str, actor: str = "human", justification: str = "", original_action: str = "", original_urgency: str = "", original_confidence: float = 0.0, original_evidence_summary: str = "", security_context: Any = None, expected_lifecycle: str | None = None) -> bool:
        """Update lifecycle with optional CAS on expected_lifecycle. Returns True if updated."""
        self._ensure_tables()
        decision = await self.get_decision(decision_id, security_context=security_context)
        if decision is None:
            return False
        if expected_lifecycle is not None and decision.lifecycle.value != expected_lifecycle:
            return False
        if decision.original_ai_proposal is None:
            decision.original_ai_proposal = AIProposal(
                action=original_action or decision.action,
                reason=decision.reason,
                urgency=original_urgency or decision.urgency,
                confidence=original_confidence or decision.confidence,
                evidence_summary=original_evidence_summary or decision.evidence_summary,
            )
        human_override = HumanOverride(
            actor=actor,
            timestamp=__import__("time").strftime("%Y-%m-%dT%H:%M:%SZ", __import__("time").gmtime()),
            justification=justification,
            original_action=original_action,
            original_urgency=original_urgency,
            original_confidence=original_confidence,
            original_evidence_summary=original_evidence_summary,
        )
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        if expected_lifecycle is not None:
            if filt:
                cur = conn.execute(
                    f"UPDATE decisions SET lifecycle = ?, human_override = ?, updated_at = CURRENT_TIMESTAMP WHERE decision_id = ? AND lifecycle = ?{filt}",
                    (lifecycle, json.dumps(human_override.model_dump()), decision_id, expected_lifecycle, *params),
                )
            else:
                cur = conn.execute(
                    "UPDATE decisions SET lifecycle = ?, human_override = ?, updated_at = CURRENT_TIMESTAMP WHERE decision_id = ? AND lifecycle = ?",
                    (lifecycle, json.dumps(human_override.model_dump()), decision_id, expected_lifecycle),
                )
        else:
            if filt:
                cur = conn.execute(
                    f"UPDATE decisions SET lifecycle = ?, human_override = ?, updated_at = CURRENT_TIMESTAMP WHERE decision_id = ?{filt}",
                    (lifecycle, json.dumps(human_override.model_dump()), decision_id, *params),
                )
            else:
                cur = conn.execute(
                    "UPDATE decisions SET lifecycle = ?, human_override = ?, updated_at = CURRENT_TIMESTAMP WHERE decision_id = ?",
                    (lifecycle, json.dumps(human_override.model_dump()), decision_id),
                )
        conn.commit()
        changed = cur.rowcount > 0
        conn.close()
        return changed

    def _row_to_decision(self, row: tuple[Any, ...]) -> TriageDecision:
        # Explicit column order as per _DECISION_COLS
        d = dict(zip(_DECISION_COLS, row, strict=False))
        original_ai_data = json.loads(d.get("original_ai_proposal") or "{}") if d.get("original_ai_proposal") else None
        original_ai = AIProposal(**original_ai_data) if original_ai_data else None
        human_override_data = json.loads(d.get("human_override") or "null") if d.get("human_override") else None
        human_override = HumanOverride(**human_override_data) if human_override_data else None
        error_data = json.loads(d.get("error") or "null") if d.get("error") else None
        error = CASEError(**error_data) if error_data else None
        try:
            metadata = json.loads(d.get("metadata") or "{}")
        except Exception:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        op_id = d.get("operation_id") or metadata.get("operation_id") or ""
        sec = metadata.get("_security") if isinstance(metadata, dict) else None
        if not isinstance(sec, dict):
            sec = {}
            metadata["_security"] = sec
        sec.setdefault("consumer_id", d.get("consumer_id") or _DEFAULT_CONSUMER)
        sec.setdefault("tenant_id", d.get("tenant_id") or _DEFAULT_TENANT)
        sec.setdefault("organization_id", d.get("organization_id") or "")
        if op_id:
            sec.setdefault("operation_id", op_id)
        try:
            factors = json.loads(d.get("decision_factors") or "[]")
        except Exception:
            factors = []
        return TriageDecision(
            decision_id=d.get("decision_id") or "",
            case_id=d.get("case_id") or "",
            domain=d.get("domain") or "",
            action=d.get("action") or "",
            reason=d.get("reason") or "",
            urgency=d.get("urgency") or "MEDIUM",
            confidence=float(d.get("confidence") or 0.0),
            evidence_summary=d.get("evidence_summary") or "",
            decision_rationale=d.get("decision_rationale") or "",
            decision_factors=factors if isinstance(factors, list) else [],
            summary=d.get("summary") or "",
            error=error,
            lifecycle=DecisionLifecycle(d.get("lifecycle") or DecisionLifecycle.AI_PROPOSED.value),
            processing_time_ms=float(d.get("processing_time_ms") or 0.0),
            metadata=metadata,
            operation_id=str(op_id or ""),
            original_ai_proposal=original_ai,
            human_override=human_override,
            created_at=str(d.get("created_at") or ""),
            updated_at=str(d.get("updated_at") or ""),
        )
