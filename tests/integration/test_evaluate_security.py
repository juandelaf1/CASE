import importlib
import os
import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CASE_PROVIDER", "mock")
sys.path.insert(0, "src")


def _make_shared_app(env: dict[str, str], include_routes: bool = False):
    # import endpoint handlers from existing app module (reuses engine/deps)
    import case_api.api.v1.app as appmod
    from case_api.api.v1.auth import APIKeyAuthMiddleware
    from case_api.api.v1.security import load_security_config

    cfg = load_security_config(env)
    a = FastAPI()
    a.state.security_config = cfg
    a.add_middleware(APIKeyAuthMiddleware, config=cfg)
    a.post("/api/v1/evaluate")(appmod.evaluate_case)
    if include_routes:
        # Representative business/read routes to verify auth coverage in strict mode
        a.post("/api/v1/triage")(appmod.triage)
        a.get("/api/v1/cases")(appmod.list_cases)
        a.get("/api/v1/hitl/pending")(appmod.list_pending_review)
        a.get("/health")(appmod.health)
    return a, cfg


def _eval_payload(correlation_id="corr-sec", tenant_id=None, org_id=None, scopes=None, idempotency_key=None):
    body = {
        "contract_version": "case-eval/v0.1-draft",
        "capability_id": "case.evaluate",
        "correlation_id": correlation_id,
        "data_status": "synthetic",
        "payload": {
            "case_id": "CASE-SEC-1",
            "domain": "logistics",
            "summary": "Synthetic security test",
            "urgency": "MEDIUM",
            "evidence": [{"id": "e1", "type": "text", "content": "Synthetic", "source": "test", "confidence": 0.6}],
            "metadata": {"synthetic": "true"},
            "provider": "mock",
        },
    }
    if tenant_id is not None:
        body["tenant_context"] = {"tenant_id": tenant_id}
    if org_id is not None:
        body["organization_context"] = {"organization_id": org_id}
    if scopes is not None:
        body["scopes"] = scopes
    if idempotency_key is not None:
        body["idempotency_key"] = idempotency_key
    return body


class TestCaseEvaluateSecurityHardening:
    def test_shared_mode_no_credentials_fails_closed_startup(self):
        from case_api.api.v1.security import load_security_config

        with pytest.raises(RuntimeError):
            load_security_config({"CASE_SECURITY_MODE": "shared"})
        with pytest.raises(RuntimeError):
            load_security_config({"CASE_SECURITY_MODE": "prod"})

    def test_no_credentials_rejected_in_shared(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-valid",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:evaluate",
            }
        )
        c = TestClient(app)
        r = c.post("/api/v1/evaluate", json=_eval_payload())
        assert r.status_code == 401

    def test_invalid_credentials_rejected(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-valid",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:evaluate",
            }
        )
        c = TestClient(app)
        r = c.post(
            "/api/v1/evaluate",
            json=_eval_payload(),
            headers={"X-API-Key": "wrong"},
        )
        assert r.status_code == 401

    def test_missing_required_scope_rejected(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-noscope",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "other:scope",
            }
        )
        c = TestClient(app)
        r = c.post(
            "/api/v1/evaluate",
            json=_eval_payload(),
            headers={"X-API-Key": "k-noscope"},
        )
        assert r.status_code == 403
        detail = r.json().get("detail", {})
        assert detail.get("code") == "AUTHZ_SCOPE_MISSING"

    def test_wrong_scope_rejected(self):
        # Equivalent negative case: credential has unrelated scope, not case:evaluate
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-wrong",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:read",
            }
        )
        c = TestClient(app)
        r = c.post(
            "/api/v1/evaluate",
            json=_eval_payload(),
            headers={"X-API-Key": "k-wrong"},
        )
        assert r.status_code == 403

    def test_valid_scope_accepted(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-ok",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:evaluate",
            }
        )
        c = TestClient(app)
        r = c.post(
            "/api/v1/evaluate",
            json=_eval_payload(),
            headers={"X-API-Key": "k-ok"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body.get("status") in ("ok", "pending_review")

    def test_tenant_spoofing_rejected(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-ok",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:evaluate",
            }
        )
        c = TestClient(app)
        r = c.post(
            "/api/v1/evaluate",
            json=_eval_payload(tenant_id="spoofed-tenant"),
            headers={"X-API-Key": "k-ok"},
        )
        assert r.status_code == 403
        assert r.json().get("detail", {}).get("code") in ("AUTHZ_TENANT_MISMATCH", "AUTHZ_TENANT_NOT_ALLOWED")

    def test_cross_consumer_access_and_idempotency_collision_prevented_fail_closed(self):
        # Current persistence/audit/idempotency isolation is not demonstrated.
        # Shared/prod must fail closed for multi-consumer/multi-tenant configs.
        from case_api.api.v1.security import load_security_config

        multi = {
            "CASE_SECURITY_MODE": "shared",
            "CASE_API_KEYS": '{"k1":{"consumer_id":"c1","tenant_id":"t1","scopes":["case:evaluate"]},"k2":{"consumer_id":"c2","tenant_id":"t2","scopes":["case:evaluate"]}}',
        }
        with pytest.raises(RuntimeError):
            load_security_config(multi)

    def test_same_consumer_same_context_idempotent_request_handling(self):
        # Evaluate endpoint is recommendation-only and stateless in response mapping;
        # same consumer/context with same idempotency key must be accepted consistently.
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-ok",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:evaluate",
            }
        )
        c = TestClient(app)
        body = _eval_payload(idempotency_key="idem-same")
        h = {"X-API-Key": "k-ok"}
        r1 = c.post("/api/v1/evaluate", json=body, headers=h)
        r2 = c.post("/api/v1/evaluate", json=body, headers=h)
        assert r1.status_code == 200 and r2.status_code == 200
        assert r1.json().get("idempotency_key") == "idem-same"
        assert r2.json().get("idempotency_key") == "idem-same"

    def test_revoked_consumer_rejected(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEYS": '{"k-rev":{"consumer_id":"c1","tenant_id":"t1","scopes":["case:evaluate"],"active":false}}',
            }
        )
        c = TestClient(app)
        r = c.post("/api/v1/evaluate", json=_eval_payload(), headers={"X-API-Key": "k-rev"})
        assert r.status_code == 403
        assert r.json().get("code") == "AUTHZ_CONSUMER_REVOKED"

    def test_shared_mode_protects_other_business_routes_fail_closed(self):
        app, _ = _make_shared_app(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-ok",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:evaluate,case:read,case:hitl:read,case:hitl:write,case:triage",
            },
            include_routes=True,
        )
        c = TestClient(app)
        # No credentials -> business routes rejected; health exempt
        assert c.post("/api/v1/triage", json={}).status_code == 401
        assert c.get("/api/v1/cases").status_code == 401
        assert c.get("/api/v1/hitl/pending").status_code == 401
        assert c.get("/health").status_code == 200
        # Valid credentials with appropriate scopes -> authenticated access reaches handlers.
        # We assert authz passed (not 401/403); handler outcomes may depend on local data/state.
        h = {"X-API-Key": "k-ok"}
        c_ok = TestClient(app, raise_server_exceptions=False)
        assert c_ok.get("/api/v1/cases", headers=h).status_code not in (401, 403)
        assert c_ok.get("/api/v1/hitl/pending", headers=h).status_code not in (401, 403)

    def test_dev_mode_explicit_allows_local_autonomous_flow(self, monkeypatch):
        # Explicit dev mode: open access allowed without credentials for local use.
        monkeypatch.delenv("CASE_API_KEY", raising=False)
        monkeypatch.delenv("CASE_API_KEYS", raising=False)
        monkeypatch.setenv("CASE_SECURITY_MODE", "dev")
        import case_api.api.v1.app as appmod

        importlib.reload(appmod)
        c = TestClient(appmod.app)
        r = c.post("/api/v1/evaluate", json=_eval_payload(scopes=["case:evaluate"]))
        assert r.status_code == 200
        # restore default dev app state for other tests
        monkeypatch.delenv("CASE_SECURITY_MODE", raising=False)
        importlib.reload(appmod)


