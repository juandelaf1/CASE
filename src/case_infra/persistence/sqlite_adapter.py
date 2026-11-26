import json
import sqlite3
from pathlib import Path
from typing import Any

from case_core.contracts.audit import AuditEvent
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.repository import RepositoryPort

_DEFAULT_CONSUMER = "local-autonomous"
_DEFAULT_TENANT = "local"


class SQLiteRepository(RepositoryPort):
    """SQLite adapter for case persistence (with context-aware isolation)."""

    def __init__(self, db_path: str = "case.db") -> None:
        self._db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        conn = sqlite3.connect(self._db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS cases (
                case_id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                consumer_id TEXT DEFAULT '',
                tenant_id TEXT DEFAULT '',
                organization_id TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_events (
                event_id TEXT PRIMARY KEY,
                case_id TEXT NOT NULL,
                data TEXT NOT NULL,
                consumer_id TEXT DEFAULT '',
                tenant_id TEXT DEFAULT '',
                organization_id TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self._migrate(conn)
        conn.commit()
        conn.close()

    def _migrate(self, conn: sqlite3.Connection) -> None:
        for table in ("cases", "audit_events"):
            cols = {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}
            for col, coldef in [("consumer_id", "TEXT DEFAULT ''"), ("tenant_id", "TEXT DEFAULT ''"), ("organization_id", "TEXT DEFAULT ''")]:
                if col not in cols:
                    conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
            conn.execute(
                f"UPDATE {table} SET consumer_id = ? WHERE consumer_id IS NULL OR consumer_id = ''",
                (_DEFAULT_CONSUMER,),
            )
            conn.execute(
                f"UPDATE {table} SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''",
                (_DEFAULT_TENANT,),
            )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_consumer_tenant ON cases(consumer_id, tenant_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_auditevents_consumer_tenant ON audit_events(consumer_id, tenant_id)")

    def _ensure_tables(self) -> None:
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("SELECT 1 FROM cases LIMIT 1")
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
        consumer, tenant, _ = SQLiteRepository._ctx_ids(security_context)
        return " AND consumer_id = ? AND tenant_id = ?", (consumer, tenant)

    async def save_case(self, case: OperationalCase, security_context: Any = None) -> None:
        self._ensure_tables()
        consumer_id, tenant_id, organization_id = self._ctx_ids(security_context)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT OR REPLACE INTO cases (case_id, data, consumer_id, tenant_id, organization_id) VALUES (?, ?, ?, ?, ?)",
            (case.case_id, json.dumps(case.model_dump()), consumer_id, tenant_id, organization_id),
        )
        conn.commit()
        conn.close()

    async def get_case(self, case_id: str, security_context: Any = None) -> OperationalCase | None:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(f"SELECT data FROM cases WHERE case_id = ?{filt}", (case_id, *params))
        row = cursor.fetchone()
        conn.close()
        if row:
            return OperationalCase.model_validate(json.loads(row[0]))
        return None

    async def list_cases(self, limit: int = 100, offset: int = 0, security_context: Any = None) -> list[OperationalCase]:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        if filt:
            cursor = conn.execute(
                f"SELECT data FROM cases WHERE 1=1{filt} ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (*params, limit, offset),
            )
        else:
            cursor = conn.execute(
                "SELECT data FROM cases ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset),
            )
        rows = cursor.fetchall()
        conn.close()
        return [OperationalCase.model_validate(json.loads(row[0])) for row in rows]

    async def save_audit_event(self, event: AuditEvent, security_context: Any = None) -> None:
        self._ensure_tables()
        consumer_id, tenant_id, organization_id = self._ctx_ids(security_context)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            "INSERT INTO audit_events (event_id, case_id, data, consumer_id, tenant_id, organization_id) VALUES (?, ?, ?, ?, ?, ?)",
            (event.event_id, event.case_id, json.dumps(event.model_dump()), consumer_id, tenant_id, organization_id),
        )
        conn.commit()
        conn.close()

    async def get_audit_events(self, case_id: str, security_context: Any = None) -> list[AuditEvent]:
        self._ensure_tables()
        filt, params = self._context_filter(security_context)
        conn = sqlite3.connect(self._db_path)
        cursor = conn.execute(
            f"SELECT data FROM audit_events WHERE case_id = ?{filt} ORDER BY created_at",
            (case_id, *params),
        )
        rows = cursor.fetchall()
        conn.close()
        return [AuditEvent.model_validate(json.loads(row[0])) for row in rows]
