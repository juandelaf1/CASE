import time
import uuid
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from case_api.api.v1.auth import APIKeyAuthMiddleware
from case_api.api.v1.rate_limit import RateLimitMiddleware
from case_core.composition import create_app_dependencies
from case_core.contracts.audit import AuditEvent
from case_core.contracts.decision import HumanOverride
from case_core.contracts.evidence import EvidenceItem, EvidenceType
from case_core.contracts.lifecycle import DecisionLifecycle
from case_core.contracts.operational_case import OperationalCase, UrgencyLevel
from case_core.version import VERSION

app = FastAPI(
    title="CASE — AI Decision Platform",
    version=VERSION,
    description="Domain-agnostic AI Decision Platform for operational case triage",
)

app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(RateLimitMiddleware)

_deps = create_app_dependencies()
engine = _deps.engine
registry = _deps.registry
audit_adapter = _deps.audit_adapter
decision_repo = _deps.decision_repo
provider = _deps.provider
providers = _deps.providers

VALID_EVIDENCE_TYPES = {t.value for t in EvidenceType}
VALID_URGENCY_LEVELS = {u.value for u in UrgencyLevel}
MAX_REPORT_LENGTH = 50000
MAX_EVIDENCE_ITEMS = 10
MAX_EVIDENCE_CONTENT_LENGTH = 10000
MAX_JUSTIFICATION_LENGTH = 5000


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": "CASE — Case Assessment and Structured Evaluation",
        "version": VERSION,
        "docs": "/docs",
        "health": "/health",
        "triage": "/api/v1/triage",
        "domains": "/domains",
    }


def _generate_case_id() -> str:
    short = uuid.uuid4().hex[:8].upper()
    return f"CASE-{short}"


class EvidenceRequest(BaseModel):
    id: str
    type: str
    content: str
    source: str
    confidence: float = Field(ge=0.0, le=1.0)
    extracted_at: str

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in VALID_EVIDENCE_TYPES:
            raise ValueError(f"Invalid evidence type: {v}. Valid types: {sorted(VALID_EVIDENCE_TYPES)}")
        return v

    @field_validator("content")
    @classmethod
    def validate_content(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evidence content cannot be empty")
        if len(v) > MAX_EVIDENCE_CONTENT_LENGTH:
            raise ValueError(f"Evidence content too long (max {MAX_EVIDENCE_CONTENT_LENGTH} characters)")
        return v.strip()

    @field_validator("source")
    @classmethod
    def validate_source(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Evidence source cannot be empty")
        return v.strip()


class TriageRequest(BaseModel):
    case_id: str | None = None
    report_text: str
    domain: str
    urgency: str = "MEDIUM"
    evidence: list[EvidenceRequest] = Field(default_factory=list)
    external_reference: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    provider: str | None = None

    @field_validator("report_text")
    @classmethod
    def validate_report_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Report text cannot be empty")
        if len(v) > MAX_REPORT_LENGTH:
            raise ValueError(f"Report text too long (max {MAX_REPORT_LENGTH} characters)")
        return v.strip()

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        if v not in VALID_URGENCY_LEVELS:
            raise ValueError(f"Invalid urgency: {v}. Valid levels: {sorted(VALID_URGENCY_LEVELS)}")
        return v

    @field_validator("domain")
    @classmethod
    def validate_domain(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Domain cannot be empty")
        return v.strip()

    @field_validator("evidence")
    @classmethod
    def validate_evidence_count(cls, v: list[EvidenceRequest]) -> list[EvidenceRequest]:
        if len(v) > MAX_EVIDENCE_ITEMS:
            raise ValueError(f"Too many evidence items (max {MAX_EVIDENCE_ITEMS})")
        return v


class TriageDecisionResponse(BaseModel):
    decision_id: str
    case_id: str
    external_reference: str | None = None
    domain: str
    action: str
    reason: str
    urgency: str
    reported_urgency: str | None = None
    confidence: float
    evidence_summary: str
    decision_rationale: str = ""
    decision_factors: list[str] = []
    summary: str = ""
    lifecycle: str
    processing_time_ms: float
    original_ai_proposal: dict[str, Any] | None = None
    human_override: dict[str, Any] | None = None
    provider_info: dict[str, Any] | None = None
    react_trace: dict[str, Any] | None = None
    cost: dict[str, Any] | None = None


class ErrorResponse(BaseModel):
    error: str
    category: str
    recoverable: bool
    retryable: bool
    requires_manual_review: bool = False


class HITLActionRequest(BaseModel):
    actor: str = "human"
    notes: str = ""
    justification: str = ""

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, v: str) -> str:
        if v and len(v) > MAX_JUSTIFICATION_LENGTH:
            raise ValueError(f"Justification too long (max {MAX_JUSTIFICATION_LENGTH} characters)")
        return v


class HITLModifyRequest(BaseModel):
    action: str
    reason: str
    urgency: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence_summary: str
    actor: str = "human"
    notes: str = ""
    justification: str = ""

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        valid = {"approve", "reject", "escalate"}
        if v not in valid:
            raise ValueError(f"Invalid action: {v}. Valid actions: {sorted(valid)}")
        return v

    @field_validator("urgency")
    @classmethod
    def validate_urgency(cls, v: str) -> str:
        if v not in VALID_URGENCY_LEVELS:
            raise ValueError(f"Invalid urgency: {v}. Valid levels: {sorted(VALID_URGENCY_LEVELS)}")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Reason cannot be empty")
        return v.strip()

    @field_validator("justification")
    @classmethod
    def validate_justification(cls, v: str) -> str:
        if v and len(v) > MAX_JUSTIFICATION_LENGTH:
            raise ValueError(f"Justification too long (max {MAX_JUSTIFICATION_LENGTH} characters)")
        return v


class HITLEscalateRequest(BaseModel):
    actor: str = "human"
    justification: str = ""
    escalate_to: str = "supervisor"


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


def _build_triage_request_from_evaluate(env: EvaluateEnvelopeRequest) -> tuple[TriageRequest, list[str]]:
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
    triage = TriageRequest(
        case_id=p.case_id,
        report_text=report_text[:MAX_REPORT_LENGTH],
        domain=str(p.domain).strip(),
        urgency=urgency,
        evidence=evidence_items[:MAX_EVIDENCE_ITEMS],
        metadata={k: str(v) for k, v in meta.items() if isinstance(k, str)},
        provider=p.provider,
    )
    return triage, warnings


def _map_triage_to_evaluate_response(env: EvaluateEnvelopeRequest, triage: TriageDecisionResponse) -> dict[str, Any]:
    requires_human_review = triage.lifecycle in {"AI_PROPOSED", "UNDER_REVIEW", "PENDING_REVIEW"}
    status = "pending_review" if requires_human_review else "ok"
    # If escalated/rejected etc still return ok status with lifecycle hint in dev adapter; keep additive
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
            "upstream_lifecycle": triage.lifecycle,
            **(env.provenance or {}),
        },
        "result": {
            "decision_type": "recommendation",
            "case_ref": triage.case_id,
            "action": triage.action,
            "urgency": triage.urgency,
            "confidence": triage.confidence,
            "risks": [],
            "decision_factors": list(triage.decision_factors or []),
            "evidence_summary": triage.evidence_summary,
            "requires_human_review": requires_human_review,
            "lifecycle_hint": triage.lifecycle,
            "reason": triage.reason,
            "summary": triage.summary,
            "decision_rationale": triage.decision_rationale,
            "processing_time_ms": triage.processing_time_ms,
        },
        "warnings": [],
        "errors": [],
    }


