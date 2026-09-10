import asyncio
import json
import sys

import pytest

sys.path.insert(0, "src")

from case_core.contracts.audit import AuditEvent
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.error import ErrorCategory
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.urban_policy import UrbanPolicy
from case_core.ports.audit import AuditPort
from case_core.reliability.pipeline import (
    ReliabilityPipeline,
    MAX_VALIDATION_RETRIES,
    MAX_TRANSIENT_RETRIES,
    TOTAL_TIMEOUT_SECONDS,
)


class InMemoryAuditPort(AuditPort):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)

    async def get_events_by_case(self, case_id: str) -> list[AuditEvent]:
        return [e for e in self.events if e.case_id == case_id]


def _make_evidence() -> EvidenceItem:
    return EvidenceItem(
        id="ev-001",
        type=EvidenceType.TEXT,
        content="Falla en farola principal",
        source="report",
        confidence=0.9,
        extracted_at="2026-09-08T12:00:00Z",
    )


def _make_case(with_evidence: bool = True) -> OperationalCase:
    return OperationalCase(
        case_id="case-001",
        report_text="Falla en farola de la calle principal",
        domain="urban_operations",
        urgency=UrgencyLevel.HIGH,
        evidence=[_make_evidence()] if with_evidence else [],
    )


VALID_RESPONSE = json.dumps({
    "decision": "approve",
    "reason": "Standard urban maintenance case with sufficient evidence provided",
    "urgency": "MEDIUM",
    "confidence": 0.85,
    "evidence_summary": "Report text validated, single evidence item provided",
})


