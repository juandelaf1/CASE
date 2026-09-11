import time

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from case_core.application.engine import TriageEngine
from case_core.contracts.audit import AuditEvent
from case_core.contracts.decision import HumanOverride
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.lifecycle import DecisionLifecycle
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.domain.infrastructure_policy import InfrastructurePolicy
from case_core.domain.logistics_policy import LogisticsPolicy
from case_core.domain.registry import DomainRegistry
from case_core.domain.urban_policy import UrbanPolicy
from case_core.providers.mock import MockProvider
from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository

app = FastAPI(
    title="CASE — AI Decision Platform",
    version="0.1.0",
    description="Domain-agnostic AI Decision Platform for operational case triage",
)

registry = DomainRegistry()
registry.register(UrbanPolicy())
registry.register(LogisticsPolicy())
registry.register(InfrastructurePolicy())

provider = MockProvider()
audit_adapter = SQLiteAuditAdapter()
decision_repo = SQLiteDecisionRepository()

engine = TriageEngine(
    domain_registry=registry,
    provider=provider,
    audit_port=audit_adapter,
    decision_repository=decision_repo,
)


class EvidenceRequest(BaseModel):
    id: str
    type: str
    content: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: str


class TriageRequest(BaseModel):
    case_id: str
    report_text: str
    domain: str
    urgency: str = "MEDIUM"
    evidence: list[EvidenceRequest] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class TriageDecisionResponse(BaseModel):
    decision_id: str
    case_id: str
    domain: str
    action: str
    reason: str
    urgency: str
    confidence: float
    evidence_summary: str
    lifecycle: str
    processing_time_ms: float
    original_ai_proposal: dict | None = None
    human_override: dict | None = None


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


class HITLModifyRequest(BaseModel):
    action: str
    reason: str
    urgency: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: str
    actor: str = "human"
    notes: str = ""
    justification: str = ""


class HITLEscalateRequest(BaseModel):
    actor: str = "human"
    justification: str = ""
    escalate_to: str = "supervisor"


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": "0.1.0"}


@app.get("/domains")
async def list_domains() -> dict[str, list[str]]:
    return {"domains": registry.list_domains()}


@app.post("/api/v1/triage")
async def triage(request: TriageRequest) -> TriageDecisionResponse:
    if not registry.validate_domain(request.domain):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain: {request.domain}. Valid domains: {registry.list_domains()}",
        )

    evidence = [
        EvidenceItem(
            id=e.id,
            type=EvidenceType(e.type),
            content=e.content,
            source=e.source,
            confidence=e.confidence,
            extracted_at=e.extracted_at,
        )
        for e in request.evidence
    ]

    case = OperationalCase(
        case_id=request.case_id,
        report_text=request.report_text,
        domain=request.domain,
        urgency=UrgencyLevel(request.urgency),
        evidence=evidence,
        metadata=request.metadata,
    )

    result = await engine.execute(case)

    if result.error is not None:
        err = result.error
        requires_manual_review = err.details.get("requires_manual_review", False) if err.details else False
        raise HTTPException(
            status_code=422,
            detail={
                "error": err.message,
                "category": err.category.value,
                "recoverable": err.recoverable,
                "retryable": err.retryable,
                "requires_manual_review": requires_manual_review,
                "processing_lifecycle": result.processing_lifecycle.value,
            },
        )

    if result.decision is None:
        raise HTTPException(
            status_code=422,
            detail={"error": "No decision produced", "category": "internal", "recoverable": False, "retryable": False},
        )

    decision = result.decision
    return TriageDecisionResponse(
        decision_id=decision.decision_id,
        case_id=decision.case_id,
        domain=decision.domain,
        action=decision.action,
        reason=decision.reason,
        urgency=decision.urgency,
        confidence=decision.confidence,
        evidence_summary=decision.evidence_summary,
        lifecycle=decision.lifecycle.value,
        processing_time_ms=decision.processing_time_ms,
        original_ai_proposal=decision.original_ai_proposal.model_dump() if decision.original_ai_proposal else None,
        human_override=decision.human_override.model_dump() if decision.human_override else None,
    )


@app.get("/api/v1/audit/{case_id}")
async def get_audit_events(case_id: str) -> dict[str, object]:
    events = await audit_adapter.get_events_by_case(case_id)
    return {
        "case_id": case_id,
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }


@app.get("/api/v1/hitl/pending")
async def list_pending_review(limit: int = 100) -> dict[str, object]:
    decisions = await decision_repo.list_pending_review(limit=limit)
    return {
        "decisions": [d.model_dump_ext() for d in decisions],
        "count": len(decisions),
    }


@app.get("/api/v1/hitl/{decision_id}")
async def get_decision(decision_id: str) -> dict[str, object]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    return decision.model_dump_ext()


@app.post("/api/v1/hitl/{decision_id}/under-review")
async def start_review(decision_id: str, request: HITLActionRequest) -> dict[str, str]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle != DecisionLifecycle.AI_PROPOSED:
        raise HTTPException(status_code=400, detail=f"Cannot transition from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.UNDER_REVIEW.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-review-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_UNDER_REVIEW",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
    ))

    return {"status": "under_review", "decision_id": decision_id}


@app.post("/api/v1/hitl/{decision_id}/approve")
async def approve_decision(decision_id: str, request: HITLActionRequest) -> dict[str, str]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot approve from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.APPROVED.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-approve-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_APPROVED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
    ))

    return {"status": "approved", "decision_id": decision_id}


@app.post("/api/v1/hitl/{decision_id}/reject")
async def reject_decision(decision_id: str, request: HITLActionRequest) -> dict[str, str]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot reject from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.REJECTED.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-reject-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_REJECTED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
    ))

    return {"status": "rejected", "decision_id": decision_id}


@app.post("/api/v1/hitl/{decision_id}/escalate")
async def escalate_decision(decision_id: str, request: HITLEscalateRequest) -> dict[str, object]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot escalate from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.ESCALATED.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-escalate-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_ESCALATED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification, "escalate_to": request.escalate_to},
        actor=request.actor,
    ))

    return {"status": "escalated", "decision_id": decision_id, "escalate_to": request.escalate_to}


@app.post("/api/v1/hitl/{decision_id}/modify")
async def modify_decision(decision_id: str, request: HITLModifyRequest) -> dict[str, object]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")

    original_action = decision.action
    original_urgency = decision.urgency
    original_confidence = decision.confidence
    original_evidence = decision.evidence_summary

    decision.action = request.action
    decision.reason = request.reason
    decision.urgency = request.urgency
    decision.confidence = request.confidence
    decision.evidence_summary = request.evidence_summary
    decision.lifecycle = DecisionLifecycle.MODIFIED
    decision.human_override = HumanOverride(
        actor=request.actor,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        justification=request.justification,
        original_action=original_action,
        original_urgency=original_urgency,
        original_confidence=original_confidence,
        original_evidence_summary=original_evidence,
    )

    await decision_repo.save_decision(decision)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-modify-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_MODIFIED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={
            "actor": request.actor,
            "justification": request.justification,
            "notes": request.notes,
            "original_action": original_action,
            "original_urgency": original_urgency,
            "new_action": request.action,
            "new_urgency": request.urgency,
        },
        actor=request.actor,
    ))

    return {"status": "modified", "decision_id": decision_id, "decision": decision.model_dump_ext()}
