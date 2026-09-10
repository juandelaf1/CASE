import sys
import pytest

sys.path.insert(0, "src")

from case_core.contracts.lifecycle import ProcessingLifecycle, DecisionLifecycle
from case_core.contracts.decision import AIProposal, HumanOverride, TriageDecision
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.error import CASEError, ErrorCategory
from case_core.contracts.audit import AuditEvent
from case_core.contracts.telemetry import TokenUsage, OperationalTelemetry, LLMTelemetry
from case_core.contracts.llm import DecodingParameters, LLMRequest, LLMResponse
from case_core.contracts.operational_case import UrgencyLevel, OperationalCase


class TestLifecycleEnums:
    def test_processing_lifecycle_values(self):
        assert ProcessingLifecycle.RECEIVED.value == "received"
        assert ProcessingLifecycle.COMPLETED.value == "completed"
        assert ProcessingLifecycle.FAILED.value == "failed"
        assert ProcessingLifecycle.TERMINAL_FAILURE.value == "terminal_failure"
        assert len(list(ProcessingLifecycle)) == 20

    def test_decision_lifecycle_values(self):
        assert DecisionLifecycle.AI_PROPOSED.value == "ai_proposed"
        assert DecisionLifecycle.UNDER_REVIEW.value == "under_review"
        assert DecisionLifecycle.APPROVED.value == "approved"
        assert len(list(DecisionLifecycle)) == 8


class TestEvidence:
    def test_evidence_item_creation(self):
        e = EvidenceItem(
            id="ev-001",
            type=EvidenceType.TEXT,
            content="Falla en semaforo",
            source="report",
            confidence=0.95,
            extracted_at="2026-09-08T12:00:00Z",
        )
        assert e.id == "ev-001"
        assert e.type == EvidenceType.TEXT
        assert e.confidence == 0.95

    def test_evidence_item_serialization(self):
        e = EvidenceItem(
            id="ev-001",
            type=EvidenceType.IMAGE,
            content="foto",
            source="camera",
            confidence=0.8,
            extracted_at="2026-09-08T12:00:00Z",
        )
        d = e.model_dump()
        assert d["id"] == "ev-001"
        assert d["type"] == "image"


class TestError:
    def test_case_error_creation(self):
        err = CASEError(
            category=ErrorCategory.PARSING,
            message="Invalid JSON",
            recoverable=True,
            retryable=True,
        )
        assert err.category == ErrorCategory.PARSING
        assert err.recoverable is True

    def test_case_error_serialization(self):
        err = CASEError(
            category=ErrorCategory.TRANSIENT,
            message="Timeout",
        )
        d = err.model_dump()
        assert d["category"] == "transient"
        assert d["retryable"] is False


class TestAuditEvent:
    def test_audit_event_creation(self):
        a = AuditEvent(
            event_id="ae-001",
            case_id="case-001",
            decision_id="dec-001",
            event_type="case_received",
            timestamp="2026-09-08T12:00:00Z",
            details={"source": "api"},
        )
        assert a.event_id == "ae-001"
        assert a.actor == "system"

    def test_audit_event_serialization(self):
        a = AuditEvent(
            event_id="ae-001",
            case_id="case-001",
            event_type="case_received",
            timestamp="2026-09-08T12:00:00Z",
        )
        d = a.model_dump()
        assert d["actor"] == "system"


class TestTelemetry:
    def test_token_usage(self):
        t = TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150)
        assert t.total_tokens == 150

    def test_llm_telemetry(self):
        lt = LLMTelemetry(
            provider="mock",
            model="mock-v1",
            latency_ms=123.4,
            tokens=TokenUsage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
        )
        assert lt.provider == "mock"
        assert lt.tokens.total_tokens == 15


class TestLLMContracts:
    def test_llm_request(self):
        req = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            response_schema={"type": "object"},
            decoding_parameters=DecodingParameters(temperature=0.0),
        )
        assert len(req.messages) == 1
        assert req.decoding_parameters.temperature == 0.0

    def test_llm_response(self):
        resp = LLMResponse(
            raw_output='{"decision": "approve"}',
            parsed={"decision": "approve"},
            usage=TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30),
            model="mock-v1",
            provider="mock",
            latency_ms=1.0,
            finish_reason="stop",
        )
        assert resp.raw_output == '{"decision": "approve"}'
        assert resp.parsed == {"decision": "approve"}
        assert resp.provider == "mock"
        assert resp.latency_ms == 1.0
        assert resp.finish_reason == "stop"

    def test_llm_response_no_domain_policy(self):
        req = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            response_schema={"type": "object"},
            decoding_parameters=DecodingParameters(temperature=0.0),
        )
        assert not hasattr(req, "domain_policy")


