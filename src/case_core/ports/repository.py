from abc import ABC, abstractmethod
from typing import Any

from case_core.contracts.operational_case import OperationalCase


class RepositoryPort(ABC):
    """Port: interface for case persistence.

    security_context is optional for backward compatibility. Implementations MUST
    enforce tenant/consumer isolation when a context is provided.
    """

    @abstractmethod
    async def save_case(self, case: OperationalCase, security_context: Any = None) -> None:
        ...

    @abstractmethod
    async def get_case(self, case_id: str, security_context: Any = None) -> OperationalCase | None:
        ...

    @abstractmethod
    async def list_cases(self, limit: int = 100, offset: int = 0, security_context: Any = None) -> list[OperationalCase]:
        ...
