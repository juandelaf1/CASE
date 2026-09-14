import ast
import inspect
import json
import sys

sys.path.insert(0, "src")

from case_core.application.engine import TriageEngine, TriageResult
from case_core.contracts.audit import AuditEvent
from case_core.contracts.error import CASEError, ErrorCategory
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.lifecycle import DecisionLifecycle, ProcessingLifecycle
from case_core.contracts.llm import LLMRequest, LLMResponse
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.contracts.telemetry import TokenUsage
from case_core.domain.infrastructure_policy import InfrastructurePolicy
from case_core.domain.logistics_policy import LogisticsPolicy
from case_core.domain.registry import DomainRegistry
from case_core.domain.urban_policy import UrbanPolicy
from case_core.ports.audit import AuditPort
from case_core.ports.decision_repository import DecisionRepositoryPort
from case_core.ports.llm import LLMProvider

VALID_RESPONSE = json.dumps({
    "decision": "approve",
    "reason": "Standard urban maintenance case with sufficient evidence provided",
    "urgency": "MEDIUM",
    "confidence": 0.85,
    "evidence_summary": "Report text validated, single evidence item provided",
})

LOGISTICS_RESPONSE = json.dumps({
    "decision": "approve",
    "reason": "Logistics route optimization approved for delivery",
    "urgency": "MEDIUM",
    "confidence": 0.78,
    "evidence_summary": "Route data and metrics provided for logistics case",
})

INFRASTRUCTURE_RESPONSE = json.dumps({
    "decision": "escalate",
    "reason": "Infrastructure structural damage requires specialist review",
    "urgency": "HIGH",
    "confidence": 0.72,
    "evidence_summary": "Multiple evidence items indicate structural concerns",
})

INVALID_JSON = "this is not valid json {{{"


class InMemoryAuditPort(AuditPort):
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def log_event(self, event: AuditEvent) -> None:
        self.events.append(event)

    async def get_events_by_case(self, case_id: str) -> list[AuditEvent]:
        return [e for e in self.events if e.case_id == case_id]


class InMemoryDecisionRepository(DecisionRepositoryPort):
    def __init__(self) -> None:
        self.decisions: dict[str, object] = {}

    async def save_decision(self, decision: object) -> None:
        self.decisions[decision.decision_id] = decision

    async def get_decision(self, decision_id: str) -> object | None:
        return self.decisions.get(decision_id)

    async def get_decision_by_case(self, case_id: str) -> object | None:
        for d in self.decisions.values():
            if d.case_id == case_id:
                return d
        return None

    async def list_pending_review(self, limit: int = 100) -> list[object]:
        return [
            d for d in self.decisions.values()
            if hasattr(d, "lifecycle") and d.lifecycle == DecisionLifecycle.UNDER_REVIEW
        ][:limit]

    async def list_decisions(self, limit: int = 50, offset: int = 0) -> list[object]:
        all_d = sorted(self.decisions.values(), key=lambda d: getattr(d, "processing_time_ms", 0), reverse=True)
        return all_d[offset:offset + limit]

    async def count_decisions(self) -> int:
        return len(self.decisions)

    async def update_lifecycle(self, decision_id: str, lifecycle: str, actor: str = "human", justification: str = "", original_action: str = "", original_urgency: str = "", original_confidence: float = 0.0, original_evidence_summary: str = "") -> None:
        if decision_id in self.decisions:
            self.decisions[decision_id].lifecycle = DecisionLifecycle(lifecycle)


class FixedResponseProvider(LLMProvider):
    def __init__(self, response: str) -> None:
        self._response = response
        self.call_count = 0

    @property
    def name(self) -> str:
        return "mock"

    @property
    def model(self) -> str:
        return "mock-v1"

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.call_count += 1
        return LLMResponse(
            raw_output=self._response,
            parsed=None,
            usage=TokenUsage(prompt_tokens=100, completion_tokens=50, total_tokens=150),
            model=self.model,
            provider=self.name,
            latency_ms=10.0,
            finish_reason="stop",
        )

    async def health_check(self) -> bool:
        return True


def _make_evidence() -> EvidenceItem:
    return EvidenceItem(
        id="ev-001",
        type=EvidenceType.TEXT,
        content="Falla en farola principal",
        source="report",
        confidence=0.9,
        extracted_at="2026-09-08T12:00:00Z",
    )


