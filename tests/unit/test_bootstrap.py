"""Bootstrap and persistence resilience tests."""
from __future__ import annotations

import os
import sqlite3
import sys
import tempfile

import pytest

sys.path.insert(0, "src")


class TestDBBootstrap:
    def test_missing_db_creates_tables(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(db_path)
        try:
            from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository

            repo = SQLiteDecisionRepository(db_path=db_path)
            conn = sqlite3.connect(db_path)
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            assert "decisions" in tables
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_valid_db_opens(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        try:
            from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository

            repo = SQLiteDecisionRepository(db_path=db_path)
            assert os.path.exists(db_path)
            assert os.path.getsize(db_path) > 0
        finally:
            os.unlink(db_path)

    def test_zero_byte_db_reinitializes(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(db_path)
        open(db_path, "w").close()
        assert os.path.getsize(db_path) == 0
        try:
            from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository

            repo = SQLiteDecisionRepository(db_path=db_path)
            conn = sqlite3.connect(db_path)
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            assert "decisions" in tables
        finally:
            os.unlink(db_path)

    def test_missing_tables_reinitializes(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE unrelated (id TEXT)")
        conn.commit()
        conn.close()
        try:
            from case_infra.persistence.sqlite_decision_repository import SQLiteDecisionRepository

            repo = SQLiteDecisionRepository(db_path=db_path)
            conn2 = sqlite3.connect(db_path)
            tables = [r[0] for r in conn2.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn2.close()
            assert "decisions" in tables
        finally:
            os.unlink(db_path)


class TestAuditBootstrap:
    def test_missing_db_creates_tables(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(db_path)
        try:
            from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter

            adapter = SQLiteAuditAdapter(db_path=db_path)
            conn = sqlite3.connect(db_path)
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            assert "audit_events" in tables
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_zero_byte_db_reinitializes(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(db_path)
        open(db_path, "w").close()
        try:
            from case_infra.persistence.sqlite_audit import SQLiteAuditAdapter

            adapter = SQLiteAuditAdapter(db_path=db_path)
            conn = sqlite3.connect(db_path)
            tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
            conn.close()
            assert "audit_events" in tables
        finally:
            os.unlink(db_path)


class TestHealthEndpoint:
    def test_health_reports_db_status(self):
        from fastapi.testclient import TestClient

        from case_api.api.v1.app import app

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "db_path" in data
