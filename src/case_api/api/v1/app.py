"""FastAPI application assembly for CASE v1 API.

This module is intentionally thin: it wires middleware, initializes shared state,
and includes capability routers. Route handlers live in `case_api.api.v1.routers`.
"""
from __future__ import annotations

from fastapi import FastAPI

from case_api.api.v1.auth import APIKeyAuthMiddleware
from case_api.api.v1.rate_limit import RateLimitMiddleware
from case_api.api.v1.routers import (
    audit,
    cases,
    comparison,
    domains,
    evaluate,
    hitl,
    seismic,
)
from case_api.api.v1.routers import (
    health as health_router,
)
from case_api.api.v1.routers import (
    providers as providers_router,
)
from case_api.api.v1.routers import (
    triage as triage_router,
)

# Backward-compatible handler/schema exports (tests import these from app module)
from case_api.api.v1.routers.audit import get_audit_events  # noqa: F401
from case_api.api.v1.routers.cases import get_case, list_cases  # noqa: F401
from case_api.api.v1.routers.comparison import compare  # noqa: F401
from case_api.api.v1.routers.domains import list_domains  # noqa: F401
from case_api.api.v1.routers.evaluate import (  # noqa: F401
    EvaluateEnvelopeRequest,
    EvaluatePayload,
    evaluate_case,
)
from case_api.api.v1.routers.health import health, root  # noqa: F401
from case_api.api.v1.routers.hitl import (  # noqa: F401
    approve_decision,
    escalate_decision,
    get_decision,
    list_pending_review,
    modify_decision,
    reject_decision,
    start_review,
)
from case_api.api.v1.routers.providers import list_providers  # noqa: F401
from case_api.api.v1.routers.schemas import (  # noqa: F401
    ComparisonRequest,
    ErrorResponse,
    EvidenceRequest,
    HITLActionRequest,
    HITLEscalateRequest,
    HITLModifyRequest,
    TriageDecisionResponse,
    TriageRequest,
)
from case_api.api.v1.routers.seismic import get_seismic_events, seismic_health  # noqa: F401
from case_api.api.v1.routers.shared import init_state
from case_api.api.v1.routers.triage import triage  # noqa: F401

try:
    from case_api.api.v1.security import load_security_config
except Exception:  # pragma: no cover - base compat when WIP module not committed
    def load_security_config():  # type: ignore[misc]
        class _Cfg:
            mode = "dev"
            dev_open_access = True
            consumers_by_key_hash: dict = {}
            single_tenant_id = None
            is_strict = False
            has_credentials = False

        return _Cfg()
from case_core.version import VERSION

app = FastAPI(
    title="CASE \u2014 AI Decision Platform",
    version=VERSION,
    description="Domain-agnostic AI Decision Platform for operational case triage",
)

# Load and validate security config at startup (fail-fast in shared/prod on missing/unsafe config).
_security_config = load_security_config()
app.state.security_config = _security_config

try:
    app.add_middleware(APIKeyAuthMiddleware, config=_security_config)  # type: ignore[call-arg,unused-ignore]
except TypeError:
    app.add_middleware(APIKeyAuthMiddleware)
app.add_middleware(RateLimitMiddleware)

_state = init_state()
_deps = _state.deps
engine = _deps.engine
registry = _deps.registry
audit_adapter = _deps.audit_adapter
decision_repo = _deps.decision_repo
provider = _deps.provider
providers = _deps.providers
_idempotency_store = _state.idempotency_store

# Routers
app.include_router(health_router.router)
app.include_router(domains.router)
app.include_router(providers_router.router)
app.include_router(cases.router)
app.include_router(triage_router.router)
app.include_router(audit.router)
app.include_router(hitl.router)
app.include_router(comparison.router)
app.include_router(evaluate.router)
app.include_router(seismic.router)

__all__ = [
    "app",
    "engine",
    "registry",
    "audit_adapter",
    "decision_repo",
    "provider",
    "providers",
    "EvaluateEnvelopeRequest",
    "EvaluatePayload",
    "TriageRequest",
    "TriageDecisionResponse",
]
