from abc import ABC, abstractmethod
from typing import Any

from case_core.contracts.automation import RiskAssessment
from case_core.contracts.operational_case import OperationalCase


class AutomationPolicy(ABC):
    """Port: interface for domain-specific automation risk assessment."""

    @property
    @abstractmethod
    def domain_name(self) -> str:
        ...

    @abstractmethod
    def assess_risk(
        self,
        case: OperationalCase,
        data: dict[str, Any],
        validation_status: str,
        evidence_quality: str,
        confidence: float,
    ) -> RiskAssessment:
        ...

    @abstractmethod
    def get_risk_factors(self) -> list[str]:
        ...

    @abstractmethod
    def get_automation_rules(self) -> dict[str, Any]:
        ...
