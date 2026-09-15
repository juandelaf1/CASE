"""Domain policy for seismic risk assessment.

Handles earthquake risk classification based on magnitude, depth, and location.
Registered as domain "seismic_risk" in CASE DomainRegistry.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.domain import DomainPolicy


class SeismicEventType(str, Enum):
    MAJOR = "MAJOR"             # M >= 7.0
    STRONG = "STRONG"           # M >= 5.5
    MODERATE = "MODERATE"       # M >= 4.5
    MINOR = "MINOR"             # M < 4.5


class SeismicRiskLevel(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


MAGNITUDE_THRESHOLDS: dict[SeismicEventType, float] = {
    SeismicEventType.MAJOR: 7.0,
    SeismicEventType.STRONG: 5.5,
    SeismicEventType.MODERATE: 4.5,
    SeismicEventType.MINOR: 0.0,
}

RISK_LEVEL_MAP: dict[SeismicEventType, SeismicRiskLevel] = {
    SeismicEventType.MAJOR: SeismicRiskLevel.CRITICAL,
    SeismicEventType.STRONG: SeismicRiskLevel.HIGH,
    SeismicEventType.MODERATE: SeismicRiskLevel.MEDIUM,
    SeismicEventType.MINOR: SeismicRiskLevel.LOW,
}

RECOMMENDED_ACTIONS: dict[SeismicEventType, list[str]] = {
    SeismicEventType.MAJOR: [
        "activate_emergency_protocol",
        "notify_authorities",
        "deploy_assessment_team",
        "activate_early_warning_systems",
    ],
    SeismicEventType.STRONG: [
        "notify_emergency_services",
        "activate_monitoring",
        "issue_public_advisory",
    ],
    SeismicEventType.MODERATE: [
        "log_event",
        "monitor_aftershocks",
        "assess_infrastructure_impact",
    ],
    SeismicEventType.MINOR: [
        "log_event",
        "archive_data",
    ],
}


def classify_magnitude(magnitude: float) -> SeismicEventType:
    """Classify earthquake by magnitude."""
    if magnitude >= 7.0:
        return SeismicEventType.MAJOR
    if magnitude >= 5.5:
        return SeismicEventType.STRONG
    if magnitude >= 4.5:
        return SeismicEventType.MODERATE
    return SeismicEventType.MINOR


def classify_risk_level(magnitude: float) -> SeismicRiskLevel:
    """Determine risk level from magnitude."""
    event_type = classify_magnitude(magnitude)
    return RISK_LEVEL_MAP[event_type]


class SeismicRiskPolicy(DomainPolicy):
    """Domain policy for seismic risk (earthquakes, volcanic events)."""

    @property
    def domain_name(self) -> str:
        return "seismic_risk"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "No evidence provided for seismic case"

        has_metric = any(e.type.value == "metric" for e in evidence)
        has_text = any(e.type.value == "text" for e in evidence)

        if not has_metric and not has_text:
            return False, "Seismic cases require at least text or metric evidence"

        return True, "Evidence validated"

    def classify_urgency(self, case: OperationalCase) -> str:
        magnitude = case.metadata.get("magnitude", 0.0)
        if magnitude >= 7.0:
            return "CRITICAL"
        if magnitude >= 5.5:
            return "HIGH"
        if magnitude >= 4.5:
            return "MEDIUM"
        return "LOW"

    def classify_seismic_event_type(self, case: OperationalCase) -> SeismicEventType:
        magnitude = case.metadata.get("magnitude", 0.0)
        return classify_magnitude(magnitude)

    def get_risk_level(self, case: OperationalCase) -> SeismicRiskLevel:
        magnitude = case.metadata.get("magnitude", 0.0)
        return classify_risk_level(magnitude)

    def get_recommended_actions(self, case: OperationalCase) -> list[str]:
        event_type = self.classify_seismic_event_type(case)
        return RECOMMENDED_ACTIONS.get(event_type, ["investigate"])

    def get_domain_context(self) -> dict[str, Any]:
        return {
            "domain": "seismic_risk",
            "evidence_types": ["text", "metric"],
            "urgency_factors": ["magnitude", "depth", "tsunami", "felt_count"],
            "event_types": [et.value for et in SeismicEventType],
            "risk_levels": [rl.value for rl in SeismicRiskLevel],
            "magnitude_thresholds": {et.value: thr for et, thr in MAGNITUDE_THRESHOLDS.items()},
            "recommended_actions": {et.value: acts for et, acts in RECOMMENDED_ACTIONS.items()},
        }