def _make_two_evidence() -> list[EvidenceItem]:
    return [
        EvidenceItem(
            id="ev-001",
            type=EvidenceType.TEXT,
            content="Inspection report: scheduled maintenance",
            source="inspector",
            confidence=0.9,
            extracted_at="2026-09-08T12:00:00Z",
        ),
        EvidenceItem(
            id="ev-002",
            type=EvidenceType.METRIC,
            content="condition_score: good",
            source="sensor",
            confidence=0.85,
            extracted_at="2026-09-08T12:00:00Z",
        ),
    ]


def _make_urban_case() -> OperationalCase:
    return OperationalCase(
        case_id="case-urban-001",
        report_text="Street light damaged on Main Street near intersection",
        domain="urban_operations",
        urgency=UrgencyLevel.HIGH,
        evidence=[_make_evidence()],
    )


def _make_logistics_case() -> OperationalCase:
    return OperationalCase(
        case_id="case-logistics-001",
        report_text="Delivery truck delayed on highway due to traffic",
        domain="logistics",
        urgency=UrgencyLevel.MEDIUM,
        evidence=[EvidenceItem(
            id="ev-log-001",
            type=EvidenceType.TEXT,
            content="Shipment status: delayed",
            source="fleet_system",
            confidence=0.85,
            extracted_at="2026-09-08T12:00:00Z",
        )],
    )


def _make_infrastructure_case() -> OperationalCase:
    return OperationalCase(
        case_id="case-infra-001",
        report_text="Bridge structural crack detected during inspection",
        domain="infrastructure",
        urgency=UrgencyLevel.CRITICAL,
        evidence=[EvidenceItem(
            id="ev-infra-001",
            type=EvidenceType.TEXT,
            content="Structural inspection report: crack in support beam",
            source="inspection_team",
            confidence=0.92,
            extracted_at="2026-09-08T12:00:00Z",
        )],
    )


def _build_registry() -> DomainRegistry:
    registry = DomainRegistry()
    registry.register(UrbanPolicy())
    registry.register(LogisticsPolicy())
    registry.register(InfrastructurePolicy())
    return registry


