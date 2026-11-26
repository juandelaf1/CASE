"""Customer Support domain pack - reference non-logistics vertical."""
from __future__ import annotations

from enum import Enum
from typing import Any

from case_core.contracts.automation import AutomationDecision, RiskAssessment, RiskLevel
from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.automation import AutomationPolicy
from case_core.ports.domain import DomainPolicy


class SupportIncidentType(str, Enum):
    BILLING = "billing"
    OUTAGE = "outage"
    ACCESS = "access"
    BUG = "bug"
    REQUEST = "request"


class CustomerSupportPolicy(DomainPolicy):
    @property
    def domain_name(self) -> str:
        return "customer_support"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "At least one evidence item required"
        if any(e.type.value in {"text", "metric", "image"} for e in evidence):
            return True, "Evidence validated"
        return False, "Support cases require text, metric, or image evidence"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if any(w in text for w in ["outage", "security", "breach", "cannot access", "down"]):
            return "CRITICAL"
        if any(w in text for w in ["urgent", "blocked", "failed payment", "error"]):
            return "HIGH"
        if any(w in text for w in ["slow", "issue", "bug"]):
            return "MEDIUM"
        return "LOW"

    def get_domain_context(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "evidence_types": ["text", "metric", "image"],
            "incident_types": [t.value for t in SupportIncidentType],
            "departments": ["support", "billing", "engineering", "security"],
        }

    def classify_incident_type(self, case: OperationalCase) -> SupportIncidentType:
        text = case.report_text.lower()
        if any(w in text for w in ["invoice", "billing", "charge", "refund"]):
            return SupportIncidentType.BILLING
        if any(w in text for w in ["outage", "down", "unavailable"]):
            return SupportIncidentType.OUTAGE
        if any(w in text for w in ["login", "access", "password", "locked"]):
            return SupportIncidentType.ACCESS
        if any(w in text for w in ["bug", "error", "crash"]):
            return SupportIncidentType.BUG
        return SupportIncidentType.REQUEST


class CustomerSupportAutomation(AutomationPolicy):
    @property
    def domain_name(self) -> str:
        return "customer_support"

    def assess_risk(self, case: OperationalCase, data: dict[str, Any], validation_status: str, evidence_quality: str, confidence: float) -> RiskAssessment:
        urgency = self._effective_urgency(case, data)
        factors: list[str] = []
        violations: list[str] = []

        if urgency in {"CRITICAL", "HIGH"}:
            factors.append(f"urgency:{urgency}")
        if confidence < 0.7:
            factors.append("low_confidence")
        if evidence_quality in {"poor", "insufficient"}:
            factors.append("weak_evidence")
        if validation_status != "valid":
            violations.append(f"validation:{validation_status}")

        if violations or urgency == "CRITICAL":
            level = RiskLevel.CRITICAL if urgency == "CRITICAL" else RiskLevel.HIGH
            decision = AutomationDecision.ESCALATE if urgency == "CRITICAL" else AutomationDecision.HUMAN_REVIEW
            hitl = True
        elif urgency == "HIGH" or confidence < 0.7:
            level = RiskLevel.HIGH
            decision = AutomationDecision.HUMAN_REVIEW
            hitl = True
        else:
            level = RiskLevel.LOW
            decision = AutomationDecision.AUTO_APPROVE
            hitl = False

        return RiskAssessment(
            decision_id=f"ra-{case.case_id}",
            case_id=case.case_id,
            domain=self.domain_name,
            risk_level=level,
            automation_decision=decision,
            confidence=confidence,
            factors=factors or ["standard_support_case"],
            requires_hitl=hitl,
            policy_violations=violations,
            evidence_quality=evidence_quality,
            validation_status=validation_status,
            justification=f"urgency={urgency}; confidence={confidence:.2f}; evidence={evidence_quality}",
        )

    def get_risk_factors(self) -> list[str]:
        return ["urgency", "confidence", "evidence_quality", "validation_status"]

    def get_automation_rules(self) -> dict[str, Any]:
        return {
            "CRITICAL": "ESCALATE",
            "HIGH": "HUMAN_REVIEW",
            "LOW_confidence": "HUMAN_REVIEW",
            "default": "AUTO_APPROVE",
        }

    @staticmethod
    def _effective_urgency(case: OperationalCase, data: dict[str, Any]) -> str:
        case_urg = case.urgency.value if hasattr(case.urgency, "value") else str(case.urgency)
        data_urg = str(data.get("urgency", case_urg)).upper()
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return case_urg if order.get(case_urg, 0) >= order.get(data_urg, 0) else data_urg
