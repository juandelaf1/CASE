"""API key authentication middleware for FastAPI.

Security modes (CASE_SECURITY_MODE): dev | shared | prod
- dev: open access allowed only when no credentials are configured (explicit dev mode).
- shared/prod: fail-closed; credentials required; identity/scopes derived server-side.

In strict modes, multi-consumer/multi-tenant operation is blocked at startup when
persistence/idempotency isolation is not demonstrated.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from case_api.api.v1.security import SecurityConfig, load_security_config

logger = logging.getLogger("case.auth")


def _json_error(status: int, error: str, code: str | None = None) -> Response:
    payload = {"error": error}
    if code:
        payload["code"] = code
    return Response(content=json.dumps(payload), status_code=status, media_type="application/json")


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware with explicit security modes."""

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/"}

    def __init__(self, app: Any, api_key: str | None = None, config: SecurityConfig | None = None) -> None:
        super().__init__(app)
        if config is not None:
            self._config = config
        else:
            # Backward-compatible construction path (tests/tools may pass api_key)
            env = None
            if api_key is not None:
                import os

                env = dict(os.environ)
                env["CASE_API_KEY"] = api_key
                env.setdefault("CASE_SECURITY_MODE", "dev")
            self._config = load_security_config(env)

    @property
    def config(self) -> SecurityConfig:
        return self._config

    @property
    def is_configured(self) -> bool:
        return self._config.has_credentials

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            request.state.security_mode = self._config.mode
            request.state.identity = None
            return await call_next(request)  # type: ignore[no-any-return]

        # Dev open access (explicit dev mode, no credentials configured)
        if self._config.dev_open_access:
            request.state.security_mode = self._config.mode
            request.state.identity = None
            return await call_next(request)  # type: ignore[no-any-return]

        # Strict/shared/prod: credentials required
        if self._config.is_strict and not self._config.has_credentials:
            return _json_error(503, "Security configuration missing for strict mode", "AUTH_CONFIG_MISSING")

        provided_key = self._extract_api_key(request)
        if not provided_key:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning("Missing credentials from %s for %s %s", client_ip, request.method, request.url.path)
            return _json_error(401, "Invalid or missing API key", "AUTHENTICATION_REQUIRED")

        identity = self._resolve_identity(provided_key)
        if identity is None:
            client_ip = request.client.host if request.client else "unknown"
            logger.warning("Auth failure from %s for %s %s", client_ip, request.method, request.url.path)
            return _json_error(401, "Invalid or missing API key", "AUTHENTICATION_FAILED")

        if not getattr(identity, "active", True):
            client_ip = request.client.host if request.client else "unknown"
            logger.warning("Revoked credentials from %s for %s %s", client_ip, request.method, request.url.path)
            return _json_error(403, "Consumer credentials revoked or inactive", "AUTHZ_CONSUMER_REVOKED")

        request.state.security_mode = self._config.mode
        request.state.identity = identity
        # Build verified security context for downstream authorization/isolation
        try:
            from case_core.contracts.security import SecurityContext

            request.state.security_context = SecurityContext(
                consumer_id=identity.consumer_id,
                tenant_id=identity.tenant_id,
                organization_id=identity.organization_id,
                organizations=getattr(identity, "organizations", ()),
                scopes=tuple(getattr(identity, "scopes", ())),
                principal_id=identity.consumer_id,
                credential_status="active" if getattr(identity, "active", True) else "revoked",
                restrictions=getattr(identity, "restrictions", {}) or {},
                correlation_id=request.headers.get("X-Correlation-Id") or request.headers.get("X-Request-Id"),
                mode=self._config.mode,
            )
        except Exception:
            request.state.security_context = None
        return await call_next(request)  # type: ignore[no-any-return]

    def _extract_api_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return api_key
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]
        return ""

    def _resolve_identity(self, provided_key: str) -> Any:
        provided_hash = hashlib.sha256(provided_key.encode("utf-8")).hexdigest()
        for key_hash, identity in self._config.consumers_by_key_hash.items():
            if hmac.compare_digest(provided_hash, key_hash):
                return identity
        return None

    @staticmethod
    def _constant_time_compare(val1: str, val2: str) -> bool:
        return hmac.compare_digest(val1.encode(), val2.encode())
