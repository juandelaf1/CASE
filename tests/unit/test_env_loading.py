import os
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "src")

from dotenv import load_dotenv


class TestEnvLoading:
    """Tests for .env file loading and environment variable precedence."""

    def test_load_dotenv_from_project_root(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("CASE_TEST_VAR=from_dotenv\n")

        loaded = load_dotenv(env_file, override=False)
        assert loaded is True
        assert os.environ.get("CASE_TEST_VAR") == "from_dotenv"

        del os.environ["CASE_TEST_VAR"]

    def test_env_var_takes_precedence_over_dotenv(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("CASE_TEST_PRECEDENCE=from_dotenv\n")

        os.environ["CASE_TEST_PRECEDENCE"] = "from_env"

        loaded = load_dotenv(env_file, override=False)
        assert loaded is True
        assert os.environ["CASE_TEST_PRECEDENCE"] == "from_env"

        del os.environ["CASE_TEST_PRECEDENCE"]

    def test_missing_dotenv_does_not_crash(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        loaded = load_dotenv(env_file, override=False)
        assert loaded is False

    def test_dotenv_does_not_override_existing_env(self, tmp_path: Path) -> None:
        env_file = tmp_path / ".env"
        env_file.write_text("CASE_GROQ_API_KEY=dotenv_value\n")

        os.environ["CASE_GROQ_API_KEY"] = "env_value"

        load_dotenv(env_file, override=False)
        assert os.environ["CASE_GROQ_API_KEY"] == "env_value"

        del os.environ["CASE_GROQ_API_KEY"]

    def test_mock_provider_works_without_env(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            from case_core.providers.mock import MockProvider

            provider = MockProvider()
            assert provider.name == "mock"

    def test_groq_provider_reads_env_var(self) -> None:
        with patch.dict(os.environ, {"CASE_GROQ_API_KEY": "test-key-12345"}):
            from case_core.providers.groq import GroqProvider

            provider = GroqProvider()
            assert provider.api_key == "test-key-12345"

    def test_groq_provider_empty_without_env(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            if "CASE_GROQ_API_KEY" in os.environ:
                del os.environ["CASE_GROQ_API_KEY"]
            from case_core.providers.groq import GroqProvider

            provider = GroqProvider()
            assert provider.api_key == ""

    def test_env_example_has_required_vars(self) -> None:
        example = Path(".env.example")
        assert example.exists(), ".env.example should exist"

        content = example.read_text()
        assert "CASE_PROVIDER=" in content
        assert "CASE_GROQ_API_KEY=" in content

    def test_env_in_gitignore(self) -> None:
        gitignore = Path(".gitignore")
        assert gitignore.exists(), ".gitignore should exist"

        content = gitignore.read_text()
        assert ".env" in content
