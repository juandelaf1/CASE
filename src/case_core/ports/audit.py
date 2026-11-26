from abc import ABC, abstractmethod
from typing import Any

from case_core.contracts.audit import AuditEvent


class AuditPort(ABC):
    """Port: interface for audit logging persistence.

    security_context is optional for backward compatibility. Implementations MUST
    enforce tenant/consumer isolation and stamp verified identity when provided.
    """

    @abstractmethod
    async def log_event(self, event: AuditEvent, security_context: Any = None) -> None:
        ...

    @abstractmethod
    async def get_events_by_case(self, case_id: str, security_context: Any = None) -> list[AuditEvent]:
        ...
