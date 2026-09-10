from typing import Any

from pydantic import BaseModel, Field


class AuditEvent(BaseModel):
    event_id: str
    case_id: str
    decision_id: str | None = None
    event_type: str
    timestamp: str
    details: dict[str, Any] = Field(default_factory=dict)
    actor: str = "system"
