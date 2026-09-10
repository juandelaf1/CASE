from abc import ABC, abstractmethod
from typing import Any

from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.operational_case import OperationalCase


class DomainPolicy(ABC):
    """Port: interface for domain-specific validation and rules."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        ...

    @abstractmethod
    def validate_evidence(self, evidence: list[EvidenceItem]) -> tuple[bool, str]:
        ...

    @abstractmethod
    def classify_urgency(self, case: OperationalCase) -> str:
        ...

    @abstractmethod
    def get_domain_context(self) -> dict[str, Any]:
        ...
