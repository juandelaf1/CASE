"""Simple API key authentication middleware for FastAPI.

For portfolio demonstration. In production, use JWT with proper key management.
"""
from __future__ import annotations

import os
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Simple API key authentication middleware.

    Checks for API key in X-API-Key header or Authorization: Bearer <key> header.
    Health check and docs endpoints are always allowed.
    """

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/"}

    def __init__(self, app: Any, api_key: str | None = None) -> None:
        super().__init__(app)
        self._api_key = api_key or os.environ.get("CASE_API_KEY", "")

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)

        if not self._api_key:
            return await call_next(request)

        provided_key = self._extract_api_key(request)
        if provided_key != self._api_key:
            return Response(
                content='{"error": "Invalid or missing API key"}',
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)

    def _extract_api_key(self, request: Request) -> str:
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            return api_key

        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:]

        api_key = request.query_params.get("api_key", "")
        return api_key
