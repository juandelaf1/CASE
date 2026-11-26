from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from case_api.api.v1.routers.schemas import ComparisonRequest
from case_api.api.v1.routers.shared import generate_case_id, get_deps, require_scope_in_strict
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel

router = APIRouter()


@router.post("/api/v1/comparison")
async def compare(request: ComparisonRequest, http_request: Request) -> dict[str, object]:
    require_scope_in_strict(http_request, ["case:compare", "case:triage", "case:evaluate", "case:admin"])
    deps = get_deps()
    _ctx = getattr(http_request.state, "security_context", None)
    if not deps.registry.validate_domain(request.domain):
        raise HTTPException(status_code=400, detail=f"Unknown domain: {request.domain}")

    for pname in request.providers:
        if pname not in deps.providers:
            raise HTTPException(status_code=422, detail=f"Unknown provider: {pname}")

    base_case_id = request.case_id or generate_case_id()

    evidence = [
        EvidenceItem(
            id=e.id, type=EvidenceType(e.type), content=e.content,
            source=e.source, confidence=e.confidence, extracted_at=e.extracted_at,
        )
        for e in request.evidence
    ]

    meta = dict(request.metadata)
    if request.external_reference:
        meta["external_reference"] = request.external_reference

    results = []
    for pname in request.providers:
        case_id = generate_case_id()
        case = OperationalCase(
            case_id=case_id, report_text=request.report_text, domain=request.domain,
            urgency=UrgencyLevel(request.urgency), evidence=list(evidence), metadata=dict(meta),
        )
        res = await deps.engine.execute(case, provider_name=pname)
        results.append({
            "provider": pname,
            "case_id": case_id,
            "decision": res.decision.model_dump_ext() if res.decision else None,
            "error": res.error.model_dump() if res.error else None,
        })

    return {
        "case_id": base_case_id,
        "results": results,
    }