class TestStrictScopeCoverageAdditionalRoutes:
    def _app(self, scopes: str = "case:hitl:write"):
        import case_api.api.v1.app as appmod
        from case_api.api.v1.auth import APIKeyAuthMiddleware
        from case_api.api.v1.security import load_security_config

        cfg = load_security_config(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-ro",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": scopes,  # intentionally insufficient for read/compare routes
            }
        )
        a = FastAPI()
        a.state.security_config = cfg
        a.add_middleware(APIKeyAuthMiddleware, config=cfg)
        a.get("/domains")(appmod.list_domains)
        a.get("/api/v1/providers")(appmod.list_providers)
        a.post("/api/v1/comparison")(appmod.compare)
        a.get("/api/v1/seismic/events")(appmod.get_seismic_events)
        a.get("/api/v1/seismic/health")(appmod.seismic_health)
        return a

    def test_missing_credentials_rejected_on_additional_routes(self):
        c = TestClient(self._app())
        assert c.get("/domains").status_code == 401
        assert c.get("/api/v1/providers").status_code == 401
        assert c.post("/api/v1/comparison", json={}).status_code == 401
        assert c.get("/api/v1/seismic/events").status_code == 401
        assert c.get("/api/v1/seismic/health").status_code == 401

    def test_wrong_scope_rejected_on_additional_routes(self):
        c = TestClient(self._app(scopes="case:hitl:write"))
        h = {"X-API-Key": "k-ro"}
        # case:hitl:write is insufficient for read/compare-scoped routes
        assert c.get("/domains", headers=h).status_code == 403
        assert c.get("/api/v1/providers", headers=h).status_code == 403
        assert c.post(
            "/api/v1/comparison",
            json={"report_text": "synthetic", "domain": "logistics", "providers": [], "evidence": []},
            headers=h,
        ).status_code == 403
        assert c.get("/api/v1/seismic/events", headers=h).status_code == 403
        assert c.get("/api/v1/seismic/health", headers=h).status_code == 403

    def test_comparison_scope_allows_compare_only_identity(self):
        # Minimal identity with compare scope should pass authz (handler may fail validation, but not 401/403)
        import case_api.api.v1.app as appmod
        from case_api.api.v1.auth import APIKeyAuthMiddleware
        from case_api.api.v1.security import load_security_config

        cfg = load_security_config(
            {
                "CASE_SECURITY_MODE": "shared",
                "CASE_API_KEY": "k-cmp",
                "CASE_CONSUMER_ID": "c1",
                "CASE_TENANT_ID": "t1",
                "CASE_API_SCOPES": "case:compare",
            }
        )
        a = FastAPI()
        a.state.security_config = cfg
        a.add_middleware(APIKeyAuthMiddleware, config=cfg)
        a.post("/api/v1/comparison")(appmod.compare)
        c = TestClient(a, raise_server_exceptions=False)
        r = c.post("/api/v1/comparison", json={"report_text": "x", "domain": "logistics"}, headers={"X-API-Key": "k-cmp"})
        assert r.status_code not in (401, 403)
