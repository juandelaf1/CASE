from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from case_api.api.v1.routers.schemas import EvidenceRequest, TriageDecisionResponse, TriageRequest
from case_api.api.v1.routers.shared import (
    MAX_EVIDENCE_CONTENT_LENGTH,
    MAX_EVIDENCE_ITEMS,
    MAX_REPORT_LENGTH,
    VALID_EVIDENCE_TYPES,
    VALID_URGENCY_LEVELS,
    get_idempotency_store,
)
from case_api.api.v1.routers.triage import triage
from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

router = APIRouter()


# --- case.evaluate boundary adapter (dev-stage, additive; no execution authority) ---
class EvaluatePayload(BaseModel):
    case_id: str | None = None
    domain: str
    summary: str | None = None
    report_text: str | None = None
    urgency: str = "MEDIUM"
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    provider: str | None = None
    options: dict[str, Any] = Field(default_factory=dict)


class EvaluateEnvelopeRequest(BaseModel):
    contract_version: str = "case-eval/v0.1-draft"
    capability_id: str = "case.evaluate"
    correlation_id: str
    idempotency_key: str | None = None
    caller: dict[str, Any] = Field(default_factory=dict)
    tenant_context: dict[str, Any] | None = None
    organization_context: dict[str, Any] | None = None
    scopes: list[str] = Field(default_factory=list)
    data_classification: str | None = None
    data_status: str | None = None
    provenance: dict[str, Any] = Field(default_factory=dict)
    payload: EvaluatePayload


