"""Supply Chain Disruption domain pack - cross-supply-chain incident decisioning."""
from __future__ import annotations

from enum import Enum
from typing import Any

from case_core.contracts.automation import AutomationDecision, RiskAssessment, RiskLevel
from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.automation import AutomationPolicy
from case_core.ports.domain import DomainPolicy


class DisruptionType(str, Enum):
    SUPPLIER_FAILURE = "supplier_failure"
    PORT_DELAY = "port_delay"
    CUSTOMS_HOLD = "customs_hold"
    WEATHER_DISRUPTION = "weather_disruption"
    INVENTORY_SHORTAGE = "inventory_shortage"
    CARRIER_FAILURE = "carrier_failure"
    QUALITY_HOLD = "quality_hold"


class SupplyChainDisruptionPolicy(DomainPolicy):
    @property
    def domain_name(self) -> str:
        return "supply_chain_disruption"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "At least one evidence item required"
        types = {e.type.value for e in evidence}
        if types.intersection({"text", "metric", "image", "file"}):
            return True, "Evidence validated"
        return False, "Disruption cases require text, metric, image, or file evidence"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        critical = ["critical", "shutdown", "breach", "total loss", "port closed", "customs seizure"]
        high = ["delay", "blocked", "shortage", "failure", "hold", "disruption", "stuck"]
        medium = ["risk", "warning", "slow", "backlog", "degraded"]
        if any(w in text for w in critical):
            return "CRITICAL"
        if any(w in text for w in high):
            return "HIGH"
        if any(w in text for w in medium):
            return "MEDIUM"
        return "LOW"

    def get_domain_context(self) -> dict[str, Any]:
        return {
            "domain": self.domain_name,
            "evidence_types": ["text", "metric", "image", "file"],
            "disruption_types": [t.value for t in DisruptionType],
            "departments": ["procurement", "logistics", "compliance", "operations", "finance"],
            "recommended_actions": [
                "assess_impact",
                "activate_alternate_supplier",
                "reroute_shipment",
                "notify_stakeholders",
                "escalate_to_human",
            ],
        }

    def classify_disruption_type(self, case: OperationalCase) -> DisruptionType | None:
        text = case.report_text.lower()
        mapping = [
            (DisruptionType.SUPPLIER_FAILURE, ["supplier", "vendor", "factory", "manufactur"]),
            (DisruptionType.PORT_DELAY, ["port", "terminal", "dock", "container"]),
            (DisruptionType.CUSTOMS_HOLD, ["customs", "import", "export", "clearance", "tariff"]),
            (DisruptionType.WEATHER_DISRUPTION, ["storm", "weather", "flood", "hurricane", "snow"]),
            (DisruptionType.INVENTORY_SHORTAGE, ["stockout", "shortage", "inventory", "backorder"]),
            (DisruptionType.CARRIER_FAILURE, ["carrier", "truck", "freight", "shipment", "delivery"]),
            (DisruptionType.QUALITY_HOLD, ["quality", "defect", "recall", "inspection hold"]),
        ]
        for dtype, kws in mapping:
            if any(k in text for k in kws):
                return dtype
        return None


class SupplyChainDisruptionAutomation(AutomationPolicy):
    @property
    def domain_name(self) -> str:
        return "supply_chain_disruption"

    def assess_risk(self, case: OperationalCase, data: dict[str, Any], validation_status: str, evidence_quality: str, confidence: float) -> RiskAssessment:
        urgency = self._effective_urgency(case, data)
        factors: list[str] = [f"urgency:{urgency}"]
        violations: list[str] = []
        if validation_status != "valid":
            violations.append(f"validation:{validation_status}")
            factors.append("validation_issue")
        if evidence_quality in {"poor", "insufficient"}:
            factors.append("weak_evidence")
        if confidence < 0.75:
            factors.append("low_confidence")

        if urgency == "CRITICAL" or violations:
            level, decision, hitl = RiskLevel.CRITICAL, AutomationDecision.ESCALATE, True
        elif urgency == "HIGH" or confidence < 0.75 or evidence_quality in {"poor", "insufficient"}:
            level, decision, hitl = RiskLevel.HIGH, AutomationDecision.HUMAN_REVIEW, True
        elif urgency == "MEDIUM":
            level, decision, hitl = RiskLevel.MEDIUM, AutomationDecision.HUMAN_REVIEW, True
        else:
            level, decision, hitl = RiskLevel.LOW, AutomationDecision.AUTO_APPROVE, False

        return RiskAssessment(
            decision_id=f"ra-{case.case_id}",
            case_id=case.case_id,
            domain=self.domain_name,
            risk_level=level,
            automation_decision=decision,
            confidence=confidence,
            factors=factors,
            requires_hitl=hitl,
            policy_violations=violations,
            evidence_quality=evidence_quality,
            validation_status=validation_status,
            justification=f"urgency={urgency}; confidence={confidence:.2f}; evidence={evidence_quality}",
        )

    def get_risk_factors(self) -> list[str]:
        return ["urgency", "confidence", "evidence_quality", "validation_status", "disruption_type"]

    def get_automation_rules(self) -> dict[str, Any]:
        return {
            "CRITICAL": "ESCALATE",
            "HIGH": "HUMAN_REVIEW",
            "MEDIUM": "HUMAN_REVIEW",
            "LOW_confidence_or_weak_evidence": "HUMAN_REVIEW",
            "default": "AUTO_APPROVE",
        }

    @staticmethod
    def _effective_urgency(case: OperationalCase, data: dict[str, Any]) -> str:
        case_urg = case.urgency.value if hasattr(case.urgency, "value") else str(case.urgency)
        data_urg = str(data.get("urgency", case_urg)).upper()
        order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
        return case_urg if order.get(case_urg, 0) >= order.get(data_urg, 0) else data_urg