@app.post("/api/v1/evaluate")
async def evaluate_case(request: EvaluateEnvelopeRequest) -> dict[str, Any]:
    # Dev-stage scope/capability checks (additive boundary; CASE does not execute effects)
    if request.capability_id not in ("case.evaluate", ""):
        raise HTTPException(
            status_code=400,
            detail={
                "error": f"Unsupported capability_id: {request.capability_id}",
                "code": "CONTRACT_UNSUPPORTED",
                "correlation_id": request.correlation_id,
            },
        )
    if request.scopes and "case:evaluate" not in request.scopes:
        # dev-tolerant: warn via error response contract style? reject to be explicit
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Missing required scope: case:evaluate",
                "code": "AUTHZ_SCOPE_MISSING",
                "correlation_id": request.correlation_id,
            },
        )
    triage_req, warnings = _build_triage_request_from_evaluate(request)
    try:
        triage_resp = await triage(triage_req)
    except HTTPException as e:
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
    return out



@app.get("/health")
async def health() -> dict[str, object]:
    import sqlite3 as _sqlite3

    db_ok = False
    db_path = decision_repo._db_path
    try:
        conn = _sqlite3.connect(db_path)
        conn.execute("SELECT 1 FROM decisions LIMIT 1")
        conn.execute("SELECT 1 FROM audit_events LIMIT 1")
        db_ok = True
        conn.close()
    except Exception:
        db_ok = False

    provider_info = []
    for _name, p in providers.items():
        provider_info.append({
            "name": p.name,
            "model": p.model,
        })

    return {
        "status": "ok" if db_ok else "degraded",
        "version": VERSION,
        "database": "ok" if db_ok else "missing_tables",
        "db_path": db_path,
        "domains": registry.list_domains(),
        "domain_count": len(registry.list_domains()),
        "active_provider": provider.name,
        "providers": provider_info,
    }


@app.get("/domains")
async def list_domains() -> dict[str, list[str]]:
    return {"domains": registry.list_domains()}


@app.get("/api/v1/providers")
async def list_providers() -> dict[str, object]:
    provider_list = []
    for _name, p in providers.items():
        provider_list.append({
            "name": p.name,
            "model": p.model,
            "is_mock": p.name == "mock",
        })
    return {
        "providers": provider_list,
        "active_provider": provider.name,
    }


@app.get("/api/v1/cases")
async def list_cases(limit: int = 50, offset: int = 0) -> dict[str, object]:
    decisions = await decision_repo.list_decisions(limit=limit, offset=offset)
    total = await decision_repo.count_decisions()
    return {
        "decisions": [d.model_dump_ext() for d in decisions],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@app.get("/api/v1/cases/{case_id}")
async def get_case(case_id: str) -> dict[str, object]:
    decision = await decision_repo.get_decision_by_case(case_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"No decision found for case: {case_id}")
    audit_events = await audit_adapter.get_events_by_case(case_id)
    return {
        "case_id": case_id,
        "decision": decision.model_dump_ext(),
        "audit_events": [e.model_dump() for e in audit_events],
        "audit_count": len(audit_events),
    }


@app.post("/api/v1/triage")
async def triage(request: TriageRequest) -> TriageDecisionResponse:
    if not registry.validate_domain(request.domain):
        raise HTTPException(
            status_code=400,
            detail=f"Unknown domain: {request.domain}. Valid domains: {registry.list_domains()}",
        )

    case_id = request.case_id or _generate_case_id()
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

    result = await engine.execute(case, provider_name=request.provider)

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


@app.get("/api/v1/audit/{case_id}")
async def get_audit_events(case_id: str) -> dict[str, object]:
    events = await audit_adapter.get_events_by_case(case_id)
    return {
        "case_id": case_id,
        "events": [e.model_dump() for e in events],
        "count": len(events),
    }


@app.get("/api/v1/hitl/pending")
async def list_pending_review(limit: int = 100) -> dict[str, object]:
    decisions = await decision_repo.list_pending_review(limit=limit)
    return {
        "decisions": [d.model_dump_ext() for d in decisions],
        "count": len(decisions),
    }


@app.get("/api/v1/hitl/{decision_id}")
async def get_decision(decision_id: str) -> dict[str, object]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    return decision.model_dump_ext()


@app.post("/api/v1/hitl/{decision_id}/under-review")
async def start_review(decision_id: str, request: HITLActionRequest) -> dict[str, str]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle != DecisionLifecycle.AI_PROPOSED:
        raise HTTPException(status_code=400, detail=f"Cannot transition from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.UNDER_REVIEW.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-review-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_UNDER_REVIEW",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
    ))

    return {"status": "under_review", "decision_id": decision_id}


