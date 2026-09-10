import json
import sqlite3

from case_core.contracts.audit import AuditEvent
from case_core.ports.audit import AuditPort


class SQLiteAuditAdapter(AuditPort):
    def __init__(self, db_path: str = "case_audit.db") -> None:
        self._db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                decision_id TEXT,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                details TEXT NOT NULL,
                actor TEXT DEFAULT 'system',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_case_id ON audit_events(case_id)")
        conn.commit()
        conn.close()

    async def log_event(self, event: AuditEvent) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT OR REPLACE INTO audit_events
               (event_id, case_id, decision_id, event_type, timestamp, details, actor)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.case_id,
                event.decision_id,
                event.event_type,
                event.timestamp,
                json.dumps(event.details),
                event.actor,
            ),
        )
        conn.commit()
        conn.close()

    async def get_events_by_case(self, case_id: str) -> list[AuditEvent]:
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            "SELECT event_id, case_id, decision_id, event_type, timestamp, details, actor FROM audit_events WHERE case_id = ? ORDER BY created_at",
            (case_id,),
        )
        rows = cursor.fetchall()
        conn.close()
        return [
            AuditEvent(
                event_id=row[0],
                case_id=row[1],
                decision_id=row[2],
                event_type=row[3],
                timestamp=row[4],
                details=json.loads(row[5]),
                actor=row[6],
            )
            for row in rows
        ]
