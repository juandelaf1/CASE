from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.domain import DomainPolicy


class InfrastructurePolicy(DomainPolicy):
    """Domain policy for infrastructure (bridges, roads, utilities)."""

    @property
    def domain_name(self) -> str:
        return "infrastructure"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "No evidence provided for infrastructure case"
        return True, "Evidence validated"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if any(w in text for w in ["collapse", "structural", "failure", "emergency"]):
            return "CRITICAL"
        if any(w in text for w in ["damage", "crack", "deterioration"]):
            return "HIGH"
        return "MEDIUM"

    def get_domain_context(self) -> dict:
        return {
            "domain": "infrastructure",
            "evidence_types": ["text", "image", "metric", "file"],
            "urgency_factors": ["collapse", "structural", "failure", "damage"],
        }
