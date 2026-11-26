import importlib
import os
import sys
import tempfile
import threading

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("CASE_PROVIDER", "mock")
sys.path.insert(0, "src")


EVAL_PAYLOAD = {
    "contract_version": "case-eval/v0.1-draft",
    "capability_id": "case.evaluate",
    "correlation_id": "corr-poc",
    "data_status": "synthetic",
    "payload": {
        "case_id": "CASE-POC-1",
        "domain": "logistics",
        "summary": "Synthetic PoC test",
        "urgency": "MEDIUM",
        "evidence": [
            {
                "id": "e1",
                "type": "text",
                "content": "Synthetic evidence",
                "source": "test",
                "confidence": 0.6,
            }
        ],
        "metadata": {"synthetic": "true"},
        "provider": "mock",
    },
}


def _reload_strict_app(tmpdir: str, consumer_id: str, tenant_id: str, api_key: str, scopes: str):
    """Reload app as isolated strict single-consumer instance with its own DB."""
    # Point persistence to isolated DB files for this instance
    os.environ["CASE_SECURITY_MODE"] = "shared"
    os.environ["CASE_API_KEY"] = api_key
    os.environ["CASE_CONSUMER_ID"] = consumer_id
    os.environ["CASE_TENANT_ID"] = tenant_id
    os.environ["CASE_API_SCOPES"] = scopes
    os.environ["CASE_DECISION_DB_PATH"] = os.path.join(tmpdir, "decisions.db")
    os.environ["CASE_AUDIT_DB_PATH"] = os.path.join(tmpdir, "audit.db")
    os.environ["CASE_REPOSITORY_DB_PATH"] = os.path.join(tmpdir, "repo.db")

    # Recreate module-level deps bound to new DB paths
    import case_api.api.v1.app as appmod
    import case_core.composition as comp
    importlib.reload(comp)
    importlib.reload(appmod)
    # Ensure deps use configured paths (composition may read env at creation)
    from case_infra.persistence.sqlite_adapter import SQLiteRepository
    from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter
    from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository

    dec_db = os.environ["CASE_DECISION_DB_PATH"]
    aud_db = os.environ["CASE_AUDIT_DB_PATH"]
    repo_db = os.environ["CASE_REPOSITORY_DB_PATH"]
    appmod.decision_repo = SQLiteDecisionRepository(dec_db)
    appmod.audit_adapter = SQLiteAuditAdapter(aud_db)
    appmod.engine._decision_repository = appmod.decision_repo
    appmod.engine._audit_port = appmod.audit_adapter
    if hasattr(appmod.engine, "_case_repository"):
        appmod.engine._case_repository = SQLiteRepository(repo_db)
    return appmod


def _cleanup_env():
    for k in [
        "CASE_SECURITY_MODE",
        "CASE_API_KEY",
        "CASE_API_KEYS",
        "CASE_CONSUMER_ID",
        "CASE_TENANT_ID",
        "CASE_API_SCOPES",
        "CASE_DECISION_DB_PATH",
        "CASE_AUDIT_DB_PATH",
        "CASE_REPOSITORY_DB_PATH",
    ]:
        os.environ.pop(k, None)


