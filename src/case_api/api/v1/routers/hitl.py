from __future__ import annotations

import time
import uuid

from fastapi import APIRouter, HTTPException, Request

from case_api.api.v1.routers.schemas import (
    HITLActionRequest,
    HITLEscalateRequest,
    HITLModifyRequest,
)
from case_api.api.v1.routers.shared import get_deps, require_scope_in_strict
from case_core.contracts.audit import AuditEvent
from case_core.contracts.decision import HumanOverride
from case_core.contracts.lifecycle import DecisionLifecycle

router = APIRouter()


@router.get("/api/v1/hitl/pending")
async def list_pending_review(http_request: Request, limit: int = 100) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:hitl:read", "case:read", "case:admin"])
    deps = get_deps()
    _ctx = getattr(http_request.state, "security_context", None)
    decisions = await deps.decision_repo.list_pending_review(limit=limit)
    return {
        "decisions": [d.model_dump_ext() for d in decisions],
        "count": len(decisions),
    }


@router.get("/api/v1/hitl/{decision_id}")
async def get_decision(decision_id: str, http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:hitl:read", "case:decision:read", "case:read", "case:admin"])
    deps = get_deps()
    _ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    return decision.model_dump_ext()


@router.post("/api/v1/hitl/{decision_id}/under-review")
async def start_review(decision_id: str, request: HITLActionRequest, http_request: Request) -> dict[str, str]:
    require_scope_in_strict(http_request, ["case:hitl:write", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle != DecisionLifecycle.AI_PROPOSED:
        raise HTTPException(status_code=400, detail=f"Cannot transition from {decision.lifecycle.value}")

    ok = await deps.decision_repo.update_lifecycle(decision_id, DecisionLifecycle.UNDER_REVIEW.value, request.actor, request.justification)  # type: ignore[func-returns-value,unused-ignore]
    if ok is False:
        raise HTTPException(status_code=409, detail="Concurrent HITL state change; transition rejected")

    await deps.audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-review-{decision_id}-{uuid.uuid4().hex[:8]}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_UNDER_REVIEW",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
        correlation_id=(getattr(ctx, "correlation_id", None) or "") if ctx else "",
    ))

    return {"status": "under_review", "decision_id": decision_id}


@router.post("/api/v1/hitl/{decision_id}/approve")
async def approve_decision(decision_id: str, request: HITLActionRequest, http_request: Request) -> dict[str, str]:
    require_scope_in_strict(http_request, ["case:hitl:write", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot approve from {decision.lifecycle.value}")

    ok = await deps.decision_repo.update_lifecycle(decision_id, DecisionLifecycle.APPROVED.value, request.actor, request.justification)  # type: ignore[func-returns-value,unused-ignore]
    if ok is False:
        raise HTTPException(status_code=409, detail="Concurrent HITL state change; transition rejected")

    await deps.audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-approve-{decision_id}-{uuid.uuid4().hex[:8]}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_APPROVED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
        correlation_id=(getattr(ctx, "correlation_id", None) or "") if ctx else "",
    ))

    return {"status": "approved", "decision_id": decision_id}


@router.post("/api/v1/hitl/{decision_id}/reject")
async def reject_decision(decision_id: str, request: HITLActionRequest, http_request: Request) -> dict[str, str]:
    require_scope_in_strict(http_request, ["case:hitl:write", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot reject from {decision.lifecycle.value}")

    ok = await deps.decision_repo.update_lifecycle(decision_id, DecisionLifecycle.REJECTED.value, request.actor, request.justification)  # type: ignore[func-returns-value,unused-ignore]
    if ok is False:
        raise HTTPException(status_code=409, detail="Concurrent HITL state change; transition rejected")

    await deps.audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-reject-{decision_id}-{uuid.uuid4().hex[:8]}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_REJECTED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
        correlation_id=(getattr(ctx, "correlation_id", None) or "") if ctx else "",
    ))

    return {"status": "rejected", "decision_id": decision_id}


@router.post("/api/v1/hitl/{decision_id}/escalate")
async def escalate_decision(decision_id: str, request: HITLEscalateRequest, http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:hitl:write", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot escalate from {decision.lifecycle.value}")

    ok = await deps.decision_repo.update_lifecycle(decision_id, DecisionLifecycle.ESCALATED.value, request.actor, request.justification)  # type: ignore[func-returns-value,unused-ignore]
    if ok is False:
        raise HTTPException(status_code=409, detail="Concurrent HITL state change; transition rejected")

    await deps.audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-escalate-{decision_id}-{uuid.uuid4().hex[:8]}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_ESCALATED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification, "escalate_to": request.escalate_to},
        actor=request.actor,
        correlation_id=(getattr(ctx, "correlation_id", None) or "") if ctx else "",
    ))

    return {"status": "escalated", "decision_id": decision_id, "escalate_to": request.escalate_to}


@router.post("/api/v1/hitl/{decision_id}/modify")
async def modify_decision(decision_id: str, request: HITLModifyRequest, http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:hitl:write", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    # Prevent silent overwrite of final/concurrent states (single-consumer safety)
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot modify from {decision.lifecycle.value}")

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

    # CAS-like: ensure state hasn't changed before persisting modification
    current = await deps.decision_repo.get_decision(decision_id)
    if not current or current.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=409, detail="Concurrent HITL state change; modification rejected")
    await deps.decision_repo.save_decision(decision)

    await deps.audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-modify-{decision_id}-{uuid.uuid4().hex[:8]}",
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
        correlation_id=(getattr(ctx, "correlation_id", None) or "") if ctx else "",
    ))

    return {"status": "modified", "decision_id": decision_id, "decision": decision.model_dump_ext()}
