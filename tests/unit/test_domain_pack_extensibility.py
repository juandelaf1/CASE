"""Proof that CASE core is domain-agnostic: a custom domain pack plugs in without core changes."""
from __future__ import annotations

from typing import Any

import pytest

from case_core.application.engine import TriageEngine
from case_core.contracts.automation import AutomationDecision, RiskAssessment, RiskLevel
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.registry import DomainRegistry
from case_core.ports.automation import AutomationPolicy
from case_core.ports.domain import DomainPolicy
from case_core.providers.mock import MockProvider


class DemoSupportPolicy(DomainPolicy):
    @property
    def domain_name(self) -> str:
        return "customer_support"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "At least one evidence item required"
        return True, "ok"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if "outage" in text or "critical" in text:
            return "CRITICAL"
        return "MEDIUM"

    def get_domain_context(self) -> dict[str, Any]:
        return {"domain": self.domain_name, "sla_hours": 4}


class DemoSupportAutomation(AutomationPolicy):
    @property
    def domain_name(self) -> str:
        return "customer_support"

    def assess_risk(self, case: OperationalCase, data: dict[str, Any], validation_status: str, evidence_quality: str, confidence: float) -> RiskAssessment:
        high = "outage" in case.report_text.lower()
        risk_level = RiskLevel.HIGH if high else RiskLevel.LOW
        decision = AutomationDecision.HUMAN_REVIEW if high else AutomationDecision.AUTO_APPROVE
        return RiskAssessment(
            decision_id=f"ra-{case.case_id}",
            case_id=case.case_id,
            domain=self.domain_name,
            risk_level=risk_level,
            automation_decision=decision,
            confidence=confidence,
            factors=["outage_keyword"] if high else ["standard_ticket"],
            requires_hitl=high,
            policy_violations=[],
            evidence_quality=evidence_quality,
            validation_status=validation_status,
            justification="outage requires human review" if high else "standard ticket",
        )

    def get_risk_factors(self) -> list[str]:
        return ["outage_keyword", "confidence"]

    def get_automation_rules(self) -> dict[str, Any]:
        return {"outage": "HUMAN_REVIEW", "default": "AUTO_APPROVE"}


@pytest.mark.asyncio
async def test_custom_domain_pack_runs_through_engine():
    registry = DomainRegistry()
    registry.register(DemoSupportPolicy())
    engine = TriageEngine(
        domain_registry=registry,
        provider=MockProvider(),
        automation_policy_fn=lambda domain: DemoSupportAutomation() if domain == "customer_support" else None,
    )
    case = OperationalCase(
        case_id="SUP-1",
        report_text="Customer reports critical outage in payment flow",
        domain="customer_support",
        urgency=UrgencyLevel.HIGH,
        evidence=[EvidenceItem(id="ev-1", type=EvidenceType.TEXT, content="users cannot pay", source="ticket", confidence=0.9, extracted_at="2026-01-01T00:00:00Z")],
    )
    result = await engine.execute(case)
    assert result.decision is not None
    assert result.error is None
    assert result.decision.domain == "customer_support"
