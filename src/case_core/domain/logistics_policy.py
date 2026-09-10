from enum import Enum
from typing import Any

from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.domain import DomainPolicy


class IncidentType(str, Enum):
    DELIVERY_DELAY = "DELIVERY_DELAY"
    DELIVERY_FAILURE = "DELIVERY_FAILURE"
    WAREHOUSE_DELAY = "WAREHOUSE_DELAY"
    TRANSPORT_DISRUPTION = "TRANSPORT_DISRUPTION"
    DAMAGED_GOODS = "DAMAGED_GOODS"
    STOCK_ISSUE = "STOCK_ISSUE"


class Department(str, Enum):
    FLEET = "FLEET"
    WAREHOUSE = "WAREHOUSE"
    ROUTING = "ROUTING"
    QUALITY = "QUALITY"
    PROCUREMENT = "PROCUREMENT"


RECOMMENDED_ACTIONS: dict[IncidentType, list[str]] = {
    IncidentType.DELIVERY_DELAY: ["check_route_status", "contact_driver", "update_customer"],
    IncidentType.DELIVERY_FAILURE: ["initiate_reshipment", "investigate_root_cause", "notify_customer"],
    IncidentType.WAREHOUSE_DELAY: ["check_inventory", "reallocate_stock", "expedite_processing"],
    IncidentType.TRANSPORT_DISRUPTION: ["reroute_shipment", "check_alternative_carriers", "notify_stakeholders"],
    IncidentType.DAMAGED_GOODS: ["inspect_damage", "file_claim", "initiate_replacement"],
    IncidentType.STOCK_ISSUE: ["check_supply_chain", "place_backorder", "alert_procurement"],
}


class LogisticsPolicy(DomainPolicy):
    """Domain policy for logistics (routing, delivery, fleet, warehouse)."""

    @property
    def domain_name(self) -> str:
        return "logistics"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "No evidence provided for logistics case"
        has_text = any(e.type.value == "text" for e in evidence)
        has_metric = any(e.type.value == "metric" for e in evidence)
        if not has_text and not has_metric:
            return False, "Logistics cases require at least text or metric evidence"
        return True, "Evidence validated"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if any(w in text for w in ["critical", "emergency", "immediate"]):
            return "CRITICAL"
        if any(w in text for w in ["delayed", "stuck", "urgent", "failure"]):
            return "HIGH"
        if any(w in text for w in ["route", "delivery", "shipment", "warehouse", "damage"]):
            return "MEDIUM"
        return "LOW"

    def classify_incident_type(self, case: OperationalCase) -> IncidentType | None:
        text = case.report_text.lower()
        if any(w in text for w in ["warehouse", "inventory", "stock"]):
            if any(w in text for w in ["delay", "backlog"]):
                return IncidentType.WAREHOUSE_DELAY
            return IncidentType.STOCK_ISSUE
        if any(w in text for w in ["delay", "late", "overdue"]):
            return IncidentType.DELIVERY_DELAY
        if any(w in text for w in ["failure", "lost", "missing"]):
            return IncidentType.DELIVERY_FAILURE
        if any(w in text for w in ["disruption", "reroute", "carrier"]):
            return IncidentType.TRANSPORT_DISRUPTION
        if any(w in text for w in ["damage", "broken", "destroyed"]):
            return IncidentType.DAMAGED_GOODS
        return None

    def get_recommended_actions(self, case: OperationalCase) -> list[str]:
        incident = self.classify_incident_type(case)
        if incident and incident in RECOMMENDED_ACTIONS:
            return RECOMMENDED_ACTIONS[incident]
        return ["investigate", "escalate_if_needed"]

    def get_domain_context(self) -> dict[str, Any]:
        return {
            "domain": "logistics",
            "evidence_types": ["text", "metric", "file"],
            "urgency_factors": ["delayed", "stuck", "urgent", "critical", "failure", "damage"],
            "incident_types": [it.value for it in IncidentType],
            "departments": [d.value for d in Department],
            "recommended_actions": {it.value: acts for it, acts in RECOMMENDED_ACTIONS.items()},
        }
