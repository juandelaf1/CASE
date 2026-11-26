from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from case_api.api.v1.routers.shared import (
    MAX_EVIDENCE_CONTENT_LENGTH,
    MAX_EVIDENCE_ITEMS,
    MAX_JUSTIFICATION_LENGTH,
    MAX_REPORT_LENGTH,
    VALID_EVIDENCE_TYPES,
    VALID_URGENCY_LEVELS,
)


class EvidenceRequest(BaseModel):
    id: str
    type: str
    content: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence type: {v}. Valid types: {sorted(VALID_EVIDENCE_TYPES)}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evidence content cannot be empty")
        if len(v) > MAX_EVIDENCE_CONTENT_LENGTH:
            raise ValueError(f"Evidence content too long (max {MAX_EVIDENCE_CONTENT_LENGTH} characters)")
        return v.strip()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evidence source cannot be empty")
        return v.strip()


class TriageRequest(BaseModel):
    case_id: str | None = None
    report_text: str
    domain: str
    urgency: str = "MEDIUM"
    evidence: list[EvidenceRequest] = Field(default_factory=list)
    external_reference: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    provider: str | None = None

    @field_validator("report_text")
    @classmethod
    def validate_report_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Report text cannot be empty")
        if len(v) > MAX_REPORT_LENGTH:
            raise ValueError(f"Report text too long (max {MAX_REPORT_LENGTH} characters)")
        return v.strip()

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        if v not in VALID_URGENCY_LEVELS:
            raise ValueError(f"Invalid urgency: {v}. Valid levels: {sorted(VALID_URGENCY_LEVELS)}")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Domain cannot be empty")
        return v.strip()

    @field_validator("evidence")
    @classmethod
    def validate_evidence_count(cls, v: list[EvidenceRequest]) -> list[EvidenceRequest]:
        if len(v) > MAX_EVIDENCE_ITEMS:
            raise ValueError(f"Too many evidence items (max {MAX_EVIDENCE_ITEMS})")
        return v


class TriageDecisionResponse(BaseModel):
    decision_id: str
    case_id: str
    external_reference: str | None = None
    domain: str
    action: str
    reason: str
    urgency: str
    reported_urgency: str | None = None
    confidence: float
    evidence_summary: str
    decision_rationale: str = ""
    decision_factors: list[str] = []
    summary: str = ""
    lifecycle: str
    processing_time_ms: float
    original_ai_proposal: dict[str, Any] | None = None
    human_override: dict[str, Any] | None = None
    provider_info: dict[str, Any] | None = None
    react_trace: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: str
    category: str
    recoverable: bool
    retryable: bool
    requires_manual_review: bool = False


class HITLActionRequest(BaseModel):
    actor: str = "human"
    notes: str = ""
    justification: str = ""

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, v: str) -> str:
        if v and len(v) > MAX_JUSTIFICATION_LENGTH:
            raise ValueError(f"Justification too long (max {MAX_JUSTIFICATION_LENGTH} characters)")
        return v


class HITLModifyRequest(BaseModel):
    action: str
    reason: str
    urgency: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: str
    actor: str = "human"
    notes: str = ""
    justification: str = ""

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid = {"approve", "reject", "escalate"}
        if v not in valid:
            raise ValueError(f"Invalid action: {v}. Valid actions: {sorted(valid)}")
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        if v not in VALID_URGENCY_LEVELS:
            raise ValueError(f"Invalid urgency: {v}. Valid levels: {sorted(VALID_URGENCY_LEVELS)}")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, v: str) -> str:
        if v and len(v) > MAX_JUSTIFICATION_LENGTH:
            raise ValueError(f"Justification too long (max {MAX_JUSTIFICATION_LENGTH} characters)")
        return v


class HITLEscalateRequest(BaseModel):
    actor: str = "human"
    justification: str = ""
    escalate_to: str = "supervisor"


class ComparisonRequest(BaseModel):
    case_id: str | None = None
    report_text: str
    domain: str
    urgency: str = "MEDIUM"
    evidence: list[EvidenceRequest] = Field(default_factory=list)
    external_reference: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    providers: list[str] = Field(default_factory=list)

    @field_validator("report_text")
    @classmethod
    def validate_report_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Report text cannot be empty")
        return v.strip()
