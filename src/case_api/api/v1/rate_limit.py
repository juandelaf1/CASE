"""Rate limiting middleware for FastAPI.

Provides per-client IP rate limiting with configurable limits.
Health check and docs endpoints are always allowed.
"""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from typing import Any

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger("case.ratelimit")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiting middleware.

    Uses a sliding window counter per client IP.
    When CASE_RATE_LIMIT is unset, rate limiting is disabled (open for development).
    When set, only requests within the limit are allowed.
    """

    EXEMPT_PATHS = {"/health", "/docs", "/openapi.json", "/redoc", "/", "/api/v1/seismic/health"}

    def __init__(self, app: Any, max_requests_per_second: int | None = None) -> None:
        super().__init__(app)
        env_val = os.environ.get("CASE_RATE_LIMIT", "")
        if max_requests_per_second is not None:
            self._max_rps = max_requests_per_second
        elif env_val:
            self._max_rps = int(env_val)
        else:
            self._max_rps = 0  # disabled

        self._requests: dict[str, list[float]] = defaultdict(list)
        self._window_seconds = 60.0
        self._cleanup_interval = 60.0
        self._last_cleanup = time.time()

    @property
    def is_configured(self) -> bool:
        return self._max_rps > 0

    def _cleanup_old_entries(self, client_ip: str) -> None:
        now = time.time()
        if now - self._last_cleanup > self._cleanup_interval:
            self._last_cleanup = now
        cutoff = now - self._window_seconds
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > cutoff
        ]

    def _is_rate_limited(self, client_ip: str) -> bool:
        if self._max_rps <= 0:
            return False

        self._cleanup_old_entries(client_ip)
        now = time.time()
        cutoff = now - self._window_seconds
        self._requests[client_ip] = [
            ts for ts in self._requests[client_ip] if ts > cutoff
        ]

        max_requests = int(self._max_rps * self._window_seconds)
        if len(self._requests[client_ip]) >= max_requests:
            return True

        self._requests[client_ip].append(now)
        return False

    def get_usage(self, client_ip: str) -> dict[str, Any]:
        self._cleanup_old_entries(client_ip)
        now = time.time()
        cutoff = now - self._window_seconds
        current = sum(1 for ts in self._requests.get(client_ip, []) if ts > cutoff)
        max_requests = int(self._max_rps * self._window_seconds) if self._max_rps > 0 else 0
        return {
            "client_ip": client_ip,
            "current_requests": current,
            "max_requests": max_requests,
            "window_seconds": self._window_seconds,
            "is_configured": self.is_configured,
        }

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        if request.url.path in self.EXEMPT_PATHS:
            return await call_next(request)  # type: ignore[no-any-return]

        if not self.is_configured:
            return await call_next(request)  # type: ignore[no-any-return]

        client_ip = request.client.host if request.client else "unknown"

        if self._is_rate_limited(client_ip):
            logger.warning("Rate limit exceeded for %s", client_ip)
            return Response(
                content='{"error": "Rate limit exceeded. Please try again later."}',
                status_code=429,
                media_type="application/json",
            )

        return await call_next(request)  # type: ignore[no-any-return]
