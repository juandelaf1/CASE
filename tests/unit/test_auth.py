"""Tests for API key authentication middleware."""
from __future__ import annotations

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from case_api.api.v1.auth import APIKeyAuthMiddleware


def _create_app(api_key: str = "") -> FastAPI:
    app = FastAPI()
    app.add_middleware(APIKeyAuthMiddleware, api_key=api_key)

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/docs")
    async def docs() -> dict[str, str]:
        return {"docs": "page"}

    @app.get("/api/v1/triage")
    async def triage() -> dict[str, str]:
        return {"result": "ok"}

    @app.get("/api/v1/cases")
    async def cases() -> dict[str, str]:
        return {"cases": []}

    return app


class TestAuthDisabled:
    async def test_no_key_allows_all(self) -> None:
        app = _create_app(api_key="")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/triage")
            assert resp.status_code == 200

    async def test_health_exempt(self) -> None:
        app = _create_app(api_key="secret")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/health")
            assert resp.status_code == 200

    async def test_docs_exempt(self) -> None:
        app = _create_app(api_key="secret")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/docs")
            assert resp.status_code == 200


class TestAuthEnabled:
    async def test_valid_x_api_key(self) -> None:
        app = _create_app(api_key="test-secret-key")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/triage", headers={"X-API-Key": "test-secret-key"})
            assert resp.status_code == 200

    async def test_valid_bearer_token(self) -> None:
        app = _create_app(api_key="test-secret-key")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/triage", headers={"Authorization": "Bearer test-secret-key"})
            assert resp.status_code == 200

    async def test_invalid_key_returns_401(self) -> None:
        app = _create_app(api_key="test-secret-key")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/triage", headers={"X-API-Key": "wrong-key"})
            assert resp.status_code == 401
            assert "error" in resp.json()

    async def test_missing_key_returns_401(self) -> None:
        app = _create_app(api_key="test-secret-key")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/triage")
            assert resp.status_code == 401

    async def test_query_string_rejected(self) -> None:
        app = _create_app(api_key="test-secret-key")
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.get("/api/v1/triage?api_key=test-secret-key")
            assert resp.status_code == 401

    async def test_constant_time_compare(self) -> None:
        assert APIKeyAuthMiddleware._constant_time_compare("abc", "abc") is True
        assert APIKeyAuthMiddleware._constant_time_compare("abc", "def") is False
        assert APIKeyAuthMiddleware._constant_time_compare("", "") is True

    async def test_is_configured_property(self) -> None:
        app = _create_app(api_key="secret")
        assert APIKeyAuthMiddleware(app=app, api_key="secret").is_configured is True
        assert APIKeyAuthMiddleware(app=app, api_key="").is_configured is False