def _build_triage_request_from_evaluate(env: EvaluateEnvelopeRequest) -> tuple[TriageRequest, list[dict[str, Any]]]:
    warnings: list[dict[str, Any]] = []
    p = env.payload
    report_text = (p.report_text or p.summary or "").strip()
    if not report_text:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "payload.summary or payload.report_text is required",
                "code": "VALIDATION_MISSING_FIELD",
                "correlation_id": env.correlation_id,
            },
        )
    evidence_items: list[EvidenceRequest] = []
    for i, e in enumerate(p.evidence or []):
        if not isinstance(e, dict):
            continue
        ev_type = str(e.get("type", "text"))
        if ev_type not in VALID_EVIDENCE_TYPES:
            ev_type = "text"
        content = str(e.get("content", "") or "").strip() or "(no content)"
        source = str(e.get("source", "unknown") or "unknown").strip() or "unknown"
        try:
            conf = float(e.get("confidence", 0.5))
        except Exception:
            conf = 0.5
        conf = max(0.0, min(1.0, conf))
        evidence_items.append(
            EvidenceRequest(
                id=str(e.get("id") or f"ev-{i+1}"),
                type=ev_type,
                content=content[:MAX_EVIDENCE_CONTENT_LENGTH],
                source=source,
                confidence=conf,
                extracted_at=str(e.get("extracted_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
            )
        )
    meta = dict(p.metadata or {})
    meta.setdefault("correlation_id", env.correlation_id)
    if env.tenant_context:
        meta.setdefault("tenant_context", "provided")
    if env.organization_context:
        meta.setdefault("organization_context", "provided")
    urgency = p.urgency if p.urgency in VALID_URGENCY_LEVELS else "MEDIUM"
    triage_req = TriageRequest(
        case_id=p.case_id,
        report_text=report_text[:MAX_REPORT_LENGTH],
        domain=str(p.domain).strip(),
        urgency=urgency,
        evidence=evidence_items[:MAX_EVIDENCE_ITEMS],
        metadata={k: str(v) for k, v in meta.items() if isinstance(k, str)},
        provider=p.provider,
    )
    return triage_req, warnings


def _map_triage_to_evaluate_response(env: EvaluateEnvelopeRequest, triage_resp: TriageDecisionResponse) -> dict[str, Any]:
    requires_human_review = triage_resp.lifecycle in {"AI_PROPOSED", "UNDER_REVIEW", "PENDING_REVIEW"}
    status = "pending_review" if requires_human_review else "ok"
    return {
        "contract_version": "case-eval/v0.1-draft",
        "capability_id": "case.evaluate",
        "correlation_id": env.correlation_id,
        "idempotency_key": env.idempotency_key,
        "status": status,
        "data_status": env.data_status or "derived",
        "provenance": {
            "provider": "case",
            "mapping": "case.evaluate adapter over /api/v1/triage",
            "upstream_lifecycle": triage_resp.lifecycle,
            **(env.provenance or {}),
        },
        "result": {
            "decision_type": "recommendation",
            "case_ref": triage_resp.case_id,
            "action": triage_resp.action,
            "urgency": triage_resp.urgency,
            "confidence": triage_resp.confidence,
            "risks": [],
            "decision_factors": list(triage_resp.decision_factors or []),
            "evidence_summary": triage_resp.evidence_summary,
            "requires_human_review": requires_human_review,
            "lifecycle_hint": triage_resp.lifecycle,
            "reason": triage_resp.reason,
            "summary": triage_resp.summary,
            "decision_rationale": triage_resp.decision_rationale,
            "processing_time_ms": triage_resp.processing_time_ms,
        },
        "warnings": [],
        "errors": [],
    }


@router.post("/api/v1/evaluate")
async def evaluate_case(request: EvaluateEnvelopeRequest, http_request: Request) -> dict[str, Any]:
    # Capability check (additive boundary; CASE does not execute effects)
    if request.capability_id not in ("case.evaluate", ""):
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unsupported capability_id: {request.capability_id}",
                "code": "CONTRACT_UNSUPPORTED",
                "correlation_id": request.correlation_id,
            },
        )

    identity = getattr(http_request.state, "identity", None)
    security_mode = getattr(http_request.state, "security_mode", "dev")
    security_context = getattr(http_request.state, "security_context", None)
    _idempotency_store = get_idempotency_store()

    # Strict modes (shared/prod): require authenticated identity and server-derived scopes/tenant.
    if security_mode in ("shared", "prod"):
        if identity is None:
            raise HTTPException(
                status_code=401,
                detail={
                    "error": "Authentication required",
                    "code": "AUTHENTICATION_REQUIRED",
                    "correlation_id": request.correlation_id,
                },
            )
        if "case:evaluate" not in identity.scope_set:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Missing required scope: case:evaluate",
                    "code": "AUTHZ_SCOPE_MISSING",
                    "correlation_id": request.correlation_id,
                },
            )
        # Tenant/organization must come from authenticated context; reject mismatches/spoofing attempts.
        if request.tenant_context:
            req_tenant = str(request.tenant_context.get("tenant_id") or request.tenant_context.get("id") or "").strip()
            if req_tenant and identity.tenant_id and req_tenant != identity.tenant_id:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Tenant context does not match authenticated identity",
                        "code": "AUTHZ_TENANT_MISMATCH",
                        "correlation_id": request.correlation_id,
                    },
                )
            if req_tenant and not identity.tenant_id:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Tenant context not authorized for this identity",
                        "code": "AUTHZ_TENANT_NOT_ALLOWED",
                        "correlation_id": request.correlation_id,
                    },
                )
        if request.organization_context:
            req_org = str(request.organization_context.get("organization_id") or request.organization_context.get("id") or "").strip()
            if req_org and identity.organization_id and req_org != identity.organization_id:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Organization context does not match authenticated identity",
                        "code": "AUTHZ_ORG_MISMATCH",
                        "correlation_id": request.correlation_id,
                    },
                )
            if req_org and not identity.organization_id:
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "Organization context not authorized for this identity",
                        "code": "AUTHZ_ORG_NOT_ALLOWED",
                        "correlation_id": request.correlation_id,
                    },
                )
        # Bind request context to server identity (ignore payload-declared tenant/org/scopes for authz).
        request = request.model_copy(
            update={
                "caller": {"consumer_id": identity.consumer_id, **(request.caller or {})},
                "scopes": sorted(identity.scope_set),
                "tenant_context": {"tenant_id": identity.tenant_id} if identity.tenant_id else None,
                "organization_context": {"organization_id": identity.organization_id} if identity.organization_id else None,
            }
        )
    else:
        # Dev mode (explicit): preserve backward-compatible behavior for existing local/dev tests.
        if request.scopes and "case:evaluate" not in request.scopes:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "Missing required scope: case:evaluate",
                    "code": "AUTHZ_SCOPE_MISSING",
                    "correlation_id": request.correlation_id,
                },
            )

    # Idempotency (scoped by authenticated consumer/tenant in strict mode)
    idem_key = (request.idempotency_key or "").strip() or None
    idem_hash = None
    operation_id: str | None = None
    if idem_key and security_context is not None and security_mode in ("shared", "prod"):
        import uuid as _uuid
        proposed_operation_id = f"op-{_uuid.uuid4().hex}"
        idem_hash = SQLiteIdempotencyStore.hash_request(request.model_dump(mode="json"))
        req_ctx = {
            "contract_version": request.contract_version,
            "capability_id": request.capability_id,
            "correlation_id": request.correlation_id,
            "idempotency_key": request.idempotency_key,
            "data_status": request.data_status or "derived",
            "provenance": dict(request.provenance or {}),
        }
        acquired, rec = _idempotency_store.begin(
            security_context,
            "case.evaluate",
            idem_key,
            idem_hash,
            operation_id=proposed_operation_id,
            correlation_id=request.correlation_id,
            request_context=req_ctx,
        )
        if acquired and rec:
            operation_id = rec.operation_id or proposed_operation_id
        elif not acquired and rec:
            operation_id = rec.operation_id
            if rec.request_hash != idem_hash:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "Idempotency key reuse with different request payload",
                        "code": "IDEMPOTENCY_CONFLICT",
                        "correlation_id": request.correlation_id,
                        "operation_id": rec.operation_id,
                    },
                )
            if rec.status == "completed" and rec.response_json:
                try:
                    cached: dict[str, Any] = json.loads(rec.response_json)
                    if rec.operation_id and isinstance(cached, dict):
                        cached.setdefault("operation_id", rec.operation_id)
                    return cached
                except Exception:
                    pass
            if rec.status in {"recovery_required", "failed", "reconciling"}:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "error": "Idempotent request requires reconciliation/recovery before retry",
                        "code": "IDEMPOTENCY_RECOVERY_REQUIRED",
                        "correlation_id": request.correlation_id,
                        "operation_id": rec.operation_id,
                    },
                )
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Idempotent request is already in progress",
                    "code": "IDEMPOTENCY_IN_PROGRESS",
                    "correlation_id": request.correlation_id,
                    "operation_id": rec.operation_id,
                },
            )

    triage_req, warnings = _build_triage_request_from_evaluate(request)
    if operation_id:
        try:
            md = dict(getattr(triage_req, "metadata", None) or {})
            md["operation_id"] = str(operation_id)
            md["correlation_id"] = str(request.correlation_id)
            triage_req.metadata = md
        except Exception:
            pass
    try:
        triage_resp = await triage(triage_req, http_request)
    except HTTPException as e:
        if idem_key and security_context is not None and idem_hash and security_mode in ("shared", "prod"):
            _idempotency_store.release(security_context, "case.evaluate", idem_key)
        detail = e.detail if isinstance(e.detail, dict) else {"error": str(e.detail)}
        return {
            "contract_version": "case-eval/v0.1-draft",
            "capability_id": "case.evaluate",
            "correlation_id": request.correlation_id,
            "status": "error",
            "data_status": request.data_status or "unknown",
            "provenance": {"provider": "case", "mapping": "case.evaluate adapter"},
            "result": {"decision_type": "recommendation", "requires_human_review": True, "case_ref": None},
            "warnings": warnings,
            "errors": [{"code": str(detail.get("category") or "EVALUATION_ERROR"), "message": str(detail.get("error") or detail)}],
        }
    out = _map_triage_to_evaluate_response(request, triage_resp)
    out["warnings"] = warnings
    if operation_id and isinstance(out, dict):
        out["operation_id"] = operation_id
        try:
            if isinstance(out.get("result"), dict):
                out["result"].setdefault("operation_id", operation_id)
        except Exception:
            pass
    if idem_key and security_context is not None and idem_hash and security_mode in ("shared", "prod"):
        try:
            _fh_maybe_raise: Any = None
            try:
                from case_core.fault_hooks import maybe_raise as _fh_maybe_raise_fn
                _fh_maybe_raise = _fh_maybe_raise_fn
            except Exception:
                pass
            if _fh_maybe_raise:
                _fh_maybe_raise("before_idempotency_complete")
            case_ref = None
            decision_id = None
            try:
                case_ref = (out.get("result") or {}).get("case_ref")
            except Exception:
                case_ref = None
            try:
                decision_id = out.get("decision_id") or (out.get("result") or {}).get("decision_id")
            except Exception:
                decision_id = None
            _idempotency_store.complete(
                security_context,
                "case.evaluate",
                idem_key,
                json.dumps(out, default=str),
                200,
                case_id=case_ref,
                decision_id=decision_id,
                result_ref={"case_ref": case_ref, "decision_id": decision_id, "correlation_id": request.correlation_id, "operation_id": operation_id},
            )
            if _fh_maybe_raise:
                _fh_maybe_raise("after_idempotency_complete")
        except Exception:
            # Do not release: business evaluation may already have persisted decisions/audit.
            # Releasing would allow retries to re-execute and duplicate side effects.
            # Leave as in_progress so retries are safely rejected (409) pending recovery.
            pass
    _fh_maybe_raise2: Any = None
    try:
        from case_core.fault_hooks import maybe_raise as _fh_maybe_raise2_fn
        _fh_maybe_raise2 = _fh_maybe_raise2_fn
    except Exception:
        pass
    if _fh_maybe_raise2:
        _fh_maybe_raise2("before_response_return")
    return out
