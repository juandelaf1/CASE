import json
import sqlite3
from pathlib import Path

from case_core.contracts.decision import AIProposal, HumanOverride, TriageDecision
from case_core.contracts.lifecycle import DecisionLifecycle
from case_core.ports.decision_repository import DecisionRepositoryPort


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
                lifecycle TEXT NOT NULL DEFAULT 'ai_proposed',
                processing_time_ms REAL DEFAULT 0.0,
                metadata TEXT DEFAULT '{}',
                original_ai_proposal TEXT DEFAULT '{}',
                human_override TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        for col in ["original_ai_proposal", "human_override"]:
            try:
                conn.execute(f"ALTER TABLE decisions ADD COLUMN {col} TEXT")
            except sqlite3.OperationalError:
                pass
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_case_id ON decisions(case_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_lifecycle ON decisions(lifecycle)")
        conn.commit()
        conn.close()

    async def save_decision(self, decision: TriageDecision) -> None:
        original_ai = json.dumps(decision.original_ai_proposal.model_dump()) if decision.original_ai_proposal else '{}'
        human_override = json.dumps(decision.human_override.model_dump()) if decision.human_override else None
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT OR REPLACE INTO decisions
               (decision_id, case_id, domain, action, reason, urgency, confidence,
                evidence_summary, lifecycle, processing_time_ms, metadata, original_ai_proposal, human_override, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
            (
                decision.decision_id,
                decision.case_id,
                decision.domain,
                decision.action,
                decision.reason,
                decision.urgency,
                decision.confidence,
                decision.evidence_summary,
                decision.lifecycle.value,
                decision.processing_time_ms,
                json.dumps(decision.metadata),
                original_ai,
                human_override,
            ),
        )
        conn.commit()
        conn.close()

    async def get_decision(self, decision_id: str) -> TriageDecision | None:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT * FROM decisions WHERE decision_id = ?",
            (decision_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_decision(row)

    async def get_decision_by_case(self, case_id: str) -> TriageDecision | None:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT * FROM decisions WHERE case_id = ? ORDER BY created_at DESC LIMIT 1",
            (case_id,),
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return None
        return self._row_to_decision(row)

    async def list_pending_review(self, limit: int = 100) -> list[TriageDecision]:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT * FROM decisions WHERE lifecycle = ? ORDER BY created_at DESC LIMIT ?",
            (DecisionLifecycle.UNDER_REVIEW.value, limit),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_decision(row) for row in rows]

    async def list_decisions(self, limit: int = 50, offset: int = 0) -> list[TriageDecision]:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT * FROM decisions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_decision(row) for row in rows]

    async def count_decisions(self) -> int:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute("SELECT COUNT(*) FROM decisions")
        row = cursor.fetchone()
        conn.close()
        return int(row[0]) if row else 0

    async def update_lifecycle(self, decision_id: str, lifecycle: str, actor: str = "human", justification: str = "", original_action: str = "", original_urgency: str = "", original_confidence: float = 0.0, original_evidence_summary: str = "") -> None:
        decision = await self.get_decision(decision_id)
        if decision and decision.original_ai_proposal is None:
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
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "UPDATE decisions SET lifecycle = ?, human_override = ?, updated_at = CURRENT_TIMESTAMP WHERE decision_id = ?",
            (lifecycle, json.dumps(human_override.model_dump()), decision_id),
        )
        conn.commit()
        conn.close()

    def _row_to_decision(self, row: tuple[str, ...]) -> TriageDecision:
        original_ai_data = json.loads(row[11]) if row[11] else None
        original_ai = AIProposal(**original_ai_data) if original_ai_data else None
        human_override_data = json.loads(row[12]) if row[12] else None
        human_override = HumanOverride(**human_override_data) if human_override_data else None
        return TriageDecision(
            decision_id=row[0],
            case_id=row[1],
            domain=row[2],
            action=row[3],
            reason=row[4],
            urgency=row[5],
            confidence=float(row[6]),
            evidence_summary=row[7],
            lifecycle=DecisionLifecycle(row[8]),
            processing_time_ms=float(row[9]),
            metadata=json.loads(row[10]) if row[10] else {},
            original_ai_proposal=original_ai,
            human_override=human_override,
        )