class TestPipelineParsing:
    def test_parse_valid_json(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data, err = pipeline.parse(VALID_RESPONSE)
        assert err is None
        assert data["decision"] == "approve"

    def test_parse_invalid_json(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data, err = pipeline.parse("not json")
        assert err is not None
        assert err.category == ErrorCategory.PARSING
        assert data is None

    def test_parse_empty_string(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data, err = pipeline.parse("")
        assert err is not None
        assert err.category == ErrorCategory.PARSING


class TestPipelineSchemaValidation:
    def test_valid_schema(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        result, err = pipeline.schema_validate(data)
        assert err is None
        assert result is not None

    def test_missing_fields(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data, err = pipeline.schema_validate({"decision": "approve"})
        assert err is not None
        assert err.category == ErrorCategory.SCHEMA_VALIDATION

    def test_invalid_decision(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        data["decision"] = "invalid"
        result, err = pipeline.schema_validate(data)
        assert err is not None
        assert err.category == ErrorCategory.SCHEMA_VALIDATION

    def test_invalid_urgency(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        data["urgency"] = "INVALID"
        result, err = pipeline.schema_validate(data)
        assert err is not None
        assert err.category == ErrorCategory.SCHEMA_VALIDATION

    def test_invalid_confidence_type(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        data["confidence"] = "high"
        result, err = pipeline.schema_validate(data)
        assert err is not None
        assert err.category == ErrorCategory.SCHEMA_VALIDATION

    def test_confidence_out_of_range(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        data["confidence"] = 1.5
        result, err = pipeline.schema_validate(data)
        assert err is not None
        assert err.category == ErrorCategory.SEMANTIC_VALIDATION


class TestPipelineSemanticValidation:
    def test_valid_semantics(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        result, err = pipeline.semantic_validate(data)
        assert err is None

    def test_reason_too_short(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        data["reason"] = "short"
        result, err = pipeline.semantic_validate(data)
        assert err is not None
        assert err.category == ErrorCategory.SEMANTIC_VALIDATION

    def test_evidence_summary_too_short(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        data["evidence_summary"] = "ok"
        result, err = pipeline.semantic_validate(data)
        assert err is not None
        assert err.category == ErrorCategory.SEMANTIC_VALIDATION


class TestPipelineDomainValidation:
    def test_valid_domain(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        case = _make_case()
        result, err = pipeline.domain_validate(data, case)
        assert err is None

    def test_empty_evidence_fails(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        data = json.loads(VALID_RESPONSE)
        case = _make_case(with_evidence=False)
        result, err = pipeline.domain_validate(data, case)
        assert err is not None
        assert err.category == ErrorCategory.DOMAIN_VALIDATION


class TestPipelineEndToEnd:
    def test_full_pipeline_success(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        case = _make_case()
        decision, err = asyncio.run(
            pipeline.run(VALID_RESPONSE, case)
        )
        assert err is None
        assert decision is not None
        assert decision.action == "approve"
        assert decision.case_id == "case-001"
        assert decision.processing_time_ms >= 0

    def test_full_pipeline_parse_error(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        case = _make_case()
        decision, err = asyncio.run(
            pipeline.run("invalid json", case)
        )
        assert err is not None
        assert decision is None

    def test_full_pipeline_schema_error(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        case = _make_case()
        decision, err = asyncio.run(
            pipeline.run(json.dumps({"decision": "approve"}), case)
        )
        assert err is not None
        assert decision is None

    def test_full_pipeline_escalate(self):
        pipeline = ReliabilityPipeline(UrbanPolicy())
        case = _make_case()
        response = json.dumps({
            "decision": "escalate",
            "reason": "High urgency case requires immediate human review by specialist",
            "urgency": "HIGH",
            "confidence": 0.60,
            "evidence_summary": "Emergency keywords detected in report text",
        })
        decision, err = asyncio.run(
            pipeline.run(response, case)
        )
        assert err is None
        assert decision.action == "escalate"
        assert decision.urgency == "HIGH"


class TestRetryLoop:
    def test_retry_success_after_validation_failure(self):
        from case_core.contracts.llm import LLMRequest, DecodingParameters
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case()

        bad_response = json.dumps({"decision": "approve"})
        good_response = VALID_RESPONSE
        call_count = [0]

        fake_request = LLMRequest(
            messages=[{"role": "user", "content": "test"}],
            response_schema={"type": "object"},
            decoding_parameters=DecodingParameters(temperature=0.0),
        )

        class MockProviderRetry:
            async def complete(self, req):
                idx = call_count[0]
                call_count[0] += 1
                from case_core.contracts.llm import LLMResponse
                from case_core.contracts.telemetry import TokenUsage
                raw = good_response if idx > 0 else bad_response
                return LLMResponse(
                    raw_output=raw,
                    parsed=None,
                    usage=TokenUsage(),
                    model="mock",
                    provider="mock",
                    latency_ms=1.0,
                    finish_reason="stop",
                )

        decision, err = asyncio.run(
            pipeline.run(bad_response, case, provider=MockProviderRetry(), llm_request=fake_request)
        )
        assert err is None
        assert decision is not None
        assert decision.action == "approve"
        assert call_count[0] == 2

    def test_retry_exhaustion_terminal_failure(self):
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case()

        bad_response = json.dumps({"decision": "approve"})

        class MockProviderExhaust:
            async def complete(self, req):
                from case_core.contracts.llm import LLMResponse
                from case_core.contracts.telemetry import TokenUsage
                return LLMResponse(
                    raw_output=bad_response,
                    parsed=None,
                    usage=TokenUsage(),
                    model="mock",
                    provider="mock",
                    latency_ms=1.0,
                    finish_reason="stop",
                )

        decision, err = asyncio.run(
            pipeline.run(bad_response, case, provider=MockProviderExhaust(), llm_request=None)
        )
        assert err is not None
        assert decision is None
        assert err.details["requires_manual_review"] is True
        assert err.details["processing_lifecycle"] == "terminal_failure"

    def test_retry_exhaustion_creates_audit_events(self):
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case()

        bad_response = json.dumps({"decision": "approve"})

        class MockProviderExhaust:
            async def complete(self, req):
                from case_core.contracts.llm import LLMResponse
                from case_core.contracts.telemetry import TokenUsage
                return LLMResponse(
                    raw_output=bad_response,
                    parsed=None,
                    usage=TokenUsage(),
                    model="mock",
                    provider="mock",
                    latency_ms=1.0,
                    finish_reason="stop",
                )

        asyncio.run(
            pipeline.run(bad_response, case, provider=MockProviderExhaust(), llm_request=None)
        )
        event_types = [e.event_type for e in audit.events]
        assert "CASE_RECEIVED" in event_types
        assert "VALIDATION_FAILED" in event_types
        assert "REPAIR_TRIGGERED" in event_types
        assert "HUMAN_REVIEW" in event_types

    def test_non_retryable_error_immediate_failure(self):
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case(with_evidence=False)

        decision, err = asyncio.run(
            pipeline.run(VALID_RESPONSE, case)
        )
        assert err is not None
        assert decision is None
        assert err.retryable is False


class TestTimeout:
    def test_timeout_budget_respected(self):
        start_time = [0.0]
        current_time = [0.0]

        def mock_time():
            current_time[0] += 0.1
            return current_time[0]

        pipeline = ReliabilityPipeline(UrbanPolicy(), time_fn=mock_time)
        case = _make_case()

        decision, err = asyncio.run(
            pipeline.run("not json", case)
        )
        assert err is not None


class TestAuditEvents:
    def test_success_produces_case_received_and_final_decision(self):
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case()

        asyncio.run(
            pipeline.run(VALID_RESPONSE, case)
        )
        event_types = [e.event_type for e in audit.events]
        assert "CASE_RECEIVED" in event_types
        assert "AI_GENERATED" in event_types
        assert "FINAL_DECISION" in event_types

    def test_audit_events_have_required_fields(self):
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case()

        asyncio.run(
            pipeline.run(VALID_RESPONSE, case)
        )
        for event in audit.events:
            assert event.event_id is not None
            assert event.case_id == "case-001"
            assert event.event_type is not None
            assert event.timestamp is not None
            assert isinstance(event.details, dict)

    def test_audit_events_persisted(self):
        audit = InMemoryAuditPort()
        pipeline = ReliabilityPipeline(UrbanPolicy(), audit_port=audit)
        case = _make_case()

        asyncio.run(
            pipeline.run(VALID_RESPONSE, case)
        )
        retrieved = asyncio.run(
            audit.get_events_by_case("case-001")
        )
        assert len(retrieved) == len(audit.events)