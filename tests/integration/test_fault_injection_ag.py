"""Deterministic fault injection scenarios (A-G subset) for CASE integrity.

Test-only: uses CASE_TEST_FAULT_INJECTION hooks. Each test isolates state.
Scenarios A,C,G,E partially demonstrated; B,D,F require deeper harness coverage.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

os.environ.setdefault("CASE_PROVIDER", "mock")
sys.path.insert(0, "src")


def _setup_strict_app(tmp: str):
    import case_api.api.v1.app as appmod
    from case_api.api.v1.auth import APIKeyAuthMiddleware
    from case_api.api.v1.security import load_security_config
    from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
    from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository
    from case_infra.persistence.sqlite_idempotency import SQLiteIdempotencyStore

    dec_db = os.path.join(tmp, "decisions.db")
    aud_db = os.path.join(tmp, "audit.db")
    saved_env = os.environ.get("CASE_DB_PATH")
    saved = (
        appmod.decision_repo,
        appmod.audit_adapter,
        appmod.engine._decision_repository,
        appmod.engine._audit_port,
        appmod._idempotency_store,
        appmod.engine._provider,
        dict(getattr(appmod.engine, "_providers", {}) or {}),
        appmod.provider,
        dict(appmod.providers),
    )
    os.environ["CASE_DB_PATH"] = dec_db
    cfg = load_security_config(
        {
            "CASE_SECURITY_MODE": "shared",
            "CASE_API_KEYS": json.dumps({"k": {"consumer_id": "c1", "tenant_id": "t1", "scopes": ["case:evaluate"]}}),
        }
    )
    a = FastAPI()
    a.state.security_config = cfg
    a.add_middleware(APIKeyAuthMiddleware, config=cfg)
    a.post("/api/v1/evaluate")(appmod.evaluate_case)

    appmod.decision_repo = SQLiteDecisionRepository(dec_db)
    appmod.audit_adapter = SQLiteAuditAdapter(aud_db)
    appmod.engine._decision_repository = appmod.decision_repo
    appmod.engine._audit_port = appmod.audit_adapter
    appmod._idempotency_store = SQLiteIdempotencyStore(dec_db)

    def restore():
        (
            appmod.decision_repo,
            appmod.audit_adapter,
            appmod.engine._decision_repository,
            appmod.engine._audit_port,
            appmod._idempotency_store,
            appmod.engine._provider,
            eng_providers,
            appmod.provider,
            app_providers,
        ) = saved
        appmod.engine._providers = eng_providers
        appmod.providers = app_providers
        if saved_env is None:
            os.environ.pop("CASE_DB_PATH", None)
        else:
            os.environ["CASE_DB_PATH"] = saved_env

    return a, dec_db, aud_db, restore


def _body(idem="idem-fi", corr="corr-fi"):
    return {
        "contract_version": "case-eval/v0.1-draft",
        "capability_id": "case.evaluate",
        "correlation_id": corr,
        "idempotency_key": idem,
        "data_status": "synthetic",
        "payload": {
            "domain": "logistics",
            "summary": "Synthetic fault injection test",
            "urgency": "MEDIUM",
            "evidence": [{"id": "e1", "type": "text", "content": "synthetic", "source": "test", "confidence": 0.5}],
            "provider": "mock",
            "metadata": {"synthetic": "true"},
        },
    }


def _count(db, table):
    if not Path(db).exists():
        return 0
    conn = sqlite3.connect(db)
    try:
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is None:
            return 0
        return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    finally:
        conn.close()


@pytest.mark.integration
class TestFaultInjectionAG:
    def test_A_before_decision_persist_no_decision_and_retry_behavior(self):
        """A: failure before persisting decision -> no business decision persisted."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            os.environ["CASE_TEST_FAULT_INJECTION"] = "1"
            from case_core.fault_hooks import clear, set_hook
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                clear()
                set_hook("before_decision_persist", lambda: (_ for _ in ()).throw(RuntimeError("boom-A")))
                c = TestClient(app, raise_server_exceptions=False)
                c.post("/api/v1/evaluate", json=_body("idem-a"), headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") == 0
                clear()
                r2 = c.post("/api/v1/evaluate", json=_body("idem-a"), headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") <= 1
                if r2.status_code == 200 and (r2.json().get("status") not in ("error",)):
                    assert _count(dec_db, "decisions") == 1
            finally:
                clear()
                os.environ.pop("CASE_TEST_FAULT_INJECTION", None)
                restore()

    def test_C_before_idempotency_complete_leaves_no_duplicate_on_retry(self):
        """C-like: failure around idempotency completion after evaluation effects; retry must not duplicate decision."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            os.environ["CASE_TEST_FAULT_INJECTION"] = "1"
            from case_core.fault_hooks import clear, set_hook
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                clear()
                set_hook("before_idempotency_complete", lambda: (_ for _ in ()).throw(RuntimeError("boom-C")))
                c = TestClient(app)
                c.post("/api/v1/evaluate", json=_body("idem-c"), headers={"X-API-Key": "k"})
                decisions = _count(dec_db, "decisions")
                assert decisions <= 1
                clear()
                r2 = c.post("/api/v1/evaluate", json=_body("idem-c"), headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") == decisions
                assert r2.status_code in (200, 409)
            finally:
                clear()
                os.environ.pop("CASE_TEST_FAULT_INJECTION", None)
                restore()

    def test_E_provider_failure_no_valid_decision_persisted(self):
        """E: provider fails before producing valid decision -> no valid decision persisted."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                import case_api.api.v1.app as appmod

                class FailingProvider:
                    name = "mock"
                    model = "failing"
                    async def complete(self, request):
                        class Usage:
                            prompt_tokens = 0
                            completion_tokens = 0
                            total_tokens = 0
                        class R:
                            raw_output = ""
                            provider = "mock"
                            model = "failing"
                            finish_reason = "error"
                            latency_ms = 1.0
                            metadata = {"detail": "synthetic provider failure"}
                            usage = Usage()
                        return R()

                failing = FailingProvider()
                appmod.providers["mock"] = failing
                appmod.provider = failing
                appmod.engine._providers = dict(appmod.providers)
                appmod.engine._provider = failing

                c = TestClient(app, raise_server_exceptions=False)
                body = _body("idem-e")
                body["payload"]["provider"] = "mock"
                r = c.post("/api/v1/evaluate", json=body, headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") == 0
                assert r.status_code in (200, 422, 500)
            finally:
                restore()

    def test_G_before_response_return_persisted_state_no_duplicate_on_retry(self):
        """G: error before returning response after effects -> no duplicate on retry."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            os.environ["CASE_TEST_FAULT_INJECTION"] = "1"
            from case_core.fault_hooks import clear, set_hook
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                clear()
                set_hook("before_response_return", lambda: (_ for _ in ()).throw(RuntimeError("boom-G")))
                c = TestClient(app, raise_server_exceptions=False)
                c.post("/api/v1/evaluate", json=_body("idem-g"), headers={"X-API-Key": "k"})
                decisions = _count(dec_db, "decisions")
                assert decisions <= 1
                clear()
                r2 = c.post("/api/v1/evaluate", json=_body("idem-g"), headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") == decisions
                assert r2.status_code in (200, 409)
            finally:
                clear()
                os.environ.pop("CASE_TEST_FAULT_INJECTION", None)
                restore()
    def test_B_decision_persisted_then_audit_failure_no_duplicate_on_retry(self):
        """B: decision persisted, subsequent audit write fails; no duplicate decision on retry/recovery path."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            os.environ["CASE_TEST_FAULT_INJECTION"] = "1"
            from case_core.fault_hooks import clear, set_hook
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                import case_api.api.v1.app as appmod
                clear()
                state = {"armed": False}
                orig_log = appmod.audit_adapter.log_event

                async def flaky_log(event, security_context=None):
                    if state["armed"]:
                        raise RuntimeError("boom-B-audit-after-persist")
                    return await orig_log(event, security_context=security_context)

                def arm_audit_failure():
                    state["armed"] = True
                    appmod.audit_adapter.log_event = flaky_log
                    appmod.engine._audit_port = appmod.audit_adapter

                set_hook("after_decision_persist", arm_audit_failure)
                c = TestClient(app, raise_server_exceptions=False)
                c.post("/api/v1/evaluate", json=_body("idem-b"), headers={"X-API-Key": "k"})
                decisions = _count(dec_db, "decisions")
                assert decisions == 1  # decision persisted before audit failure
                # restore and retry same idempotent operation
                clear()
                appmod.audit_adapter.log_event = orig_log
                appmod.engine._audit_port = appmod.audit_adapter
                r2 = c.post("/api/v1/evaluate", json=_body("idem-b"), headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") == decisions
                assert r2.status_code in (200, 409)
            finally:
                clear()
                try:
                    import case_api.api.v1.app as appmod
                    # best-effort restore handled by outer restore; ensure hook cleared
                except Exception:
                    pass
                os.environ.pop("CASE_TEST_FAULT_INJECTION", None)
                restore()

    def test_D_interruption_after_persist_before_return_no_duplicate(self):
        """D: interruption after persist/idempotency completion but before returning response -> no duplicate on retry."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            os.environ["CASE_TEST_FAULT_INJECTION"] = "1"
            from case_core.fault_hooks import clear, set_hook
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                clear()
                # Decision and idempotency completion effects done; interruption before response delivery
                set_hook("after_idempotency_complete", lambda: (_ for _ in ()).throw(RuntimeError("boom-D-interrupt")))
                c = TestClient(app, raise_server_exceptions=False)
                c.post("/api/v1/evaluate", json=_body("idem-d"), headers={"X-API-Key": "k"})
                decisions = _count(dec_db, "decisions")
                assert decisions <= 1
                clear()
                r2 = c.post("/api/v1/evaluate", json=_body("idem-d"), headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") == decisions
                # completed idempotency should allow replay
                assert r2.status_code == 200
                assert r2.json().get("status") in ("ok", "pending_review")
            finally:
                clear()
                os.environ.pop("CASE_TEST_FAULT_INJECTION", None)
                restore()

    def test_F_transient_failure_then_retry_no_duplicate(self):
        """F: transient failure followed by retry on same idempotent operation -> no duplicate effects."""
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            app, dec_db, aud_db, restore = _setup_strict_app(tmp)
            try:
                import case_api.api.v1.app as appmod

                class FlakyProvider:
                    name = "mock"
                    model = "flaky"
                    def __init__(self):
                        self.calls = 0
                    async def complete(self, request):
                        self.calls += 1
                        if self.calls == 1:
                            class Usage:
                                prompt_tokens = 0
                                completion_tokens = 0
                                total_tokens = 0
                            class R:
                                raw_output = ""
                                provider = "mock"
                                model = "flaky"
                                finish_reason = "timeout"
                                latency_ms = 1.0
                                metadata = {"detail": "transient"}
                                usage = Usage()
                            return R()
                        # second call: succeed with valid mock-like JSON output
                        from case_core.providers.mock import MockProvider
                        return await MockProvider().complete(request)

                flaky = FlakyProvider()
                appmod.providers["mock"] = flaky
                appmod.provider = flaky
                appmod.engine._providers = dict(appmod.providers)
                appmod.engine._provider = flaky

                c = TestClient(app, raise_server_exceptions=False)
                body = _body("idem-f")
                body["payload"]["provider"] = "mock"
                r1 = c.post("/api/v1/evaluate", json=body, headers={"X-API-Key": "k"})
                # first attempt fails transiently; idempotency may be released -> retry can proceed
                r2 = c.post("/api/v1/evaluate", json=body, headers={"X-API-Key": "k"})
                assert _count(dec_db, "decisions") <= 1
                assert r1.status_code in (200, 409, 422, 500)
                assert r2.status_code in (200, 409, 422, 500)
            finally:
                restore()
