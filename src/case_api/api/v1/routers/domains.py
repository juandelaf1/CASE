from __future__ import annotations

from fastapi import APIRouter, Request

from case_api.api.v1.routers.shared import get_deps, require_scope_in_strict

router = APIRouter()


@router.get("/domains")
async def list_domains(http_request: Request) -> dict[str, list[str]]:
    require_scope_in_strict(http_request, ["case:read", "case:admin"])
    return {"domains": get_deps().registry.list_domains()}
