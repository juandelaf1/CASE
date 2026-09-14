from __future__ import annotations

import os
import sys
import tempfile

from fastapi.testclient import TestClient

sys.path.insert(0, "src")
from case_api.api.v1.app import app

client = TestClient(app)


def _fresh_client() -> TestClient:
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    old = os.environ.get("CASE_DB_PATH")
    os.environ["CASE_DB_PATH"] = db_path
    try:
        import importlib

        import case_api.api.v1.app as app_mod
        import case_core.composition as comp_mod
        importlib.reload(comp_mod)
        importlib.reload(app_mod)
        return TestClient(app_mod.app), db_path
    except Exception:
        os.unlink(db_path)
        if old is not None:
            os.environ["CASE_DB_PATH"] = old
        else:
            os.environ.pop("CASE_DB_PATH", None)
        raise


class TestCaseIdGeneration:
    def test_auto_generated_when_omitted(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "Test auto-generated case ID",
                "domain": "urban_operations",
                "urgency": "LOW",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
            case_id = response.json()["case_id"]
            assert case_id.startswith("CASE-")
            assert len(case_id) == 13
        finally:
            os.unlink(db)

    def test_unique_across_requests(self):
        c, db = _fresh_client()
        try:
            ids = set()
            for _ in range(5):
                request = {
                    "report_text": "Uniqueness test",
                    "domain": "urban_operations",
                    "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
                }
                response = c.post("/api/v1/triage", json=request)
                assert response.status_code == 200
                ids.add(response.json()["case_id"])
            assert len(ids) == 5
        finally:
            os.unlink(db)

    def test_explicit_case_id_preserved(self):
        c, db = _fresh_client()
        try:
            request = {
                "case_id": "MY-CUSTOM-ID",
                "report_text": "Test explicit case ID",
                "domain": "urban_operations",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
            assert response.json()["case_id"] == "MY-CUSTOM-ID"
        finally:
            os.unlink(db)


class TestExternalReference:
    def test_returned_in_response(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "Test external reference",
                "domain": "urban_operations",
                "external_reference": "TICKET-2026-001",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
            assert response.json()["external_reference"] == "TICKET-2026-001"
        finally:
            os.unlink(db)

    def test_none_when_not_provided(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "Test no external reference",
                "domain": "urban_operations",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
            assert response.json()["external_reference"] is None
        finally:
            os.unlink(db)


class TestReportValidation:
    def test_empty_report_rejected(self):
        response = client.post("/api/v1/triage", json={"report_text": "", "domain": "urban_operations"})
        assert response.status_code == 422

    def test_whitespace_only_report_rejected(self):
        response = client.post("/api/v1/triage", json={"report_text": "   \n\t  ", "domain": "urban_operations"})
        assert response.status_code == 422

    def test_report_too_long_rejected(self):
        response = client.post("/api/v1/triage", json={"report_text": "x" * 50001, "domain": "urban_operations"})
        assert response.status_code == 422

    def test_report_at_max_length_accepted(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "x" * 50000,
                "domain": "urban_operations",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
        finally:
            os.unlink(db)


class TestDomainValidation:
    def test_valid_domain_accepted(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "Valid domain test",
                "domain": "urban_operations",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
        finally:
            os.unlink(db)

    def test_unknown_domain_rejected(self):
        response = client.post("/api/v1/triage", json={"report_text": "Test", "domain": "nonexistent"})
        assert response.status_code == 400

    def test_empty_domain_rejected(self):
        response = client.post("/api/v1/triage", json={"report_text": "Test", "domain": ""})
        assert response.status_code == 422


class TestUrgencyValidation:
    def test_valid_urgency_levels(self):
        c, db = _fresh_client()
        try:
            for level in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]:
                request = {
                    "report_text": f"Urgency test {level}",
                    "domain": "urban_operations",
                    "urgency": level,
                    "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
                }
                response = c.post("/api/v1/triage", json=request)
                assert response.status_code == 200
        finally:
            os.unlink(db)

    def test_invalid_urgency_rejected(self):
        response = client.post("/api/v1/triage", json={"report_text": "Test", "domain": "urban_operations", "urgency": "INVALID"})
        assert response.status_code == 422

    def test_default_urgency_is_medium(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "Default urgency test",
                "domain": "urban_operations",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Ev", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
            assert response.json()["reported_urgency"] == "MEDIUM"
        finally:
            os.unlink(db)


class TestEvidenceValidation:
    def test_valid_evidence_accepted(self):
        c, db = _fresh_client()
        try:
            request = {
                "report_text": "Evidence test",
                "domain": "urban_operations",
                "evidence": [{"id": "ev-1", "type": "text", "content": "Valid", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
            }
            response = c.post("/api/v1/triage", json=request)
            assert response.status_code == 200
        finally:
            os.unlink(db)

    def test_invalid_evidence_type_rejected(self):
        response = client.post("/api/v1/triage", json={
            "report_text": "Test",
            "domain": "urban_operations",
            "evidence": [{"id": "ev-1", "type": "bad", "content": "X", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
        })
        assert response.status_code == 422

    def test_empty_evidence_content_rejected(self):
        response = client.post("/api/v1/triage", json={
            "report_text": "Test",
            "domain": "urban_operations",
            "evidence": [{"id": "ev-1", "type": "text", "content": "", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"}],
        })
        assert response.status_code == 422

    def test_confidence_out_of_range_rejected(self):
        response = client.post("/api/v1/triage", json={
            "report_text": "Test",
            "domain": "urban_operations",
            "evidence": [{"id": "ev-1", "type": "text", "content": "X", "source": "t", "confidence": 1.5, "extracted_at": "2026-09-14T12:00:00Z"}],
        })
        assert response.status_code == 422

    def test_negative_confidence_rejected(self):
        response = client.post("/api/v1/triage", json={
            "report_text": "Test",
            "domain": "urban_operations",
            "evidence": [{"id": "ev-1", "type": "text", "content": "X", "source": "t", "confidence": -0.1, "extracted_at": "2026-09-14T12:00:00Z"}],
        })
        assert response.status_code == 422

    def test_too_many_evidence_items_rejected(self):
        response = client.post("/api/v1/triage", json={
            "report_text": "Test",
            "domain": "urban_operations",
            "evidence": [{"id": f"ev-{i}", "type": "text", "content": f"E{i}", "source": "t", "confidence": 0.9, "extracted_at": "2026-09-14T12:00:00Z"} for i in range(11)],
        })
        assert response.status_code == 422


class TestVersionConsistency:
    def test_version_matches_pyproject(self):
        import tomllib
        from pathlib import Path

        pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        expected_version = data["project"]["version"]

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["version"] == expected_version

    def test_version_module_reads_correctly(self):
        from case_core.version import VERSION

        assert VERSION
        assert VERSION != "0.0.0"

    def test_fastapi_version_matches(self):
        from case_core.version import VERSION

        assert app.version == VERSION
