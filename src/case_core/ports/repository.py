from abc import ABC, abstractmethod

from case_core.contracts.operational_case import OperationalCase


class RepositoryPort(ABC):
    """Port: interface for case persistence."""

    @abstractmethod
    async def save_case(self, case: OperationalCase) -> None:
        ...

    @abstractmethod
    async def get_case(self, case_id: str) -> OperationalCase | None:
        ...

    @abstractmethod
    async def list_cases(self, limit: int = 100, offset: int = 0) -> list[OperationalCase]:
        ...
