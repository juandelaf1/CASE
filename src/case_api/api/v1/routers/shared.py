"""Shared API state, constants, and helpers for v1 routers."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any, cast

from fastapi import HTTPException, Request

from case_core.composition import AppDependencies, create_app_dependencies
from case_core.contracts.evidence import EvidenceType
from case_core.contracts.operational_case import UrgencyLevel as CaseUrgencyLevel
from case_core.version import VERSION

try:
    from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore
except Exception:  # pragma: no cover - base compat when WIP module not committed
    import hashlib
    import json as _json

    class SQLiteIdempotencyStore:  # type: ignore[no-redef]
        def __init__(self, db_path: str = "case_audit.db") -> None:
            self.db_path = db_path

        @staticmethod
        def hash_request(payload: dict[str, Any]) -> str:
            return hashlib.sha256(_json.dumps(payload, sort_keys=True, default=str).encode()).hexdigest()

        def begin(self, *args: Any, **kwargs: Any) -> tuple[bool, Any]:
            return True, None

        def complete(self, *args: Any, **kwargs: Any) -> None:
            return None

        def release(self, *args: Any, **kwargs: Any) -> None:
            return None

VALID_EVIDENCE_TYPES = {t.value for t in EvidenceType}
VALID_URGENCY_LEVELS = {u.value for u in CaseUrgencyLevel}
MAX_REPORT_LENGTH = 50000
MAX_EVIDENCE_ITEMS = 10
MAX_EVIDENCE_CONTENT_LENGTH = 10000
MAX_JUSTIFICATION_LENGTH = 5000


@dataclass
class APIState:
    deps: AppDependencies
    idempotency_store: SQLiteIdempotencyStore


_state: APIState | None = None


def init_state() -> APIState:
    global _state
    deps = create_app_dependencies()
    _state = APIState(deps=deps, idempotency_store=SQLiteIdempotencyStore())
    return _state


def get_state() -> APIState:
    if _state is None:
        return init_state()
    return _state


class _CompatDeps:
    """Dynamic deps proxy for backward compat with tests that patch app module attrs."""

    def __getattr__(self, name: str) -> Any:
        try:
            import case_api.api.v1.app as app_mod  # noqa: PLC0415

            if hasattr(app_mod, name):
                return getattr(app_mod, name)
        except Exception:
            pass
        return getattr(get_state().deps, name)


_compat_deps = _CompatDeps()


def get_deps() -> AppDependencies:
    return _compat_deps  # type: ignore[return-value]


def get_idempotency_store() -> SQLiteIdempotencyStore:
    # Backward compat: tests patch case_api.api.v1.app._idempotency_store
    try:
        import case_api.api.v1.app as app_mod  # noqa: PLC0415

        store = getattr(app_mod, "_idempotency_store", None)
        if store is not None:
            return cast(SQLiteIdempotencyStore, store)
    except Exception:
        pass
    return get_state().idempotency_store


def require_scope_in_strict(http_request: Request, required_scopes: list[str], correlation_id: str = "") -> None:
    """Enforce server-derived scopes in strict modes. Dev mode remains backward-compatible."""
    identity = getattr(http_request.state, "identity", None)
    security_mode = getattr(http_request.state, "security_mode", "dev")
    if security_mode not in ("shared", "prod"):
        return
    if identity is None:
        raise HTTPException(
            status_code=401,
            detail={"error": "Authentication required", "code": "AUTHENTICATION_REQUIRED", "correlation_id": correlation_id},
        )
    scopes = set(getattr(identity, "scopes", ()) or ())
    if not any(s in scopes for s in required_scopes):
        raise HTTPException(
            status_code=403,
            detail={
                "error": f"Missing required scope (any of): {required_scopes}",
                "code": "AUTHZ_SCOPE_MISSING",
                "correlation_id": correlation_id,
            },
        )


def generate_case_id() -> str:
    short = uuid.uuid4().hex[:8].upper()
    return f"CASE-{short}"


__all__ = [
    "VERSION",
    "VALID_EVIDENCE_TYPES",
    "VALID_URGENCY_LEVELS",
    "MAX_REPORT_LENGTH",
    "MAX_EVIDENCE_ITEMS",
    "MAX_EVIDENCE_CONTENT_LENGTH",
    "MAX_JUSTIFICATION_LENGTH",
    "APIState",
    "init_state",
    "get_state",
    "get_deps",
    "get_idempotency_store",
    "require_scope_in_strict",
    "generate_case_id",
]
