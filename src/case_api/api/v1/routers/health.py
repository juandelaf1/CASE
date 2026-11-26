from __future__ import annotations

from fastapi import APIRouter

from case_api.api.v1.routers.shared import VERSION, get_deps

router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    return {
        "name": "CASE \u2014 Case Assessment and Structured Evaluation",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
        "triage": "/api/v1/triage",
        "domains": "/domains",
    }


@router.get("/health")
async def health() -> dict[str, object]:
    import sqlite3 as _sqlite3

    deps = get_deps()
    db_ok = False
    db_path = deps.decision_repo._db_path
    try:
        conn = _sqlite3.connect(db_path)
        conn.execute("SELECT 1 FROM decisions LIMIT 1")
        conn.execute("SELECT 1 FROM audit_events LIMIT 1")
        db_ok = True
        conn.close()
    except Exception:
        db_ok = False

    provider_info = []
    for _name, p in deps.providers.items():
        provider_info.append({
            "name": p.name,
            "model": p.model,
        })

    return {
        "status": "ok" if db_ok else "degraded",
        "version": VERSION,
        "database": "ok" if db_ok else "missing_tables",
        "db_path": db_path,
        "domains": deps.registry.list_domains(),
        "domain_count": len(deps.registry.list_domains()),
        "active_provider": deps.provider.name,
        "providers": provider_info,
    }