class TestTriageEngineExecution:
    async def test_successful_execution(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        audit = InMemoryAuditPort()
        repo = InMemoryDecisionRepository()
        engine = TriageEngine(
            domain_registry=_build_registry(),
            provider=provider,
            audit_port=audit,
            decision_repository=repo,
        )

        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.error is None
        assert result.processing_lifecycle == ProcessingLifecycle.COMPLETED
        assert result.decision.action == "approve"
        assert result.decision.lifecycle == DecisionLifecycle.AI_PROPOSED
        assert result.decision.original_ai_proposal is not None
        assert provider.call_count == 1

    async def test_decision_persisted(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        repo = InMemoryDecisionRepository()
        engine = TriageEngine(
            domain_registry=_build_registry(),
            provider=provider,
            decision_repository=repo,
        )

        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.decision_id in repo.decisions

    async def test_audit_events_emitted(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        audit = InMemoryAuditPort()
        engine = TriageEngine(
            domain_registry=_build_registry(),
            provider=provider,
            audit_port=audit,
        )

        case = _make_urban_case()
        await engine.execute(case)

        event_types = [e.event_type for e in audit.events]
        assert "CASE_RECEIVED" in event_types
        assert "AI_GENERATED" in event_types
        assert "FINAL_DECISION" in event_types


class TestTriageEngineDomainResolution:
    async def test_unknown_domain_returns_error(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        engine = TriageEngine(domain_registry=_build_registry(), provider=provider)

        case = OperationalCase(
            case_id="case-bad",
            report_text="Test",
            domain="nonexistent_domain",
        )
        result = await engine.execute(case)

        assert result.decision is None
        assert result.error is not None
        assert result.error.category == ErrorCategory.DOMAIN_VALIDATION
        assert "Unknown domain" in result.error.message
        assert result.processing_lifecycle == ProcessingLifecycle.TERMINAL_FAILURE

    async def test_urban_domain_resolves(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        engine = TriageEngine(domain_registry=_build_registry(), provider=provider)

        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.domain == "urban_operations"

    async def test_logistics_domain_resolves(self):
        provider = FixedResponseProvider(LOGISTICS_RESPONSE)
        engine = TriageEngine(domain_registry=_build_registry(), provider=provider)

        case = _make_logistics_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.domain == "logistics"

    async def test_infrastructure_domain_resolves(self):
        provider = FixedResponseProvider(INFRASTRUCTURE_RESPONSE)
        engine = TriageEngine(domain_registry=_build_registry(), provider=provider)

        case = _make_infrastructure_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.domain == "infrastructure"


class TestTriageEngineProvider:
    async def test_provider_invoked_once(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        engine = TriageEngine(domain_registry=_build_registry(), provider=provider)

        case = _make_urban_case()
        await engine.execute(case)

        assert provider.call_count == 1


class TestTriageEngineFailure:
    async def test_invalid_json_propagates_error(self):
        provider = FixedResponseProvider(INVALID_JSON)
        engine = TriageEngine(domain_registry=_build_registry(), provider=provider)

        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is None
        assert result.error is not None
        assert result.processing_lifecycle == ProcessingLifecycle.TERMINAL_FAILURE

    async def test_no_repository_still_works(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        engine = TriageEngine(
            domain_registry=_build_registry(),
            provider=provider,
            decision_repository=None,
        )

        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.error is None

    async def test_no_audit_still_works(self):
        provider = FixedResponseProvider(VALID_RESPONSE)
        engine = TriageEngine(
            domain_registry=_build_registry(),
            provider=provider,
            audit_port=None,
        )

        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.error is None


class TestTriageEngineDomainAgnostic:
    def test_no_domain_specific_logic_in_engine(self):
        source = inspect.getsource(TriageEngine)
        tree = ast.parse(source)

        code_lines = []
        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                code_lines.append(ast.get_source_segment(source, node) or "")

        all_code = "\n".join(code_lines)
        assert 'if domain == "logistics"' not in all_code
        assert 'if domain == "urban' not in all_code
        assert 'if domain == "infrastructure"' not in all_code


class TestTriageResult:
    def test_default_values(self):
        result = TriageResult()
        assert result.decision is None
        assert result.error is None
        assert result.processing_lifecycle == ProcessingLifecycle.RECEIVED

    def test_error_result(self):
        result = TriageResult(
            error=CASEError(category=ErrorCategory.PARSING, message="test"),
            processing_lifecycle=ProcessingLifecycle.TERMINAL_FAILURE,
        )
        assert result.decision is None
        assert result.error is not None
        assert result.processing_lifecycle == ProcessingLifecycle.TERMINAL_FAILURE


class TestTriageEngineAllDomains:
    async def test_all_three_domains_produce_decisions(self):
        cases = [
            (_make_urban_case(), VALID_RESPONSE),
            (_make_logistics_case(), LOGISTICS_RESPONSE),
            (_make_infrastructure_case(), INFRASTRUCTURE_RESPONSE),
        ]

        for case, response in cases:
            provider = FixedResponseProvider(response)
            engine = TriageEngine(domain_registry=_build_registry(), provider=provider)
            result = await engine.execute(case)

            assert result.decision is not None, f"Failed for domain: {case.domain}"
            assert result.error is None, f"Error for domain: {case.domain}"
            assert result.decision.domain == case.domain


class TestTriageEngineAutomation:
    """Integration tests: TriageEngine → ReliabilityPipeline → AutomationEvaluator → lifecycle."""

    def _make_engine(self, provider_response: str, domain: str = "urban_operations", automation_policy_fn=None):
        provider = FixedResponseProvider(provider_response)
        audit = InMemoryAuditPort()
        repo = InMemoryDecisionRepository()
        return TriageEngine(
            domain_registry=_build_registry(),
            provider=provider,
            audit_port=audit,
            decision_repository=repo,
            automation_policy_fn=automation_policy_fn,
        ), audit, repo

    def _make_domain_agnostic_automation_fn(self):
        from case_core.domain.default_automation import DefaultAutomationPolicy
        policy = DefaultAutomationPolicy()
        return lambda domain: policy

    async def test_auto_approve_low_risk(self):
        """LOW risk + valid validation + high confidence + sufficient evidence → APPROVED."""
        from case_core.domain.default_automation import DefaultAutomationPolicy

        response = json.dumps({
            "decision": "approve",
            "reason": "Standard maintenance case with clear evidence provided",
            "urgency": "LOW",
            "confidence": 0.9,
            "evidence_summary": "Sufficient evidence from inspection report",
        })
        engine, audit, repo = self._make_engine(
            response,
            automation_policy_fn=lambda d: DefaultAutomationPolicy(),
        )
        case = OperationalCase(
            case_id="case-low",
            report_text="Scheduled street light inspection completed",
            domain="urban_operations",
            urgency=UrgencyLevel.LOW,
            evidence=_make_two_evidence(),
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.APPROVED
        event_types = [e.event_type for e in audit.events]
        assert "AUTO_APPROVED" in event_types
        assert "AUTOMATION_ASSESSED" in event_types

    async def test_human_review_medium_risk(self):
        """MEDIUM urgency → HUMAN_REVIEW."""
        response = json.dumps({
            "decision": "approve",
            "reason": "Case requires careful review due to moderate urgency",
            "urgency": "MEDIUM",
            "confidence": 0.85,
            "evidence_summary": "Standard evidence provided for review",
        })
        engine, audit, repo = self._make_engine(
            response,
            automation_policy_fn=self._make_domain_agnostic_automation_fn(),
        )
        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.UNDER_REVIEW
        event_types = [e.event_type for e in audit.events]
        assert "AUTO_HUMAN_REVIEW" in event_types

    async def test_escalate_critical(self):
        """CRITICAL urgency → ESCALATE."""
        response = json.dumps({
            "decision": "escalate",
            "reason": "Critical structural issue requiring immediate specialist attention",
            "urgency": "CRITICAL",
            "confidence": 0.75,
            "evidence_summary": "Multiple critical indicators detected in inspection",
        })
        engine, audit, repo = self._make_engine(
            response,
            automation_policy_fn=self._make_domain_agnostic_automation_fn(),
        )
        case = OperationalCase(
            case_id="case-critical",
            report_text="Emergency bridge structural failure imminent danger",
            domain="urban_operations",
            urgency=UrgencyLevel.CRITICAL,
            evidence=[_make_evidence()],
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.ESCALATED
        event_types = [e.event_type for e in audit.events]
        assert "AUTO_ESCALATED" in event_types

    async def test_urban_uses_default_policy(self):
        """Urban domain uses DefaultAutomationPolicy."""
        from case_core.domain.default_automation import DefaultAutomationPolicy

        response = json.dumps({
            "decision": "approve",
            "reason": "Urban maintenance case with clear evidence",
            "urgency": "LOW",
            "confidence": 0.88,
            "evidence_summary": "Evidence validated for urban case",
        })
        engine, audit, repo = self._make_engine(
            response,
            domain="urban_operations",
            automation_policy_fn=lambda d: DefaultAutomationPolicy() if d == "urban_operations" else None,
        )
        case = OperationalCase(
            case_id="case-urban-auto",
            report_text="Scheduled maintenance completed on schedule",
            domain="urban_operations",
            urgency=UrgencyLevel.LOW,
            evidence=_make_two_evidence(),
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.APPROVED

    async def test_infrastructure_uses_default_policy(self):
        """Infrastructure domain uses DefaultAutomationPolicy."""
        from case_core.domain.default_automation import DefaultAutomationPolicy

        response = json.dumps({
            "decision": "approve",
            "reason": "Infrastructure inspection passed with sufficient data",
            "urgency": "LOW",
            "confidence": 0.92,
            "evidence_summary": "Structural inspection data validated",
        })
        engine, audit, repo = self._make_engine(
            response,
            domain="infrastructure",
            automation_policy_fn=lambda d: DefaultAutomationPolicy() if d == "infrastructure" else None,
        )
        case = OperationalCase(
            case_id="case-infra-auto",
            report_text="Routine infrastructure inspection completed",
            domain="infrastructure",
            urgency=UrgencyLevel.LOW,
            evidence=[
                EvidenceItem(
                    id="ev-infra-001",
                    type=EvidenceType.TEXT,
                    content="Routine inspection: no issues found",
                    source="inspection_team",
                    confidence=0.92,
                    extracted_at="2026-09-08T12:00:00Z",
                ),
                EvidenceItem(
                    id="ev-infra-002",
                    type=EvidenceType.METRIC,
                    content="structural_integrity: 0.95",
                    source="sensor",
                    confidence=0.88,
                    extracted_at="2026-09-08T12:00:00Z",
                ),
            ],
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.APPROVED

    async def test_logistics_uses_logistics_policy(self):
        """Logistics domain uses LogisticsAutomationPolicy."""
        from case_core.domain.logistics_automation import LogisticsAutomationPolicy

        response = json.dumps({
            "decision": "approve",
            "reason": "Logistics delivery case with clear evidence",
            "urgency": "LOW",
            "confidence": 0.9,
            "evidence_summary": "Delivery status confirmed by tracking system",
        })
        engine, audit, repo = self._make_engine(
            response,
            domain="logistics",
            automation_policy_fn=lambda d: LogisticsAutomationPolicy() if d == "logistics" else None,
        )
        case = OperationalCase(
            case_id="case-log-auto",
            report_text="Package delivered successfully on time",
            domain="logistics",
            urgency=UrgencyLevel.LOW,
            evidence=[
                EvidenceItem(
                    id="ev-log-001",
                    type=EvidenceType.TEXT,
                    content="Delivery confirmed by driver",
                    source="fleet_system",
                    confidence=0.9,
                    extracted_at="2026-09-08T12:00:00Z",
                ),
                EvidenceItem(
                    id="ev-log-002",
                    type=EvidenceType.METRIC,
                    content="delivery_status: on_time",
                    source="tracking",
                    confidence=0.95,
                    extracted_at="2026-09-08T12:00:00Z",
                ),
            ],
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.APPROVED

    async def test_no_automation_policy_falls_back_to_ai_proposed(self):
        """Without automation_policy_fn, lifecycle stays AI_PROPOSED."""
        engine, audit, repo = self._make_engine(VALID_RESPONSE, automation_policy_fn=None)
        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.AI_PROPOSED
        event_types = [e.event_type for e in audit.events]
        assert "AUTOMATION_ASSESSED" not in event_types

    async def test_auto_approved_not_in_hitl_queue(self):
        """AUTO_APPROVED decisions should not appear in HITL pending queue."""
        response = json.dumps({
            "decision": "approve",
            "reason": "Clear low-risk case with strong evidence",
            "urgency": "LOW",
            "confidence": 0.95,
            "evidence_summary": "Strong evidence from multiple sources",
        })
        engine, audit, repo = self._make_engine(
            response,
            automation_policy_fn=self._make_domain_agnostic_automation_fn(),
        )
        case = OperationalCase(
            case_id="case-hitl-check",
            report_text="Routine scheduled maintenance completed",
            domain="urban_operations",
            urgency=UrgencyLevel.LOW,
            evidence=_make_two_evidence(),
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.APPROVED
        pending = await repo.list_pending_review()
        assert len(pending) == 0

    async def test_human_review_in_hitl_queue(self):
        """HUMAN_REVIEW decisions appear in HITL pending queue."""
        response = json.dumps({
            "decision": "approve",
            "reason": "Moderate risk case requiring human verification",
            "urgency": "MEDIUM",
            "confidence": 0.85,
            "evidence_summary": "Standard evidence requiring review",
        })
        engine, audit, repo = self._make_engine(
            response,
            automation_policy_fn=self._make_domain_agnostic_automation_fn(),
        )
        case = _make_urban_case()
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.UNDER_REVIEW
        pending = await repo.list_pending_review()
        assert len(pending) == 1

    async def test_escalated_decision_persisted(self):
        """ESCALATED decisions are persisted and audited."""
        response = json.dumps({
            "decision": "escalate",
            "reason": "Critical issue requiring immediate supervisor attention",
            "urgency": "CRITICAL",
            "confidence": 0.7,
            "evidence_summary": "Critical indicators detected",
        })
        engine, audit, repo = self._make_engine(
            response,
            automation_policy_fn=self._make_domain_agnostic_automation_fn(),
        )
        case = OperationalCase(
            case_id="case-esc",
            report_text="Emergency situation with collapse danger",
            domain="urban_operations",
            urgency=UrgencyLevel.CRITICAL,
            evidence=[_make_evidence()],
        )
        result = await engine.execute(case)

        assert result.decision is not None
        assert result.decision.lifecycle == DecisionLifecycle.ESCALATED
        persisted = await repo.get_decision(result.decision.decision_id)
        assert persisted is not None
        assert persisted.lifecycle == DecisionLifecycle.ESCALATED
