import json
import sqlite3

from case_core.contracts.audit import AuditEvent
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.repository import RepositoryPort


class SQLiteRepository(RepositoryPort):
    """SQLite adapter for case persistence."""

    def __init__(self, db_path: str = "case.db") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                data TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (case_id) REFERENCES cases(case_id)
            )
        """)
        conn.commit()
        conn.close()

    async def save_case(self, case: OperationalCase) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO cases (case_id, data) VALUES (?, ?)",
            (case.case_id, json.dumps(case.model_dump())),
        )
        conn.commit()
        conn.close()

    async def get_case(self, case_id: str) -> OperationalCase | None:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute("SELECT data FROM cases WHERE case_id = ?", (case_id,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return OperationalCase.model_validate(json.loads(row[0]))
        return None

    async def list_cases(self, limit: int = 100, offset: int = 0) -> list[OperationalCase]:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT data FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset),
        )
        rows = cursor.fetchall()
        conn.close()
        return [OperationalCase.model_validate(json.loads(row[0])) for row in rows]

    async def save_audit_event(self, event: AuditEvent) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO audit_events (event_id, case_id, data) VALUES (?, ?, ?)",
            (event.event_id, event.case_id, json.dumps(event.model_dump())),
        )
        conn.commit()
        conn.close()

    async def get_audit_events(self, case_id: str) -> list[AuditEvent]:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT data FROM audit_events WHERE case_id = ? ORDER BY created_at",
            (case_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [AuditEvent.model_validate(json.loads(row[0])) for row in rows]
