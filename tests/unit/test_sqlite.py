import asyncio
import os
import sys

import pytest

sys.path.insert(0, "src")

from case_core.contracts.audit import AuditEvent
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_infra.persistence.sqlite_adapter import SQLiteRepository
from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter


TEST_DB = "test_case.db"
TEST_AUDIT_DB = "test_audit.db"


@pytest.fixture(autouse=True)
def cleanup():
    yield
    for db in [TEST_DB, TEST_AUDIT_DB]:
        if os.path.exists(db):
            os.remove(db)


def _make_case(case_id: str = "case-001") -> OperationalCase:
    return OperationalCase(
        case_id=case_id,
        report_text="Test report",
        domain="urban_operations",
        urgency=UrgencyLevel.MEDIUM,
        evidence=[
            EvidenceItem(
                id="ev-001",
                type=EvidenceType.TEXT,
                content="Test evidence",
                source="test",
                confidence=0.9,
                extracted_at="2026-09-08T12:00:00Z",
            )
        ],
    )


def _make_audit_event(case_id: str = "case-001", event_type: str = "case_received") -> AuditEvent:
    return AuditEvent(
        event_id=f"ae-{case_id}-{event_type}",
        case_id=case_id,
        event_type=event_type,
        timestamp="2026-09-08T12:00:00Z",
        details={"source": "test"},
    )


class TestSQLiteRepository:
    def test_save_and_get_case(self):
        repo = SQLiteRepository(TEST_DB)
        case = _make_case()
        asyncio.run(repo.save_case(case))
        retrieved = asyncio.run(repo.get_case("case-001"))
        assert retrieved is not None
        assert retrieved.case_id == "case-001"
        assert retrieved.report_text == "Test report"

    def test_get_nonexistent_returns_none(self):
        repo = SQLiteRepository(TEST_DB)
        retrieved = asyncio.run(repo.get_case("nonexistent"))
        assert retrieved is None

    def test_list_cases(self):
        repo = SQLiteRepository(TEST_DB)
        asyncio.run(repo.save_case(_make_case("c1")))
        asyncio.run(repo.save_case(_make_case("c2")))
        cases = asyncio.run(repo.list_cases())
        assert len(cases) == 2

    def test_list_cases_with_limit(self):
        repo = SQLiteRepository(TEST_DB)
        for i in range(5):
            asyncio.run(repo.save_case(_make_case(f"c{i}")))
        cases = asyncio.run(repo.list_cases(limit=2))
        assert len(cases) == 2


class TestSQLiteAuditAdapter:
    def test_log_and_retrieve_event(self):
        adapter = SQLiteAuditAdapter(TEST_AUDIT_DB)
        event = _make_audit_event()
        asyncio.run(adapter.log_event(event))
        events = asyncio.run(adapter.get_events_by_case("case-001"))
        assert len(events) == 1
        assert events[0].event_id == "ae-case-001-case_received"
        assert events[0].case_id == "case-001"
        assert events[0].event_type == "case_received"

    def test_multiple_events_for_same_case(self):
        adapter = SQLiteAuditAdapter(TEST_AUDIT_DB)
        asyncio.run(adapter.log_event(_make_audit_event(event_type="case_received")))
        asyncio.run(adapter.log_event(_make_audit_event(event_type="ai_generated")))
        asyncio.run(adapter.log_event(_make_audit_event(event_type="final_decision")))
        events = asyncio.run(adapter.get_events_by_case("case-001"))
        assert len(events) == 3
        event_types = [e.event_type for e in events]
        assert "case_received" in event_types
        assert "ai_generated" in event_types
        assert "final_decision" in event_types

    def test_events_for_different_cases(self):
        adapter = SQLiteAuditAdapter(TEST_AUDIT_DB)
        asyncio.run(adapter.log_event(_make_audit_event(case_id="c1")))
        asyncio.run(adapter.log_event(_make_audit_event(case_id="c2")))
        events_c1 = asyncio.run(adapter.get_events_by_case("c1"))
        events_c2 = asyncio.run(adapter.get_events_by_case("c2"))
        assert len(events_c1) == 1
        assert len(events_c2) == 1

    def test_get_events_empty(self):
        adapter = SQLiteAuditAdapter(TEST_AUDIT_DB)
        events = asyncio.run(adapter.get_events_by_case("nonexistent"))
        assert len(events) == 0

    def test_event_has_timestamp(self):
        adapter = SQLiteAuditAdapter(TEST_AUDIT_DB)
        event = _make_audit_event()
        asyncio.run(adapter.log_event(event))
        events = asyncio.run(adapter.get_events_by_case("case-001"))
        assert events[0].timestamp == "2026-09-08T12:00:00Z"

    def test_event_has_details(self):
        adapter = SQLiteAuditAdapter(TEST_AUDIT_DB)
        event = AuditEvent(
            event_id="ae-test",
            case_id="case-001",
            event_type="test",
            timestamp="2026-09-08T12:00:00Z",
            details={"key": "value", "nested": {"a": 1}},
        )
        asyncio.run(adapter.log_event(event))
        events = asyncio.run(adapter.get_events_by_case("case-001"))
        assert events[0].details == {"key": "value", "nested": {"a": 1}}