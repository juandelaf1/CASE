from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from case_api.api.v1.routers.schemas import TriageDecisionResponse, TriageRequest
from case_api.api.v1.routers.shared import generate_case_id, get_deps, require_scope_in_strict
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel

router = APIRouter()


@router.post("/api/v1/triage")
async def triage(request: TriageRequest, http_request: Request) -> TriageDecisionResponse:
    require_scope_in_strict(http_request, ["case:triage", "case:evaluate", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    if not deps.registry.validate_domain(request.domain):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain: {request.domain}. Valid domains: {deps.registry.list_domains()}",
        )

    case_id = request.case_id or generate_case_id()
    reported_urgency = request.urgency

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

    meta = dict(request.metadata)
    if request.external_reference:
        meta["external_reference"] = request.external_reference

    case = OperationalCase(
        case_id=case_id,
        report_text=request.report_text,
        domain=request.domain,
        urgency=UrgencyLevel(request.urgency),
        evidence=evidence,
        metadata=meta,
    )
    # Propagate operation correlation into case for downstream persistence/audit linkage
    if meta.get("operation_id"):
        case.metadata["operation_id"] = str(meta.get("operation_id", ""))
    if meta.get("correlation_id"):
        case.metadata["correlation_id"] = str(meta.get("correlation_id", ""))

    result = await deps.engine.execute(case, provider_name=request.provider, security_context=ctx)

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
        external_reference=request.external_reference,
        domain=decision.domain,
        action=decision.action,
        reason=decision.reason,
        urgency=decision.urgency,
        reported_urgency=reported_urgency,
        confidence=decision.confidence,
        evidence_summary=decision.evidence_summary,
        decision_rationale=decision.decision_rationale,
        decision_factors=decision.decision_factors,
        summary=decision.summary,
        lifecycle=decision.lifecycle.value,
        processing_time_ms=decision.processing_time_ms,
        original_ai_proposal=decision.original_ai_proposal.model_dump() if decision.original_ai_proposal else None,
        human_override=decision.human_override.model_dump() if decision.human_override else None,
        provider_info=decision.metadata.get("provider_info"),
        react_trace=decision.metadata.get("react_trace"),
        cost=decision.metadata.get("cost"),
    )
