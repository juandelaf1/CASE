"""Logistics domain policy implementation."""
from __future__ import annotations

from typing import Any

from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.domain import DomainPolicy


class LogisticsPolicy(DomainPolicy):
    """Domain policy for logistics operations."""

    @property
    def domain_name(self) -> str:
        return "logistics"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "No evidence provided for logistics case"
        return True, "Evidence validated"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if any(w in text for w in ["emergency", "critical", "urgent", "immediate"]):
            return "CRITICAL"
        if any(w in text for w in ["delayed", "late", "failure", "broken"]):
            return "HIGH"
        if any(w in text for w in ["issue", "problem", "concern"]):
            return "MEDIUM"
        return "LOW"

    def get_domain_context(self) -> dict[str, Any]:
        return {
            "domain": "logistics",
            "evidence_types": ["text", "metric", "file"],
            "urgency_factors": ["delivery_status", " shipment_condition", "carrier_performance"],
        }