class TestOperationalCase:
    def test_operational_case_creation(self):
        case = OperationalCase(
            case_id="case-001",
            report_text="Falla en farola calle 5",
            domain="urban_operations",
            urgency=UrgencyLevel.HIGH,
        )
        assert case.case_id == "case-001"
        assert case.urgency == UrgencyLevel.HIGH
        assert case.status == ProcessingLifecycle.RECEIVED

    def test_operational_case_default_values(self):
        case = OperationalCase(
            case_id="case-002",
            report_text="Test",
            domain="urban_operations",
        )
        assert case.urgency == UrgencyLevel.MEDIUM
        assert case.evidence == []
        assert case.metadata == {}

    def test_urgency_levels(self):
        assert UrgencyLevel.LOW.value == "LOW"
        assert UrgencyLevel.MEDIUM.value == "MEDIUM"
        assert UrgencyLevel.HIGH.value == "HIGH"
        assert UrgencyLevel.CRITICAL.value == "CRITICAL"


class TestAIProposal:
    def test_ai_proposal_creation(self):
        proposal = AIProposal(action="approve", reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok")
        assert proposal.action == "approve"
        assert proposal.confidence == 0.9

    def test_ai_proposal_serialization(self):
        proposal = AIProposal(action="approve", reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok")
        d = proposal.model_dump()
        assert d["action"] == "approve"


class TestHumanOverride:
    def test_human_override_creation(self):
        override = HumanOverride(
            actor="human", timestamp="2025-01-01T00:00:00Z", justification="approved",
            original_action="approve", original_urgency="LOW", original_confidence=0.9, original_evidence_summary="ok",
        )
        assert override.actor == "human"
        assert override.justification == "approved"

    def test_human_override_serialization(self):
        override = HumanOverride(
            actor="human", timestamp="2025-01-01T00:00:00Z", justification="approved",
            original_action="approve", original_urgency="LOW", original_confidence=0.9, original_evidence_summary="ok",
        )
        d = override.model_dump()
        assert d["original_action"] == "approve"


class TestTriageDecisionWithHumanTracking:
    def test_decision_with_original_ai_proposal(self):
        proposal = AIProposal(action="approve", reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok")
        decision = TriageDecision(
            decision_id="dec-1", case_id="case-1", domain="urban", action="approve",
            reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok",
            lifecycle=DecisionLifecycle.AI_PROPOSED, original_ai_proposal=proposal,
        )
        assert decision.original_ai_proposal is not None
        assert decision.original_ai_proposal.action == "approve"
        assert decision.lifecycle == DecisionLifecycle.AI_PROPOSED

    def test_decision_with_human_override(self):
        proposal = AIProposal(action="approve", reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok")
        override = HumanOverride(
            actor="human", timestamp="2025-01-01T00:00:00Z", justification="approved",
            original_action="approve", original_urgency="LOW", original_confidence=0.9, original_evidence_summary="ok",
        )
        decision = TriageDecision(
            decision_id="dec-1", case_id="case-1", domain="urban", action="reject",
            reason="rejected", urgency="LOW", confidence=0.5, evidence_summary="ok",
            lifecycle=DecisionLifecycle.APPROVED, original_ai_proposal=proposal, human_override=override,
        )
        assert decision.human_override is not None
        assert decision.human_override.actor == "human"
        assert decision.action == "reject"

    def test_model_dump_ext_includes_tracking(self):
        proposal = AIProposal(action="approve", reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok")
        decision = TriageDecision(
            decision_id="dec-1", case_id="case-1", domain="urban", action="approve",
            reason="valid", urgency="LOW", confidence=0.9, evidence_summary="ok",
            lifecycle=DecisionLifecycle.AI_PROPOSED, original_ai_proposal=proposal,
        )
        d = decision.model_dump_ext()
        assert "original_ai_proposal" in d
        assert d["original_ai_proposal"] is not None
        assert "human_override" in d
        assert d["human_override"] is None