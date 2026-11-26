"""API key authentication middleware for FastAPI.

Secures API endpoints with constant-time key comparison.
When CASE_API_KEY is unset, authentication is disabled (open access for development).
When set, only X-API-Key or Authorization: Bearer headers are accepted.
"""
from __future__ import annotations

import hmac
import logging
import os
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("case.auth")


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """API key authentication middleware.

    Uses constant-time comparison to prevent timing attacks.
    Query-string API keys are rejected for security.
    Health check and docs endpoints are always allowed.
    """

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/"}

    def __init__(self, app: Any, api_key: str | None = None) -> None:
        super().__init__(app)
        self._api_key = api_key or os.environ.get("CASE_API_KEY", "")

    @property
    def is_configured(self) -> bool:
        """Whether authentication is configured (key is set)."""
        return bool(self._api_key)

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)  # type: ignore[no-any-return]

        if not self._api_key:
            return await call_next(request)  # type: ignore[no-any-return]

        provided_key = self._extract_api_key(request)
        if not self._constant_time_compare(provided_key, self._api_key):
            client_ip = request.client.host if request.client else "unknown"
            logger.warning("Auth failure from %s for %s %s", client_ip, request.method, request.url.path)
            return Response(
                content='{"error": "Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)  # type: ignore[no-any-return]

    def _extract_api_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return api_key

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        return ""

    @staticmethod
    def _constant_time_compare(val1: str, val2: str) -> bool:
        """Constant-time string comparison to prevent timing attacks."""
        return hmac.compare_digest(val1.encode(), val2.encode())
