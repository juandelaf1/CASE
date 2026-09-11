from typing import Any

from case_core.contracts.automation import AutomationDecision, RiskAssessment, RiskLevel
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.automation import AutomationPolicy


class DefaultAutomationPolicy(AutomationPolicy):
    """Conservative automation policy for domains without specific risk assessment.

    Prioritizes false negative automation over unnecessary human review.
    When in doubt, sends to HUMAN_REVIEW.
    """

    @property
    def domain_name(self) -> str:
        return "default"

    def assess_risk(
        self,
        case: OperationalCase,
        data: dict[str, Any],
        validation_status: str,
        evidence_quality: str,
        confidence: float,
    ) -> RiskAssessment:
        factors: list[str] = []
        risk_level = RiskLevel.LOW
        policy_violations: list[str] = []

        urgency = data.get("urgency", "MEDIUM")
        case_urgency = case.urgency.value if hasattr(case.urgency, "value") else str(case.urgency)
        effective_urgency = self._get_effective_urgency(urgency, case_urgency)
        action = data.get("decision", "")

        if effective_urgency == "CRITICAL":
            risk_level = RiskLevel.CRITICAL
            factors.append("urgency_critical")
            policy_violations.append("critical_urgency_requires_escalation")
        elif effective_urgency == "HIGH":
            risk_level = RiskLevel.HIGH
            factors.append("urgency_high")
        elif effective_urgency == "MEDIUM":
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM
                factors.append("urgency_medium")

        if validation_status != "valid":
            risk_level = RiskLevel.HIGH
            factors.append("validation_failed")
            policy_violations.append("validation_failure")

        if evidence_quality == "insufficient":
            if risk_level.value in ("LOW", "MEDIUM"):
                risk_level = RiskLevel.MEDIUM
            factors.append("evidence_insufficient")
        elif evidence_quality == "none":
            risk_level = RiskLevel.HIGH
            factors.append("evidence_none")

        if confidence < 0.5:
            if risk_level.value in ("LOW", "MEDIUM"):
                risk_level = RiskLevel.MEDIUM
            factors.append("confidence_low")
        elif confidence < 0.7:
            factors.append("confidence_moderate")

        if action == "escalate":
            factors.append("action_escalate")
            if risk_level.value in ("LOW", "MEDIUM"):
                risk_level = RiskLevel.HIGH

        if action == "reject":
            factors.append("action_reject")
            if risk_level == RiskLevel.LOW:
                risk_level = RiskLevel.MEDIUM

        requires_hitl = self._requires_hitl(risk_level, confidence, evidence_quality)
        automation_decision = self._decide_automation(risk_level, requires_hitl, policy_violations)

        justification = self._build_justification(risk_level, automation_decision, factors, policy_violations)

        return RiskAssessment(
            decision_id=f"ra-{case.case_id}",
            case_id=case.case_id,
            domain=self.domain_name,
            risk_level=risk_level,
            automation_decision=automation_decision,
            confidence=confidence,
            factors=factors,
            requires_hitl=requires_hitl,
            policy_violations=policy_violations,
            evidence_quality=evidence_quality,
            validation_status=validation_status,
            justification=justification,
        )

    def _requires_hitl(self, risk_level: RiskLevel, confidence: float, evidence_quality: str) -> bool:
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True
        if confidence < 0.6:
            return True
        if evidence_quality in ("insufficient", "none"):
            return True
        return False

    def _get_effective_urgency(self, llm_urgency: str, case_urgency: str) -> str:
        urgency_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        llm_val = urgency_order.get(llm_urgency, 1)
        case_val = urgency_order.get(case_urgency, 1)
        return llm_urgency if llm_val >= case_val else case_urgency

    def _decide_automation(
        self,
        risk_level: RiskLevel,
        requires_hitl: bool,
        policy_violations: list[str],
    ) -> AutomationDecision:
        if policy_violations:
            if any("critical" in v or "escalat" in v for v in policy_violations):
                return AutomationDecision.ESCALATE
            return AutomationDecision.HUMAN_REVIEW

        if risk_level == RiskLevel.CRITICAL:
            return AutomationDecision.ESCALATE
        if risk_level == RiskLevel.HIGH:
            return AutomationDecision.HUMAN_REVIEW
        if requires_hitl:
            return AutomationDecision.HUMAN_REVIEW
        if risk_level == RiskLevel.MEDIUM:
            return AutomationDecision.HUMAN_REVIEW
        return AutomationDecision.AUTO_APPROVE

    def _build_justification(
        self,
        risk_level: RiskLevel,
        automation_decision: AutomationDecision,
        factors: list[str],
        policy_violations: list[str],
    ) -> str:
        parts = [f"Risk: {risk_level.value}", f"Decision: {automation_decision.value}"]
        if factors:
            parts.append(f"Factors: {', '.join(factors)}")
        if policy_violations:
            parts.append(f"Violations: {', '.join(policy_violations)}")
        return "; ".join(parts)

    def get_risk_factors(self) -> list[str]:
        return [
            "urgency_level",
            "validation_status",
            "evidence_quality",
            "confidence_score",
            "action_type",
        ]

    def get_automation_rules(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "auto_approve_conditions": {
                "risk_level": "LOW",
                "validation_status": "valid",
                "evidence_quality": "sufficient",
                "confidence_min": 0.7,
                "no_policy_violations": True,
            },
            "human_review_conditions": {
                "risk_level_in": ["MEDIUM", "HIGH"],
                "confidence_below": 0.6,
                "evidence_quality_in": ["insufficient", "none"],
            },
            "escalate_conditions": {
                "risk_level": "CRITICAL",
                "critical_urgency": True,
            },
        }
