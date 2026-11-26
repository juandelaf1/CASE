"""Formal, versioned SQLite migrations for CASE persistence (decision/audit/idempotency DB).

Scope: additive, testable on DB copies. Designed for `case_audit.db`-style databases
containing `decisions`, `audit_events`, and optionally `idempotency_keys`.

- Upgrade is in-place and non-destructive (add columns/indexes/tables, backfill defaults).
- Downgrade is supported as **best-effort on a DB copy** by table rebuild to remove
  context-isolation/idempotency structures. Do NOT run downgrade on real/production DBs
  without backup and explicit authorization.
- Runtime repositories also perform defensive auto-migration; this module provides
  explicit, versioned, reproducible steps for validation and operations.

Version history:
- 1: legacy schema (no consumer/tenant/organization context columns, no idempotency table)
- 2: context-isolation columns/indexes + idempotency_keys table + schema_version tracking
- 3: idempotency operation correlation (operation_id/correlation_id/case_id/decision_id/result_ref_json)
- 4: decision/audit operation correlation (operation_id columns and indexes)
- 5: idempotency request context snapshot for evidence-based response reconstruction
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

DEFAULT_CONSUMER = "local-autonomous"
DEFAULT_TENANT = "local"
LATEST_VERSION = 5


def _connect(db_path: str) -> sqlite3.Connection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=OFF")
    return conn


def get_user_version(db_path: str) -> int:
    conn = _connect(db_path)
    try:
        (v,) = conn.execute("PRAGMA user_version").fetchone()
        return int(v or 0)
    finally:
        conn.close()


def set_user_version(conn: sqlite3.Connection, version: int) -> None:
    conn.execute(f"PRAGMA user_version = {int(version)}")


def _table_exists(conn: sqlite3.Connection, name: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return row is not None


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    if not _table_exists(conn, table):
        return set()
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _ensure_context_columns_decisions(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "decisions"):
        return
    cols = _columns(conn, "decisions")
    for col, coldef in [
        ("consumer_id", "TEXT DEFAULT ''"),
        ("tenant_id", "TEXT DEFAULT ''"),
        ("organization_id", "TEXT DEFAULT ''"),
        ("operation_id", "TEXT DEFAULT ''"),
        ("correlation_id", "TEXT DEFAULT ''"),
    ]:
        if col not in cols:
            conn.execute(f"ALTER TABLE decisions ADD COLUMN {col} {coldef}")
    conn.execute(
        "UPDATE decisions SET consumer_id = ? WHERE consumer_id IS NULL OR consumer_id = ''",
        (DEFAULT_CONSUMER,),
    )
    conn.execute(
        "UPDATE decisions SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''",
        (DEFAULT_TENANT,),
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_decisions_consumer_tenant ON decisions(consumer_id, tenant_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_decisions_tenant_case ON decisions(tenant_id, case_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_decisions_operation_id ON decisions(operation_id)"
    )


def _ensure_context_columns_audit(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "audit_events"):
        return
    cols = _columns(conn, "audit_events")
    for col, coldef in [
        ("consumer_id", "TEXT DEFAULT ''"),
        ("tenant_id", "TEXT DEFAULT ''"),
        ("organization_id", "TEXT DEFAULT ''"),
        ("correlation_id", "TEXT DEFAULT ''"),
        ("operation_id", "TEXT DEFAULT ''"),
    ]:
        if col not in cols:
            conn.execute(f"ALTER TABLE audit_events ADD COLUMN {col} {coldef}")
    conn.execute(
        "UPDATE audit_events SET consumer_id = ? WHERE consumer_id IS NULL OR consumer_id = ''",
        (DEFAULT_CONSUMER,),
    )
    conn.execute(
        "UPDATE audit_events SET tenant_id = ? WHERE tenant_id IS NULL OR tenant_id = ''",
        (DEFAULT_TENANT,),
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_consumer_tenant ON audit_events(consumer_id, tenant_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant_case ON audit_events(tenant_id, case_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_operation_id ON audit_events(operation_id)"
    )


def _ensure_idempotency_table(conn: sqlite3.Connection) -> None:
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
    cols = _columns(conn, "idempotency_keys")
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
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_idem_consumer_tenant ON idempotency_keys(consumer_id, tenant_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_idem_status_updated ON idempotency_keys(status, updated_at)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_idem_operation_id ON idempotency_keys(operation_id)"
    )


def upgrade_to_v3(conn: sqlite3.Connection) -> None:
    # v3 is additive on idempotency correlation columns; ensure v2 base first.
    upgrade_to_v2(conn)
    _ensure_idempotency_table(conn)
    set_user_version(conn, 3)


def upgrade_to_v4(conn: sqlite3.Connection) -> None:
    # v4 adds operation correlation columns to decisions and audit_events.
    upgrade_to_v3(conn)
    _ensure_context_columns_decisions(conn)
    _ensure_context_columns_audit(conn)
    _ensure_idempotency_table(conn)
    set_user_version(conn, 4)


def upgrade_to_v5(conn: sqlite3.Connection) -> None:
    # v5 adds request context snapshot to idempotency for deterministic recovery reconstruction.
    upgrade_to_v4(conn)
    _ensure_idempotency_table(conn)
    set_user_version(conn, 5)


def upgrade_to_v2(conn: sqlite3.Connection) -> None:
    _ensure_context_columns_decisions(conn)
    _ensure_context_columns_audit(conn)
    _ensure_idempotency_table(conn)
    set_user_version(conn, 2)


def upgrade(db_path: str, target_version: int = LATEST_VERSION) -> int:
    """Upgrade DB in-place to target_version. Returns resulting version.

    Idempotent: re-applying ensures columns/indexes/tables/backfill on copies/states.
    """
    if target_version not in (1, 2, 3, 4, 5):
        raise ValueError(f"Unsupported target_version: {target_version}")
    conn = _connect(db_path)
    try:
        current = int(conn.execute("PRAGMA user_version").fetchone()[0] or 0)
        if target_version < current:
            raise ValueError(
                "In-place downgrade is not supported; use downgrade_on_copy for test copies."
            )
        if target_version >= 5:
            upgrade_to_v5(conn)
            conn.commit()
            current = 5
        elif target_version >= 4:
            upgrade_to_v4(conn)
            conn.commit()
            current = 4
        elif target_version >= 3:
            upgrade_to_v3(conn)
            conn.commit()
            current = 3
        elif target_version >= 2:
            upgrade_to_v2(conn)
            conn.commit()
            current = 2
        elif current == 0 and target_version == 1:
            if not _table_exists(conn, "idempotency_keys"):
                set_user_version(conn, 1)
                conn.commit()
                current = 1
            else:
                set_user_version(conn, 2)
                conn.commit()
                current = 2
        return current
    finally:
        conn.close()


def _rebuild_decisions_v1(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "decisions"):
        return
    cols = _columns(conn, "decisions")
    # Keep core columns present in legacy/v1; drop context columns.
    keep = [
        c
        for c in [
            "decision_id",
            "case_id",
            "domain",
            "action",
            "reason",
            "urgency",
            "confidence",
            "evidence_summary",
            "decision_rationale",
            "decision_factors",
            "summary",
            "error",
            "lifecycle",
            "processing_time_ms",
            "metadata",
            "original_ai_proposal",
            "human_override",
            "created_at",
            "updated_at",
        ]
        if c in cols
    ]
    if not keep:
        return
    conn.execute("ALTER TABLE decisions RENAME TO decisions_v2")
    conn.execute(
        """
        CREATE TABLE decisions (
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    # copy intersection
    dst_cols = _columns(conn, "decisions")
    common = [c for c in keep if c in dst_cols]
    common_sql = ", ".join(common)
    conn.execute(f"INSERT INTO decisions ({common_sql}) SELECT {common_sql} FROM decisions_v2")
    conn.execute("DROP TABLE decisions_v2")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_case_id ON decisions(case_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_decisions_lifecycle ON decisions(lifecycle)")


def _rebuild_audit_v1(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "audit_events"):
        return
    cols = _columns(conn, "audit_events")
    keep = [
        c
        for c in [
            "event_id",
            "case_id",
            "decision_id",
            "event_type",
            "timestamp",
            "details",
            "actor",
            "correlation_id",
            "created_at",
        ]
        if c in cols
    ]
    if not keep:
        return
    conn.execute("ALTER TABLE audit_events RENAME TO audit_events_v2")
    conn.execute(
        """
        CREATE TABLE audit_events (
            event_id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL,
            decision_id TEXT,
            event_type TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            details TEXT NOT NULL,
            actor TEXT DEFAULT 'system',
            correlation_id TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    dst_cols = _columns(conn, "audit_events")
    common = [c for c in keep if c in dst_cols]
    common_sql = ", ".join(common)
    conn.execute(
        f"INSERT INTO audit_events ({common_sql}) SELECT {common_sql} FROM audit_events_v2"
    )
    conn.execute("DROP TABLE audit_events_v2")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_case_id ON audit_events(case_id)")


def downgrade_on_copy(db_path: str, target_version: int = 1) -> int:
    """Best-effort downgrade for DB copies. Rebuilds tables to remove v2 structures."""
    if target_version != 1:
        raise ValueError("Only downgrade to v1 is supported")
    conn = _connect(db_path)
    try:
        _rebuild_decisions_v1(conn)
        _rebuild_audit_v1(conn)
        if _table_exists(conn, "idempotency_keys"):
            conn.execute("DROP TABLE idempotency_keys")
        set_user_version(conn, 1)
        conn.commit()
        return 1
    finally:
        conn.close()
