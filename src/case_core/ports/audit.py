from abc import ABC, abstractmethod

from case_core.contracts.audit import AuditEvent


class AuditPort(ABC):
    """Port: interface for audit logging persistence."""

    @abstractmethod
    async def log_event(self, event: AuditEvent) -> None:
        ...

    @abstractmethod
    async def get_events_by_case(self, case_id: str) -> list[AuditEvent]:
        ...
