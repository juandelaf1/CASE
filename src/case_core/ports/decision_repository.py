from abc import ABC, abstractmethod

from case_core.contracts.decision import TriageDecision


class DecisionRepositoryPort(ABC):
    """Port: interface for decision persistence."""

    @abstractmethod
    async def save_decision(self, decision: TriageDecision) -> None:
        ...

    @abstractmethod
    async def get_decision(self, decision_id: str) -> TriageDecision | None:
        ...

    @abstractmethod
    async def get_decision_by_case(self, case_id: str) -> TriageDecision | None:
        ...

    @abstractmethod
    async def list_pending_review(self, limit: int = 100) -> list[TriageDecision]:
        ...

    @abstractmethod
    async def update_lifecycle(self, decision_id: str, lifecycle: str, actor: str = "human", justification: str = "", original_action: str = "", original_urgency: str = "", original_confidence: float = 0.0, original_evidence_summary: str = "") -> None:
        ...
