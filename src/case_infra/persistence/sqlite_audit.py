import json
import sqlite3
from pathlib import Path
from typing import Any

from case_core.contracts.audit import AuditEvent
from case_core.ports.audit import AuditPort

_DEFAULT_CONSUMER = "local-autonomous"
_DEFAULT_TENANT = "local"


class SQLiteAuditAdapter(AuditPort):
    def __init__(self, db_path: str = "case_audit.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
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
                correlation_id TEXT DEFAULT '',
                operation_id TEXT DEFAULT '',
                consumer_id TEXT DEFAULT '',
                tenant_id TEXT DEFAULT '',
                organization_id TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._migrate(conn)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_case_id ON audit_events(case_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_consumer_tenant ON audit_events(consumer_id, tenant_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_tenant_case ON audit_events(tenant_id, case_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_operation_id ON audit_events(operation_id)")
        conn.commit()
        conn.close()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        cursor = conn.execute("PRAGMA table_info(audit_events)")
        columns = {row[1] for row in cursor.fetchall()}
        for col, coldef in [
            ("correlation_id", "TEXT DEFAULT ''"),
            ("operation_id", "TEXT DEFAULT ''"),
            ("consumer_id", "TEXT DEFAULT ''"),
            ("tenant_id", "TEXT DEFAULT ''"),
            ("organization_id", "TEXT DEFAULT ''"),
        ]:
            if col not in columns:
                conn.execute(f"ALTER TABLE audit_events ADD COLUMN {col} {coldef}")
        conn.execute(
            "UPDATE audit_events SET consumer_id = ? WHERE consumer_id IS NULL OR consumer_id = ''",
            (_DEFAULT_CONSUMER,),
        )
        conn.execute(
            "UPDATE audit_events SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''",
            (_DEFAULT_TENANT,),
        )

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("SELECT 1 FROM audit_events LIMIT 1")
            self._migrate(conn)
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
        consumer, tenant, _ = SQLiteAuditAdapter._ctx_ids(security_context)
        return " AND consumer_id = ? AND tenant_id = ?", (consumer, tenant)

    async def log_event(self, event: AuditEvent, security_context: Any = None) -> None:
        self._ensure_tables()
        consumer_id, tenant_id, organization_id = self._ctx_ids(security_context)
        details = dict(event.details or {})
        sec = {"consumer_id": consumer_id, "tenant_id": tenant_id, "organization_id": organization_id}
        if event.operation_id:
            sec["operation_id"] = event.operation_id
        details.setdefault("_security", sec)
        actor = event.actor
        if security_context is not None and getattr(security_context, "consumer_id", None):
            actor = actor or str(security_context.consumer_id)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """INSERT INTO audit_events
               (event_id, case_id, decision_id, event_type, timestamp, details, actor, correlation_id, operation_id, consumer_id, tenant_id, organization_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                event.event_id,
                event.case_id,
                event.decision_id,
                event.event_type,
                event.timestamp,
                json.dumps(details),
                actor,
                event.correlation_id or "",
                getattr(event, "operation_id", "") or "",
                consumer_id,
                tenant_id,
                organization_id,
            ),
        )
        conn.commit()
        conn.close()

    async def get_events_by_case(self, case_id: str, security_context: Any = None) -> list[AuditEvent]:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        # Select with operation_id; keep compatible with rows that may not have it in older schemas by querying explicitly
        cursor = conn.execute(
            f"SELECT event_id, case_id, decision_id, event_type, timestamp, details, actor, correlation_id, operation_id FROM audit_events WHERE case_id = ?{filt} ORDER BY created_at",
            (case_id, *params),
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
                correlation_id=row[7] or "",
                operation_id=row[8] or "",
            )
            for row in rows
        ]
