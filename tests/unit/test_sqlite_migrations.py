import shutil
import sqlite3
import tempfile
from pathlib import Path

from case_infra.persistence.sqlite_migrations import (
    DEFAULT_CONSUMER,
    DEFAULT_TENANT,
    downgrade_on_copy,
    get_user_version,
    upgrade,
)


def _make_legacy_v1_db(db_path: str) -> None:
    """Create a legacy schema without context columns/idempotency/version."""
    conn = sqlite3.connect(db_path)
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
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    conn.execute(
        "INSERT INTO decisions (decision_id,case_id,domain,action,reason,urgency,confidence,evidence_summary,lifecycle,metadata) "
        "VALUES ('d1','c1','logistics','act','reason','low',0.5,'ev','ai_proposed','{\"x\":1}')"
    )
    conn.execute(
        "INSERT INTO audit_events (event_id,case_id,event_type,timestamp,details) VALUES ('e1','c1','E','t','{\"y\":2}')"
    )
    conn.commit()
    conn.close()


def _cols(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    finally:
        conn.close()


def test_upgrade_v1_to_v2_on_copy_preserves_data_and_backfills_context():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        legacy = str(Path(d) / "legacy.db")
        copy = str(Path(d) / "copy.db")
        _make_legacy_v1_db(legacy)
        shutil.copy2(legacy, copy)

        v = upgrade(copy, target_version=2)
        assert v == 2
        assert get_user_version(copy) == 2
        assert {"consumer_id", "tenant_id", "organization_id"}.issubset(_cols(copy, "decisions"))
        assert {"consumer_id", "tenant_id", "organization_id"}.issubset(_cols(copy, "audit_events"))
        assert "idempotency_keys" in {r[0] for r in sqlite3.connect(copy).execute("SELECT name FROM sqlite_master WHERE type='table'")}

        conn = sqlite3.connect(copy)
        drow = conn.execute("SELECT consumer_id,tenant_id,metadata FROM decisions WHERE decision_id='d1'").fetchone()
        arow = conn.execute("SELECT consumer_id,tenant_id,details FROM audit_events WHERE event_id='e1'").fetchone()
        conn.close()
        assert drow[0] == DEFAULT_CONSUMER and drow[1] == DEFAULT_TENANT
        assert arow[0] == DEFAULT_CONSUMER and arow[1] == DEFAULT_TENANT


def test_downgrade_on_copy_rebuilds_to_v1_and_preserves_core_data():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        legacy = str(Path(d) / "legacy.db")
        copy = str(Path(d) / "copy.db")
        _make_legacy_v1_db(legacy)
        shutil.copy2(legacy, copy)

        upgrade(copy, target_version=2)
        # simulate v2-only artifacts
        conn = sqlite3.connect(copy)
        conn.execute(
            "INSERT OR REPLACE INTO idempotency_keys (consumer_id,tenant_id,operation,idempotency_key,request_hash,status) VALUES (?,?,?,?,?,?)",
            ("c", "t", "op", "k", "h", "completed"),
        )
        conn.commit()
        conn.close()

        v = downgrade_on_copy(copy, target_version=1)
        assert v == 1
        assert get_user_version(copy) == 1
        dcols = _cols(copy, "decisions")
        acols = _cols(copy, "audit_events")
        assert "consumer_id" not in dcols and "tenant_id" not in dcols
        assert "consumer_id" not in acols and "tenant_id" not in acols
        tables = {r[0] for r in sqlite3.connect(copy).execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "idempotency_keys" not in tables

        conn = sqlite3.connect(copy)
        assert conn.execute("SELECT decision_id,case_id,metadata FROM decisions WHERE decision_id='d1'").fetchone()[0] == "d1"
        assert conn.execute("SELECT event_id,case_id,details FROM audit_events WHERE event_id='e1'").fetchone()[0] == "e1"
        conn.close()


def test_upgrade_is_idempotent_on_multiple_copies_states():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        # state A: legacy v1
        a = str(Path(d) / "a.db")
        _make_legacy_v1_db(a)
        assert upgrade(a, 2) == 2
        assert upgrade(a, 2) == 2

        # state B: already v2/current-like created fresh then upgraded
        b = str(Path(d) / "b.db")
        _make_legacy_v1_db(b)
        upgrade(b, 2)
        # second pass after data exists
        conn = sqlite3.connect(b)
        conn.execute(
            "INSERT INTO decisions (decision_id,case_id,domain,action,reason,urgency,confidence,evidence_summary,lifecycle,consumer_id,tenant_id) "
            "VALUES ('d2','c2','log','a','r','low',0.5,'e','ai_proposed','','')"
        )
        conn.commit()
        conn.close()
        assert upgrade(b, 2) == 2
        conn = sqlite3.connect(b)
        row = conn.execute("SELECT consumer_id,tenant_id FROM decisions WHERE decision_id='d2'").fetchone()
        conn.close()
        assert row == (DEFAULT_CONSUMER, DEFAULT_TENANT)
def _table_names(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    finally:
        conn.close()


def _indexes(db_path: str, table: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {r[1] for r in conn.execute(f"PRAGMA index_list({table})").fetchall()}
    finally:
        conn.close()


def test_upgrade_v1_to_v5_chain_on_copy_preserves_data_and_required_schema():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        legacy = str(Path(d) / "legacy.db")
        db = str(Path(d) / "chain.db")
        _make_legacy_v1_db(legacy)
        shutil.copy2(legacy, db)

        assert upgrade(db, target_version=5) == 5
        assert get_user_version(db) == 5
        # repeated migration idempotent
        assert upgrade(db, target_version=5) == 5

        dcols = _cols(db, "decisions")
        acols = _cols(db, "audit_events")
        icols = _cols(db, "idempotency_keys")
        assert {"consumer_id", "tenant_id", "organization_id", "operation_id", "correlation_id"}.issubset(dcols)
        assert {"consumer_id", "tenant_id", "organization_id", "correlation_id", "operation_id"}.issubset(acols)
        assert {"operation_id", "correlation_id", "case_id", "decision_id", "result_ref_json", "request_context_json"}.issubset(icols)
        assert "idempotency_keys" in _table_names(db)
        assert "idx_decisions_operation_id" in _indexes(db, "decisions")
        assert "idx_audit_operation_id" in _indexes(db, "audit_events")
        assert "idx_idem_operation_id" in _indexes(db, "idempotency_keys")

        conn = sqlite3.connect(db)
        drow = conn.execute("SELECT decision_id, case_id, consumer_id, tenant_id, metadata FROM decisions WHERE decision_id='d1'").fetchone()
        arow = conn.execute("SELECT event_id, case_id, consumer_id, tenant_id, details FROM audit_events WHERE event_id='e1'").fetchone()
        conn.close()
        assert drow is not None and drow[0] == "d1" and drow[1] == "c1"
        assert drow[2] == DEFAULT_CONSUMER and drow[3] == DEFAULT_TENANT
        assert arow is not None and arow[0] == "e1" and arow[1] == "c1"
        assert arow[2] == DEFAULT_CONSUMER and arow[3] == DEFAULT_TENANT


def test_upgrade_from_v2_v3_v4_with_data_preserves_records():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        legacy = str(Path(d) / "legacy.db")
        _make_legacy_v1_db(legacy)
        for ver in (2, 3, 4):
            db = str(Path(d) / f"v{ver}.db")
            shutil.copy2(legacy, db)
            assert upgrade(db, target_version=ver) == ver
            # insert representative data at that version state
            conn = sqlite3.connect(db)
            conn.execute(
                "INSERT OR REPLACE INTO decisions (decision_id,case_id,domain,action,reason,urgency,confidence,evidence_summary,lifecycle,consumer_id,tenant_id,metadata) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (f"d{ver}", f"c{ver}", "logistics", "approve", "reason", "LOW", 0.5, "ev", "ai_proposed", DEFAULT_CONSUMER, DEFAULT_TENANT, "{}"),
            )
            conn.execute(
                "INSERT OR REPLACE INTO audit_events (event_id,case_id,event_type,timestamp,details,consumer_id,tenant_id) VALUES (?,?,?,?,?,?,?)",
                (f"e{ver}", f"c{ver}", "E", "t", "{}", DEFAULT_CONSUMER, DEFAULT_TENANT),
            )
            conn.commit()
            conn.close()
            assert upgrade(db, target_version=5) == 5
            conn = sqlite3.connect(db)
            assert conn.execute("SELECT COUNT(*) FROM decisions WHERE decision_id IN ('d1',?)", (f"d{ver}",)).fetchone()[0] == 2
            assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE event_id IN ('e1',?)", (f"e{ver}",)).fetchone()[0] == 2
            conn.close()


def test_new_db_upgrade_and_repository_initialization_after_migrate():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        db = str(Path(d) / "new.db")
        # new empty DB upgraded to latest
        assert upgrade(db, target_version=5) == 5
        assert get_user_version(db) == 5
        # repositories should initialize and operate correctly
        import asyncio

        from case_core.contracts.audit import AuditEvent
        from case_core.contracts.decision import TriageDecision
        from case_core.contracts.lifecycle import DecisionLifecycle
        from case_core.contracts.security import SecurityContext
        from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
        from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository
        from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

        dec_repo = SQLiteDecisionRepository(db)
        aud = SQLiteAuditAdapter(db)
        idem = SQLiteIdempotencyStore(db)
        ctx = SecurityContext(consumer_id="c1", tenant_id="t1", mode="shared")

        async def _run():
            decision = TriageDecision(
                decision_id="dec-new", case_id="case-new", domain="logistics", action="approve",
                reason="reason text long enough", urgency="LOW", confidence=0.7, evidence_summary="evidence",
                lifecycle=DecisionLifecycle.AI_PROPOSED, metadata={}, operation_id="op-new",
            )
            await dec_repo.save_decision(decision, security_context=ctx)
            got = await dec_repo.get_decision("dec-new", security_context=ctx)
            assert got is not None and got.operation_id == "op-new"
            await aud.log_event(AuditEvent(
                event_id="ae-new", case_id="case-new", event_type="E", timestamp="t", details={}, operation_id="op-new"
            ), security_context=ctx)
            ev = await aud.get_events_by_case("case-new", security_context=ctx)
            assert len(ev) == 1 and ev[0].operation_id == "op-new"
            idem.begin(ctx, "case.evaluate", "k", "h", operation_id="op-new", correlation_id="c", request_context={"a": 1})
            rec = idem.get_by_key("c1", "t1", "case.evaluate", "k")
            assert rec is not None and rec.get("operation_id") == "op-new" and rec.get("request_context", {}).get("a") == 1

        asyncio.run(_run())
