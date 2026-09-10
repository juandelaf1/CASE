from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase
from case_core.ports.domain import DomainPolicy


class UrbanPolicy(DomainPolicy):
    """Domain policy for urban operations (streets, lighting, traffic)."""

    @property
    def domain_name(self) -> str:
        return "urban_operations"

    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        if not evidence:
            return False, "No evidence provided for urban operations case"
        text_evidence = [e for e in evidence if e.type.value == "text"]
        if not text_evidence:
            return False, "Urban operations requires at least one text evidence"
        return True, "Evidence validated"

    def classify_urgency(self, case: OperationalCase) -> str:
        text = case.report_text.lower()
        if any(w in text for w in ["emergency", "danger", "risk", "accident"]):
            return "HIGH"
        if any(w in text for w in ["broken", "damaged", "failure", "outage"]):
            return "MEDIUM"
        return "LOW"

    def get_domain_context(self) -> dict:
        return {
            "domain": "urban_operations",
            "evidence_types": ["text", "image", "metric"],
            "urgency_factors": ["emergency", "danger", "broken", "damaged"],
        }
