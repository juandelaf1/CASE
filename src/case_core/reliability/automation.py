from typing import Any

from case_core.contracts.automation import AutomationDecision, RiskAssessment
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.automation import AutomationPolicy


class AutomationEvaluator:
    """Evaluates automation decisions based on domain-specific policies."""

    def __init__(self, automation_policy: AutomationPolicy) -> None:
        self._automation_policy = automation_policy

    def evaluate(
        self,
        case: OperationalCase,
        data: dict[str, Any],
        validation_passed: bool,
        evidence_count: int,
        confidence: float,
    ) -> RiskAssessment:
        validation_status = "valid" if validation_passed else "invalid"
        evidence_quality = self._assess_evidence_quality(evidence_count, confidence)

        return self._automation_policy.assess_risk(
            case=case,
            data=data,
            validation_status=validation_status,
            evidence_quality=evidence_quality,
            confidence=confidence,
        )

    def _assess_evidence_quality(self, evidence_count: int, confidence: float) -> str:
        if evidence_count == 0:
            return "none"
        if evidence_count < 2 or confidence < 0.6:
            return "insufficient"
        if evidence_count >= 3 and confidence >= 0.8:
            return "strong"
        return "sufficient"

    def should_automate(self, assessment: RiskAssessment) -> bool:
        return assessment.automation_decision == AutomationDecision.AUTO_APPROVE

    def requires_human_review(self, assessment: RiskAssessment) -> bool:
        return assessment.automation_decision == AutomationDecision.HUMAN_REVIEW

    def requires_escalation(self, assessment: RiskAssessment) -> bool:
        return assessment.automation_decision == AutomationDecision.ESCALATE
