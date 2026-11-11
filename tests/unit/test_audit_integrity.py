"""Tests for audit event integrity (append-only semantics)."""
from __future__ import annotations

import os
import tempfile

import pytest

from case_core.contracts.audit import AuditEvent
from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter


@pytest.fixture
def tmp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_event(event_id: str, case_id: str = "c-1", event_type: str = "test") -> AuditEvent:
    return AuditEvent(
        event_id=event_id,
        case_id=case_id,
        event_type=event_type,
        timestamp="2026-09-23T00:00:00Z",
        details={"test": True},
        actor="test",
    )


class TestAuditIntegrity:
    async def test_two_different_events_stored(self, tmp_db: str) -> None:
        adapter = SQLiteAuditAdapter(db_path=tmp_db)
        e1 = _make_event("e1", event_type="type_a")
        e2 = _make_event("e2", event_type="type_b")
        await adapter.log_event(e1)
        await adapter.log_event(e2)
        events = await adapter.get_events_by_case("c-1")
        assert len(events) == 2
        assert {e.event_id for e in events} == {"e1", "e2"}

    async def test_repeated_event_types_preserved(self, tmp_db: str) -> None:
        adapter = SQLiteAuditAdapter(db_path=tmp_db)
        await adapter.log_event(_make_event("e1", event_type="lifecycle"))
        await adapter.log_event(_make_event("e2", event_type="lifecycle"))
        await adapter.log_event(_make_event("e3", event_type="lifecycle"))
        events = await adapter.get_events_by_case("c-1")
        assert len(events) == 3

    async def test_ordering_is_stable(self, tmp_db: str) -> None:
        adapter = SQLiteAuditAdapter(db_path=tmp_db)
        for i in range(5):
            await adapter.log_event(_make_event(f"e{i}"))
        events = await adapter.get_events_by_case("c-1")
        assert len(events) == 5
        assert [e.event_id for e in events] == ["e0", "e1", "e2", "e3", "e4"]

    async def test_case_filtering(self, tmp_db: str) -> None:
        adapter = SQLiteAuditAdapter(db_path=tmp_db)
        await adapter.log_event(_make_event("e1", case_id="c-1"))
        await adapter.log_event(_make_event("e2", case_id="c-2"))
        await adapter.log_event(_make_event("e3", case_id="c-1"))
        events_c1 = await adapter.get_events_by_case("c-1")
        events_c2 = await adapter.get_events_by_case("c-2")
        assert len(events_c1) == 2
        assert len(events_c2) == 1

    async def test_no_event_disappears(self, tmp_db: str) -> None:
        adapter = SQLiteAuditAdapter(db_path=tmp_db)
        for i in range(10):
            await adapter.log_event(_make_event(f"e{i}"))
        events = await adapter.get_events_by_case("c-1")
        assert len(events) == 10
        ids = {e.event_id for e in events}
        assert ids == {f"e{i}" for i in range(10)}

    async def test_empty_case_returns_empty(self, tmp_db: str) -> None:
        adapter = SQLiteAuditAdapter(db_path=tmp_db)
        events = await adapter.get_events_by_case("nonexistent")
        assert events == []
