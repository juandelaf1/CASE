from __future__ import annotations

from fastapi import APIRouter, Request

from case_api.api.v1.routers.shared import get_deps, require_scope_in_strict

router = APIRouter()


@router.get("/api/v1/audit/{case_id}")
async def get_audit_events(case_id: str, http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:audit:read", "case:read", "case:admin"])
    deps = get_deps()
    ctx = getattr(http_request.state, "security_context", None)
    events = await deps.audit_adapter.get_events_by_case(case_id)
    return {
        "case_id": case_id,
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }
