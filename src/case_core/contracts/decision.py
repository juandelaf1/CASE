from typing import Any

from pydantic import BaseModel

from case_core.contracts.error import CASEError
from case_core.contracts.lifecycle import DecisionLifecycle


class AIProposal(BaseModel):
    action: str
    reason: str
    urgency: str
    confidence: float
    evidence_summary: str


class HumanOverride(BaseModel):
    actor: str
    timestamp: str
    justification: str
    original_action: str
    original_urgency: str
    original_confidence: float
    original_evidence_summary: str


class TriageDecision(BaseModel):
    decision_id: str
    case_id: str
    domain: str
    action: str
    reason: str
    urgency: str
    confidence: float
    evidence_summary: str
    lifecycle: DecisionLifecycle = DecisionLifecycle.AI_PROPOSED
    processing_time_ms: float = 0.0
    error: CASEError | None = None
    metadata: dict[str, Any] = {}
    original_ai_proposal: AIProposal | None = None
    human_override: HumanOverride | None = None

    def model_dump_ext(self) -> dict:
        return {
            "decision_id": self.decision_id,
            "case_id": self.case_id,
            "domain": self.domain,
            "action": self.action,
            "reason": self.reason,
            "urgency": self.urgency,
            "confidence": self.confidence,
            "evidence_summary": self.evidence_summary,
            "lifecycle": self.lifecycle.value,
            "processing_time_ms": self.processing_time_ms,
            "error": self.error.model_dump() if self.error else None,
            "metadata": self.metadata,
            "original_ai_proposal": self.original_ai_proposal.model_dump() if self.original_ai_proposal else None,
            "human_override": self.human_override.model_dump() if self.human_override else None,
        }

    @classmethod
    def model_validate_ext(cls, data: dict) -> "TriageDecision":
        original_ai = None
        if data.get("original_ai_proposal"):
            original_ai = AIProposal(**data["original_ai_proposal"])
        human_override = None
        if data.get("human_override"):
            human_override = HumanOverride(**data["human_override"])
        return cls(
            decision_id=data["decision_id"],
            case_id=data["case_id"],
            domain=data["domain"],
            action=data["action"],
            reason=data["reason"],
            urgency=data["urgency"],
            confidence=data["confidence"],
            evidence_summary=data["evidence_summary"],
            lifecycle=DecisionLifecycle(data["lifecycle"]),
            processing_time_ms=data.get("processing_time_ms", 0.0),
            error=CASEError.model_validate(data["error"]) if data.get("error") else None,
            metadata=data.get("metadata", {}),
            original_ai_proposal=original_ai,
            human_override=human_override,
        )
