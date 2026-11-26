from __future__ import annotations

from fastapi import APIRouter, Request

from case_api.api.v1.routers.shared import require_scope_in_strict

router = APIRouter()


@router.get("/api/v1/seismic/events")
async def get_seismic_events(
    http_request: Request,
    min_magnitude: float = 4.5,
    lookback_days: int = 30,
    limit: int = 50,
) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:read", "case:admin"])
    from usgs_adapter.client import USGSClient

    client = USGSClient(min_magnitude=min_magnitude, lookback_days=lookback_days)
    events = client.fetch_recent()
    return {
        "events": [e.to_dict() for e in events[:limit]],
        "count": min(len(events), limit),
        "total_available": len(events),
        "min_magnitude": min_magnitude,
        "lookback_days": lookback_days,
    }


@router.get("/api/v1/seismic/health")
async def seismic_health(http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:read", "case:admin"])
    from usgs_adapter.client import USGSClient

    client = USGSClient()
    reachable = client.health_check()
    return {
        "status": "ok" if reachable else "unreachable",
        "api": "USGS Earthquake Hazards API",
        "reachable": reachable,
    }
