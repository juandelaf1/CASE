from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from case_api.api.v1.routers.shared import get_deps, require_scope_in_strict

router = APIRouter()


@router.get("/api/v1/cases")
async def list_cases(http_request: Request, limit: int = 50, offset: int = 0) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:read", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    decisions = await deps.decision_repo.list_decisions(limit=limit, offset=offset)
    total = await deps.decision_repo.count_decisions(security_context=ctx)
    return {
        "decisions": [d.model_dump_ext() for d in decisions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str, http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:read", "case:decision:read", "case:admin"])
    deps = get_deps()
    _ctx = getattr(http_request.state, "security_context", None)
    decision = await deps.decision_repo.get_decision_by_case(case_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"No decision found for case: {case_id}")
    audit_events = await deps.audit_adapter.get_events_by_case(case_id)
    return {
        "case_id": case_id,
        "decision": decision.model_dump_ext(),
        "audit_events": [e.model_dump() for e in audit_events],
        "audit_count": len(audit_events),
    }
