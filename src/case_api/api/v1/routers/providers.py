from __future__ import annotations

from fastapi import APIRouter, Request

from case_api.api.v1.routers.shared import get_deps, require_scope_in_strict

router = APIRouter()


@router.get("/api/v1/providers")
async def list_providers(http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:read", "case:admin"])
    deps = get_deps()
    provider_list = []
    for _name, p in deps.providers.items():
        provider_list.append({
            "name": p.name,
            "model": p.model,
            "is_mock": p.name == "mock",
        })
    return {
        "providers": provider_list,
        "active_provider": deps.provider.name,
    }