@app.post("/api/v1/hitl/{decision_id}/approve")
async def approve_decision(decision_id: str, request: HITLActionRequest) -> dict[str, str]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot approve from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.APPROVED.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-approve-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_APPROVED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
    ))

    return {"status": "approved", "decision_id": decision_id}


@app.post("/api/v1/hitl/{decision_id}/reject")
async def reject_decision(decision_id: str, request: HITLActionRequest) -> dict[str, str]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot reject from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.REJECTED.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-reject-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_REJECTED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification},
        actor=request.actor,
    ))

    return {"status": "rejected", "decision_id": decision_id}


@app.post("/api/v1/hitl/{decision_id}/escalate")
async def escalate_decision(decision_id: str, request: HITLEscalateRequest) -> dict[str, object]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")
    if decision.lifecycle not in (DecisionLifecycle.AI_PROPOSED, DecisionLifecycle.UNDER_REVIEW):
        raise HTTPException(status_code=400, detail=f"Cannot escalate from {decision.lifecycle.value}")

    await decision_repo.update_lifecycle(decision_id, DecisionLifecycle.ESCALATED.value, request.actor, request.justification)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-escalate-{decision_id}",
        case_id=decision.case_id,
        decision_id=decision_id,
        event_type="HITL_ESCALATED",
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        details={"actor": request.actor, "justification": request.justification, "escalate_to": request.escalate_to},
        actor=request.actor,
    ))

    return {"status": "escalated", "decision_id": decision_id, "escalate_to": request.escalate_to}


@app.post("/api/v1/hitl/{decision_id}/modify")
async def modify_decision(decision_id: str, request: HITLModifyRequest) -> dict[str, object]:
    decision = await decision_repo.get_decision(decision_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"Decision not found: {decision_id}")

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

    await decision_repo.save_decision(decision)

    await audit_adapter.log_event(AuditEvent(
        event_id=f"ae-hitl-modify-{decision_id}",
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
    ))

    return {"status": "modified", "decision_id": decision_id, "decision": decision.model_dump_ext()}


class ComparisonRequest(BaseModel):
    case_id: str | None = None
    report_text: str
    domain: str
    urgency: str = "MEDIUM"
    evidence: list[EvidenceRequest] = Field(default_factory=list)
    external_reference: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    providers: list[str] = Field(default_factory=list)

    @field_validator("report_text")
    @classmethod
    def validate_report_text(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Report text cannot be empty")
        return v.strip()


@app.post("/api/v1/comparison")
async def compare(request: ComparisonRequest) -> dict[str, object]:
    if not registry.validate_domain(request.domain):
        raise HTTPException(status_code=400, detail=f"Unknown domain: {request.domain}")

    for pname in request.providers:
        if pname not in providers:
            raise HTTPException(status_code=422, detail=f"Unknown provider: {pname}")

    base_case_id = request.case_id or _generate_case_id()

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
        case_id = _generate_case_id()
        case = OperationalCase(
            case_id=case_id, report_text=request.report_text, domain=request.domain,
            urgency=UrgencyLevel(request.urgency), evidence=list(evidence), metadata=dict(meta),
        )
        res = await engine.execute(case, provider_name=pname)
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


@app.get("/api/v1/seismic/events")
async def get_seismic_events(
    min_magnitude: float = 4.5,
    lookback_days: int = 30,
    limit: int = 50,
) -> dict[str, object]:
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


@app.get("/api/v1/seismic/health")
async def seismic_health() -> dict[str, object]:
    from usgs_adapter.client import USGSClient

    client = USGSClient()
    reachable = client.health_check()
    return {
        "status": "ok" if reachable else "unreachable",
        "api": "USGS Earthquake Hazards API",
        "reachable": reachable,
    }
