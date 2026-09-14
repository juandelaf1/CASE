"""Logistics risk, automation, HITL, and audit integration — Phase 2.7."""

from __future__ import annotations

import datetime
from typing import Any

from case_core.domain.logistics_classification import ShipmentClassification
from case_core.domain.logistics_contracts import (
    CargoType,
    ShipmentProfile,
    SpecialHandling,
)


class LogisticsRiskManager:
    """Manages risk assessment, HITL routing, and audit trails for logistics cases."""

    def __init__(self) -> None:
        self.classifier = ShipmentClassification()
        self.audit_log: list[dict[str, Any]] = []

    def register_case(self, shipment_id: str, profile: ShipmentProfile) -> str:
        """Register a shipment case for processing."""
        case_id = f"case_{shipment_id}_logistics"
        entry = {
            "case_id": case_id,
            "shipment_id": shipment_id,
            "profile": profile.model_dump(),
            "registered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "PENDING",
        }
        self.audit_log.append(entry)
        return case_id

    def assess_risk(self, profile: ShipmentProfile) -> dict[str, Any]:
        """Perform comprehensive risk assessment for a shipment."""
        classification = self.classifier.classify(profile)
        risk_level = str(classification["risk_level"])
        factors = self._extract_risk_factors(profile)
        justification = self._build_risk_justification(risk_level, factors)
        return {
            "risk_level": risk_level,
            "factors": factors,
            "justification": justification,
            "risk_score": classification["complexity_score"],
            "classification": classification,
        }

    def decide_automation(self, profile: ShipmentProfile) -> str:
        """Make an automated decision based on risk and policy."""
        risk_assessment = self.assess_risk(profile)
        risk_level = risk_assessment["risk_level"]
        requires_hitl = self._requires_hitl(profile, risk_level)

        if risk_level == "HIGH" or requires_hitl:
            decision = "HUMAN_REVIEW"
        elif risk_level == "MEDIUM":
            decision = "HUMAN_REVIEW"
        else:
            decision = "AUTO_APPROVE"

        # Record decision in audit log
        self.audit_log.append({
            "action": "automation_decision",
            "case_id": profile.shipment_id,
            "decision": decision,
            "risk_level": risk_level,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        })

        return decision

    def _requires_hitl(self, profile: ShipmentProfile, risk_level: str) -> bool:
        """Determine if human-in-the-loop is required."""
        if risk_level == "HIGH":
            return True
        if profile.cargo_type in (CargoType.HAZARDOUS, CargoType.PERISHABLE):
            return True
        if profile.special_handling != SpecialHandling.NONE:
            return True
        if profile.priority in ("CRITICAL", "RUSH"):
            return True
        if profile.declared_value_usd is not None and profile.declared_value_usd > 100000:
            return True
        if "cross_border" in profile.constraints:
            return True
        return False

    def _extract_risk_factors(self, profile: ShipmentProfile) -> list[str]:
        """Extract risk factors from the shipment profile."""
        factors = []
        if profile.cargo_type == CargoType.HAZARDOUS:
            factors.append("hazardous_cargo")
        if profile.cargo_type == CargoType.PERISHABLE:
            factors.append("perishable_cargo")
        if profile.special_handling != SpecialHandling.NONE:
            factors.append(f"special_handling:{profile.special_handling.value}")
        if profile.priority in ("CRITICAL", "RUSH"):
            factors.append("high_priority")
        if profile.sla_hours is not None and profile.sla_hours < 12:
            factors.append("tight_sla")
        if profile.weight_kg > 5000:
            factors.append("heavy_weight")
        if "weather_exposed" in profile.constraints:
            factors.append("weather_exposed")
        if "cross_border" in profile.constraints:
            factors.append("cross_border")
        if profile.declared_value_usd is not None and profile.declared_value_usd > 100000:
            factors.append("high_declared_value")
        return factors

    def _build_risk_justification(self, risk_level: str, factors: list[str]) -> str:
        """Build a human-readable justification for the risk level."""
        parts = [f"Risk: {risk_level}"]
        if factors:
            parts.append(f"Factors: {', '.join(factors)}")
        return "; ".join(parts)

    def submit_for_hitl(self, profile: ShipmentProfile) -> dict[str, Any]:
        """Submit a case to human review if required."""
        decision = self.decide_automation(profile)
        if decision == "AUTO_APPROVE":
            return {
                "status": "APPROVED",
                "decision": "AUTO_APPROVE",
                "confidence": 0.9,
            }
        else:
            return {
                "status": "HITL_REQUIRED",
                "decision": decision,
                "reason": "High risk or special handling requires human review",
            }

    def record_audit_entry(self, action: str, details: dict[str, Any]) -> None:
        """Record an audit entry for compliance."""
        entry = {
            "action": action,
            "case_id": details.get("case_id", "unknown"),
            "details": details,
            "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        }
        self.audit_log.append(entry)

    def get_audit_history(self, case_id: str) -> list[dict[str, Any]]:
        """Retrieve audit history for a specific case."""
        return [e for e in self.audit_log if e.get("case_id") == case_id]

    def close_case(self, case_id: str) -> None:
        """Close a case after completion."""
        for entry in self.audit_log:
            if entry.get("case_id") == case_id:
                entry["status"] = "CLOSED"
                break

    def generate_report(self, case_id: str) -> dict[str, Any]:
        """Generate a comprehensive report for a case."""
        case_entry = next((e for e in self.audit_log if e.get("case_id") == case_id), None)
        if not case_entry:
            return {"error": "Case not found"}

        report = {
            "case_id": case_id,
            "registration_time": case_entry.get("registered_at"),
            "current_status": case_entry.get("status", "UNKNOWN"),
            "risk_assessment": self.assess_risk(case_entry.get("profile", {})),
            "automation_decision": self.decide_automation(case_entry.get("profile", {})),
            "hitl_requirement": case_entry.get("requires_hitl", False),
            "audit_log": self.get_audit_history(case_id),
        }
        return report

    def assess_automation(self, profile: ShipmentProfile) -> dict[str, Any] | None:
        """Evaluate automation readiness for a shipment."""
        risk = self.assess_risk(profile)
        decision = self.decide_automation(profile)
        return {
            "risk_level": risk["risk_level"],
            "automation_decision": decision,
            "needs_hitl": decision == "HUMAN_REVIEW",
            "risk_score": risk["risk_score"],
        }

    def build_explanation(self, profile: ShipmentProfile, decision: str) -> str:
        """Build a human-readable explanation for the decision."""
        reasons = []
        if decision == "AUTO_APPROVE":
            reasons.append("Low risk and sufficient carrier/route compatibility")
        elif decision == "HUMAN_REVIEW":
            reasons.append("High risk or special handling requiring human review")
        else:
            reasons.append("Medium risk with acceptable mitigation strategies")

        return " ".join(reasons)
