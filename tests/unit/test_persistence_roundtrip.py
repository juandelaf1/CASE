"""Tests for persistence round-trip integrity."""
from __future__ import annotations

import os
import tempfile

import pytest

from case_core.contracts.decision import TriageDecision
from case_core.contracts.error import CASEError, ErrorCategory
from case_core.contracts.lifecycle import DecisionLifecycle
from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository


@pytest.fixture
def tmp_db() -> str:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


def _make_decision(
    decision_id: str = "d-1",
    case_id: str = "c-1",
    decision_rationale: str = "test rationale",
    decision_factors: list[str] | None = None,
    summary: str = "test summary for this case decision",
    error: CASEError | None = None,
) -> TriageDecision:
    return TriageDecision(
        decision_id=decision_id,
        case_id=case_id,
        domain="logistics",
        action="APPROVE",
        reason="low risk",
        urgency="MEDIUM",
        confidence=0.85,
        evidence_summary="test evidence",
        decision_rationale=decision_rationale,
        decision_factors=decision_factors or ["factor1", "factor2"],
        summary=summary,
        error=error,
        lifecycle=DecisionLifecycle.AI_PROPOSED,
        processing_time_ms=150.0,
        metadata={"key": "value"},
    )


class TestDecisionRoundTrip:
    async def test_basic_round_trip(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision()
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.decision_id == "d-1"
        assert loaded.case_id == "c-1"
        assert loaded.domain == "logistics"
        assert loaded.action == "APPROVE"
        assert loaded.confidence == 0.85

    async def test_preserves_decision_rationale(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision(decision_rationale="because of risk assessment")
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.decision_rationale == "because of risk assessment"

    async def test_preserves_decision_factors(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision(decision_factors=["risk", "cost", "timeline"])
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.decision_factors == ["risk", "cost", "timeline"]

    async def test_preserves_summary(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        summary = "approved low risk logistics case for this situation today now"
        decision = _make_decision(summary=summary)
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.summary == summary

    async def test_preserves_error(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        error = CASEError(category=ErrorCategory.TRANSIENT, message="timeout", recoverable=True)
        decision = _make_decision(error=error)
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.error is not None
        assert loaded.error.category == ErrorCategory.TRANSIENT
        assert loaded.error.message == "timeout"
        assert loaded.error.recoverable is True

    async def test_no_error_preserves_none(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision(error=None)
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.error is None

    async def test_preserves_metadata(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision()
        decision.metadata = {"source": "test", "version": 2}
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.metadata == {"source": "test", "version": 2}

    async def test_preserves_lifecycle(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision()
        decision.lifecycle = DecisionLifecycle.APPROVED
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.lifecycle == DecisionLifecycle.APPROVED

    async def test_empty_factors_round_trip(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        decision = _make_decision()
        decision.decision_factors = []
        await repo.save_decision(decision)
        loaded = await repo.get_decision("d-1")
        assert loaded is not None
        assert loaded.decision_factors == []

    async def test_get_nonexistent_returns_none(self, tmp_db: str) -> None:
        repo = SQLiteDecisionRepository(db_path=tmp_db)
        loaded = await repo.get_decision("nonexistent")
        assert loaded is None
