from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from case_core.contracts.evidence import EvidenceItem
from case_core.contracts.lifecycle import ProcessingLifecycle


class UrgencyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OperationalCase(BaseModel):
    case_id: str
    report_text: str
    domain: str
    urgency: UrgencyLevel = UrgencyLevel.MEDIUM
    evidence: list[EvidenceItem] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    received_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: ProcessingLifecycle = ProcessingLifecycle.RECEIVED
    decision: Any = None  # TriageDecision forward reference
    audit_events: list[Any] = Field(default_factory=list)  # AuditEvent forward reference

    model_config = {"arbitrary_types_allowed": True}


OperationalCase.model_rebuild()
