from abc import ABC, abstractmethod
from typing import Any

from case_core.contracts.decision import TriageDecision


class DecisionRepositoryPort(ABC):
    """Port: interface for decision persistence.

    security_context is optional for backward compatibility with autonomous/dev flows.
    Implementations MUST enforce tenant/consumer isolation when a context is provided.
    """

    @abstractmethod
    async def save_decision(self, decision: TriageDecision, security_context: Any = None) -> None:
        ...

    @abstractmethod
    async def get_decision(self, decision_id: str, security_context: Any = None) -> TriageDecision | None:
        ...

    @abstractmethod
    async def get_decision_by_case(self, case_id: str, security_context: Any = None) -> TriageDecision | None:
        ...

    @abstractmethod
    async def list_pending_review(self, limit: int = 100, security_context: Any = None) -> list[TriageDecision]:
        ...

    @abstractmethod
    async def list_decisions(self, limit: int = 50, offset: int = 0, security_context: Any = None) -> list[TriageDecision]:
        ...

    @abstractmethod
    async def count_decisions(self, security_context: Any = None) -> int:
        ...

    @abstractmethod
    async def update_lifecycle(self, decision_id: str, lifecycle: str, actor: str = "human", justification: str = "", original_action: str = "", original_urgency: str = "", original_confidence: float = 0.0, original_evidence_summary: str = "", security_context: Any = None, expected_lifecycle: str | None = None) -> bool:
        ...