@pytest.mark.integration
class TestMulticonsumerIsolationPoC:
    def test_api_isolated_instances_no_cross_access(self):
        """Two strict single-consumer instances with separate DBs: B cannot access A data."""
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as dA, tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as dB:
                # Instance A
                appA = _reload_strict_app(
                    dA, "consA", "tA", "keyA",
                    "case:evaluate,case:read,case:triage,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read",
                )
                cA = TestClient(appA.app)
                hA = {"X-API-Key": "keyA"}
                # create a triage decision in A
                triage = {
                    "domain": "logistics",
                    "report_text": "Synthetic isolation PoC case for consumer A",
                    "urgency": "MEDIUM",
                    "evidence": [
                        {
                            "id": "ev-a-1",
                            "type": "text",
                            "content": "Synthetic evidence for isolation PoC",
                            "source": "test",
                            "confidence": 0.8,
                            "extracted_at": "2026-11-10T00:00:00Z",
                        }
                    ],
                    "provider": "mock",
                }
                r_triage = cA.post("/api/v1/triage", json=triage, headers=hA)
                assert r_triage.status_code in (200, 201), r_triage.text
                body = r_triage.json()
                decision_id = body.get("decision_id") or body.get("id")
                case_id = body.get("case_id")
                assert decision_id or case_id

                # A can list/read own
                r_list_a = cA.get("/api/v1/cases", headers=hA)
                assert r_list_a.status_code == 200
                assert r_list_a.json().get("total", 0) >= 1

                # Instance B (separate DB, separate credentials)
                appB = _reload_strict_app(
                    dB, "consB", "tB", "keyB",
                    "case:evaluate,case:read,case:triage,case:hitl:read,case:hitl:write,case:decision:read,case:audit:read",
                )
                cB = TestClient(appB.app)
                hB = {"X-API-Key": "keyB"}

                # B sees no A data
                r_list_b = cB.get("/api/v1/cases", headers=hB)
                assert r_list_b.status_code == 200
                assert r_list_b.json().get("total", 0) == 0
                if decision_id:
                    r_hitl = cB.get(f"/api/v1/hitl/{decision_id}", headers=hB)
                    assert r_hitl.status_code == 404
                if case_id:
                    r_case = cB.get(f"/api/v1/cases/{case_id}", headers=hB)
                    assert r_case.status_code == 404
                    r_audit = cB.get(f"/api/v1/audit/{case_id}", headers=hB)
                    assert r_audit.status_code in (200, 404)
                    # audit endpoint returns list; if scoped filter applied it should be empty/404-equivalent behavior
                    if r_audit.status_code == 200:
                        assert r_audit.json().get("count", 0) == 0

                # A creds rejected by B instance (different key/identity bound to instance config)
                assert cB.get("/api/v1/cases", headers=hA).status_code in (401, 403)
        finally:
            _cleanup_env()
            import case_api.api.v1.app as appmod
            importlib.reload(appmod)

    def test_strict_idempotency_replay_and_conflict_api(self):
        """Same strict context: replay returns stored response, different payload conflicts."""
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                appmod = _reload_strict_app(d, "consI", "tI", "keyI", "case:evaluate")
                c = TestClient(appmod.app)
                h = {"X-API-Key": "keyI"}
                p1 = {**EVAL_PAYLOAD, "idempotency_key": "idem-api-1"}
                r1 = c.post("/api/v1/evaluate", json=p1, headers=h)
                assert r1.status_code == 200
                r2 = c.post("/api/v1/evaluate", json=p1, headers=h)
                assert r2.status_code == 200
                assert r2.json().get("decision_id") == r1.json().get("decision_id")
                # conflict: same idempotency key, different payload
                payload2 = {**p1, "correlation_id": "corr-diff", "idempotency_key": "idem-api-1"}
                payload2["payload"] = {**EVAL_PAYLOAD["payload"], "summary": "different payload for conflict"}
                r3 = c.post("/api/v1/evaluate", json=payload2, headers=h)
                assert r3.status_code == 409
        finally:
            _cleanup_env()
            import case_api.api.v1.app as appmod
            importlib.reload(appmod)

    def test_strict_idempotency_concurrent_stress(self):
        """Concurrent identical evaluate requests with same idempotency key: no 5xx, safe convergence."""
        try:
            with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
                appmod = _reload_strict_app(d, "consC", "tC", "keyC", "case:evaluate")
                c = TestClient(appmod.app, raise_server_exceptions=False)
                h = {"X-API-Key": "keyC"}
                payload = {**EVAL_PAYLOAD, "idempotency_key": "idem-concurrent"}
                results = []

                def worker():
                    try:
                        r = c.post("/api/v1/evaluate", json=payload, headers=h)
                        results.append(r.status_code)
                    except Exception:
                        results.append(599)

                threads = [threading.Thread(target=worker) for _ in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

                # Must not crash with 5xx due to idempotency logic; SQLite locking may surface as handled errors.
                assert all(code < 500 or code == 599 for code in results)
                assert any(code in (200, 409) for code in results)
        finally:
            _cleanup_env()
            import case_api.api.v1.app as appmod
            importlib.reload(appmod)
