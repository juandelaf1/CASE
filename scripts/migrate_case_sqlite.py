# ruff: noqa: T201
"""Explicit SQLite migration helper for CASE context-isolation columns.

Usage:
  python scripts/migrate_case_sqlite.py --db path/to/case_audit.db
  python scripts/migrate_case_sqlite.py --db path/to/case.db --kind repository

- Non-destructive: adds columns/indexes if missing and backfills legacy rows to local-autonomous context.
- Reproducible/idempotent: safe to run multiple times.
- Reversible (best-effort): not automatically reversible for added columns in SQLite; restore from backup/copy.
- Do NOT run on production/real databases without backup and authorization.
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

DEFAULT_CONSUMER = "local-autonomous"
DEFAULT_TENANT = "local"


def migrate_decision_audit_db(db_path: str) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    changes = {"decisions_updated": 0, "audit_events_updated": 0}
    for table, cols in {
        "decisions": [("consumer_id", "TEXT DEFAULT ''"), ("tenant_id", "TEXT DEFAULT ''"), ("organization_id", "TEXT DEFAULT ''")],
        "audit_events": [("consumer_id", "TEXT DEFAULT ''"), ("tenant_id", "TEXT DEFAULT ''"), ("organization_id", "TEXT DEFAULT ''"), ("correlation_id", "TEXT DEFAULT ''")],
        "idempotency_keys": [],
    }.items():
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            continue
        existing = {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}
        for col, coldef in cols:
            if col not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
        if table == "decisions":
            cur.execute("UPDATE decisions SET consumer_id=? WHERE consumer_id IS NULL OR consumer_id=''", (DEFAULT_CONSUMER,))
            cur.execute("UPDATE decisions SET tenant_id=? WHERE tenant_id IS NULL OR tenant_id=''", (DEFAULT_TENANT,))
            changes["decisions_updated"] = cur.rowcount if cur.rowcount is not None else 0
            cur.execute("CREATE INDEX IF NOT EXISTS idx_decisions_consumer_tenant ON decisions(consumer_id, tenant_id)")
        if table == "audit_events":
            cur.execute("UPDATE audit_events SET consumer_id=? WHERE consumer_id IS NULL OR consumer_id=''", (DEFAULT_CONSUMER,))
            cur.execute("UPDATE audit_events SET tenant_id=? WHERE tenant_id IS NULL OR tenant_id=''", (DEFAULT_TENANT,))
            changes["audit_events_updated"] = cur.rowcount if cur.rowcount is not None else 0
            cur.execute("CREATE INDEX IF NOT EXISTS idx_audit_consumer_tenant ON audit_events(consumer_id, tenant_id)")
    conn.commit()
    conn.close()
    return changes


def migrate_repository_db(db_path: str) -> dict[str, int]:
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    changes = {"cases_updated": 0, "audit_events_updated": 0}
    for table in ("cases", "audit_events"):
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        if not cur.fetchone():
            continue
        existing = {r[1] for r in cur.execute(f"PRAGMA table_info({table})")}
        for col, coldef in [("consumer_id", "TEXT DEFAULT ''"), ("tenant_id", "TEXT DEFAULT ''"), ("organization_id", "TEXT DEFAULT ''")]:
            if col not in existing:
                cur.execute(f"ALTER TABLE {table} ADD COLUMN {col} {coldef}")
        cur.execute(f"UPDATE {table} SET consumer_id=? WHERE consumer_id IS NULL OR consumer_id=''", (DEFAULT_CONSUMER,))
        cur.execute(f"UPDATE {table} SET tenant_id=? WHERE tenant_id IS NULL OR tenant_id=''", (DEFAULT_TENANT,))
        changes[f"{table}_updated"] = 0
    cur.execute("CREATE INDEX IF NOT EXISTS idx_cases_consumer_tenant ON cases(consumer_id, tenant_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_repo_audit_consumer_tenant ON audit_events(consumer_id, tenant_id)")
    conn.commit()
    conn.close()
    return changes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--kind", choices=["decision_audit", "repository"], default="decision_audit")
    args = ap.parse_args()
    path = Path(args.db)
    if not path.exists():
        raise SystemExit(f"DB not found: {path}")
    if args.kind == "repository":
        print(migrate_repository_db(str(path)))
    else:
        print(migrate_decision_audit_db(str(path)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
