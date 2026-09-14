"""Real Estate domain policy — Phase 6."""

from __future__ import annotations

from enum import Enum
from typing import Any

from case_core.contracts.automation import AutomationDecision, RiskAssessment, RiskLevel
from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.automation import AutomationPolicy
from case_core.ports.domain import DomainPolicy


class PropertyType(str, Enum):
    """Types of real estate properties."""

    RESIDENTIAL = "residential"
    COMMERCIAL = "commercial"
    INDUSTRIAL = "industrial"
    LAND = "land"
    MIXED_USE = "mixed_use"


class TransactionType(str, Enum):
    """Types of real estate transactions."""

    SALE = "sale"
    LEASE = "lease"
    RENTAL = "rental"
    AUCTION = "auction"
    TRANSFER = "transfer"


class RealEstateIncidentType(str, Enum):
    """Types of real estate incidents."""

    VALUATION = "valuation"
    INSPECTION = "inspection"
    LISTING = "listing"
    NEGOTIATION = "negotiation"
    CLOSING = "closing"
    DISPUTE = "dispute"
    MAINTENANCE = "maintenance"
    COMPLIANCE = "compliance"


class RealEstateUrgency(str, Enum):
    """Urgency levels for real estate cases."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class RealEstatePolicy(DomainPolicy):
    """Domain policy for Real Estate operations."""

    @property
    def domain_name(self) -> str:
        return "real_estate"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "No evidence provided for real estate case"
        has_text = any(e.type.value == "text" for e in evidence)
        has_metric = any(e.type.value == "metric" for e in evidence)
        has_document = any(e.type.value == "document" for e in evidence)
        if has_text or has_metric or has_document:
            return True, "Evidence validated"
        return False, "Insufficient evidence types for real estate case"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if any(kw in text for kw in ["emergency", "urgent", "critical", "immediate"]):
            return RealEstateUrgency.CRITICAL.value
        if any(kw in text for kw in ["important", "deadline", "time-sensitive"]):
            return RealEstateUrgency.HIGH.value
        if any(kw in text for kw in ["standard", "normal", "routine"]):
            return RealEstateUrgency.MEDIUM.value
        return RealEstateUrgency.LOW.value

    def get_domain_context(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "property_types": [pt.value for pt in PropertyType],
            "transaction_types": [tt.value for tt in TransactionType],
            "incident_types": [it.value for it in RealEstateIncidentType],
            "evidence_requirements": ["text", "metric", "document"],
            "departments": ["valuation", "legal", "sales", "maintenance", "compliance"],
        }

    def classify_incident_type(self, case: OperationalCase) -> RealEstateIncidentType | None:
        text = case.report_text.lower()
        if any(kw in text for kw in ["valuation", "appraisal", "worth", "value"]):
            return RealEstateIncidentType.VALUATION
        if any(kw in text for kw in ["inspection", "survey", "assessment"]):
            return RealEstateIncidentType.INSPECTION
        if any(kw in text for kw in ["listing", "advertise", "market"]):
            return RealEstateIncidentType.LISTING
        if any(kw in text for kw in ["negotiate", "offer", "bid"]):
            return RealEstateIncidentType.NEGOTIATION
        if any(kw in text for kw in ["closing", "settlement", "final"]):
            return RealEstateIncidentType.CLOSING
        if any(kw in text for kw in ["dispute", "conflict", "issue"]):
            return RealEstateIncidentType.DISPUTE
        if any(kw in text for kw in ["maintenance", "repair", "fix"]):
            return RealEstateIncidentType.MAINTENANCE
        if any(kw in text for kw in ["compliance", "regulation", "permit"]):
            return RealEstateIncidentType.COMPLIANCE
        return None

    def get_recommended_actions(self, incident_type: RealEstateIncidentType) -> list[str]:
        actions = {
            RealEstateIncidentType.VALUATION: [
                "Request property details",
                "Compare with market data",
                "Schedule professional appraisal",
            ],
            RealEstateIncidentType.INSPECTION: [
                "Schedule inspection",
                "Review property history",
                "Identify potential issues",
            ],
            RealEstateIncidentType.LISTING: [
                "Prepare listing materials",
                "Set competitive pricing",
                "Schedule photography",
            ],
            RealEstateIncidentType.NEGOTIATION: [
                "Review comparable sales",
                "Prepare counter-offer",
                "Document terms",
            ],
            RealEstateIncidentType.CLOSING: [
                "Verify documentation",
                "Schedule final walkthrough",
                "Coordinate with title company",
            ],
            RealEstateIncidentType.DISPUTE: [
                "Document the dispute",
                "Review contract terms",
                "Escalate to legal",
            ],
            RealEstateIncidentType.MAINTENANCE: [
                "Assess maintenance needs",
                "Get contractor quotes",
                "Schedule repairs",
            ],
            RealEstateIncidentType.COMPLIANCE: [
                "Review regulations",
                "Check permits",
                "Document compliance status",
            ],
        }
        return actions.get(incident_type, ["General review required"])


class RealEstateAutomationPolicy(AutomationPolicy):
    """Automation policy for Real Estate domain."""

    @property
    def domain_name(self) -> str:
        return "real_estate"

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
        if urgency == "CRITICAL":
            risk_level = RiskLevel.CRITICAL
            factors.append("urgency_critical")
            policy_violations.append("critical_urgency_requires_escalation")
        elif urgency == "HIGH":
            risk_level = RiskLevel.HIGH
            factors.append("urgency_high")
        if validation_status != "valid":
            risk_level = RiskLevel.HIGH
            factors.append("validation_failed")
            policy_violations.append("validation_failure")
        if evidence_quality == "insufficient":
            if risk_level.value in ("LOW", "MEDIUM"):
                risk_level = RiskLevel.MEDIUM
            factors.append("evidence_insufficient")
        if confidence < 0.5:
            if risk_level.value in ("LOW", "MEDIUM"):
                risk_level = RiskLevel.MEDIUM
            factors.append("confidence_low")
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
            "policy_violations",
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
                "evidence_quality": "insufficient",
            },
            "escalate_conditions": {
                "risk_level": "CRITICAL",
                "critical_urgency": True,
            },
        }
