"""Automation policy for seismic risk assessment.

Determines risk level and automation decisions for seismic events.
High-magnitude events require human review; low-magnitude can be auto-approved.
"""
from __future__ import annotations

from typing import Any

from case_core.contracts.automation import AutomationDecision, RiskAssessment, RiskLevel
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.automation import AutomationPolicy


class SeismicAutomationPolicy(AutomationPolicy):
    """Automation policy for seismic risk domain."""

    @property
    def domain_name(self) -> str:
        return "seismic_risk"

    def assess_risk(
        self,
        case: OperationalCase,
        data: dict[str, Any],
        validation_status: str,
        evidence_quality: str,
        confidence: float,
    ) -> RiskAssessment:
        magnitude = case.metadata.get("magnitude", 0.0)
        depth_km = case.metadata.get("depth_km", 0.0)
        tsunami = case.metadata.get("tsunami", False)

        risk_level = self._compute_risk_level(magnitude, depth_km, tsunami)
        factors = self._compute_risk_factors(magnitude, depth_km, tsunami, confidence)
        policy_violations = self._compute_violations(risk_level, validation_status)

        requires_hitl = risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL) or confidence < 0.6
        automation_decision = self._decide_automation(risk_level, requires_hitl, policy_violations)

        justification = self._build_justification(risk_level, automation_decision, factors, policy_violations)

        return RiskAssessment(
            decision_id=f"ra-{case.case_id}",
            case_id=case.case_id,
            domain="seismic_risk",
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

    def get_risk_factors(self) -> list[str]:
        return [
            "magnitude_level",
            "depth_category",
            "tsunami_flag",
            "confidence_score",
        ]

    def get_automation_rules(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "auto_approve_conditions": {
                "risk_level_in": ["LOW", "MEDIUM"],
                "validation_status": "valid",
                "confidence_min": 0.7,
                "no_tsunami": True,
            },
            "human_review_conditions": {
                "risk_level_in": ["HIGH", "CRITICAL"],
                "confidence_below": 0.6,
                "tsunami_flag": True,
            },
            "escalate_conditions": {
                "risk_level": "CRITICAL",
                "magnitude_min": 7.0,
            },
        }

    def _compute_risk_level(
        self,
        magnitude: float,
        depth_km: float,
        tsunami: bool,
    ) -> RiskLevel:
        if magnitude >= 7.0:
            return RiskLevel.CRITICAL
        if magnitude >= 5.5:
            return RiskLevel.HIGH
        if tsunami and magnitude >= 4.5:
            return RiskLevel.HIGH
        if magnitude >= 4.5:
            return RiskLevel.MEDIUM
        return RiskLevel.LOW

    def _compute_risk_factors(
        self,
        magnitude: float,
        depth_km: float,
        tsunami: bool,
        confidence: float,
    ) -> list[str]:
        factors: list[str] = []
        if magnitude >= 7.0:
            factors.append("major_magnitude")
        elif magnitude >= 5.5:
            factors.append("strong_magnitude")
        elif magnitude >= 4.5:
            factors.append("moderate_magnitude")

        if depth_km < 70:
            factors.append("shallow_depth")
        elif depth_km < 300:
            factors.append("intermediate_depth")
        else:
            factors.append("deep_depth")

        if tsunami:
            factors.append("tsunami_flag")

        if confidence < 0.5:
            factors.append("confidence_low")

        return factors

    def _compute_violations(
        self,
        risk_level: RiskLevel,
        validation_status: str,
    ) -> list[str]:
        violations: list[str] = []
        if validation_status != "valid":
            violations.append("validation_failure")
        if risk_level == RiskLevel.CRITICAL:
            violations.append("critical_risk_requires_escalation")
        return violations

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
