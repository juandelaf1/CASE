import ast
import os
import sys

sys.path.insert(0, "src")

STREAMLIT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "streamlit_app")

FORBIDDEN_MODULES = [
    "case_core.contracts",
    "case_core.domain",
    "case_core.providers",
    "case_core.reliability",
    "case_core.prompts",
    "case_core.ports",
    "case_infra",
]


def _find_python_files(directory: str) -> list[str]:
    files = []
    for root, _, filenames in os.walk(directory):
        for f in filenames:
            if f.endswith(".py"):
                files.append(os.path.join(root, f))
    return files


def _get_imports(filepath: str) -> list[str]:
    with open(filepath, encoding="utf-8") as f:
        tree = ast.parse(f.read())

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


class TestArchitectureBoundary:
    def test_streamlit_no_direct_core_imports(self):
        files = _find_python_files(STREAMLIT_DIR)
        violations = []

        for filepath in files:
            imports = _get_imports(filepath)
            for imp in imports:
                for forbidden in FORBIDDEN_MODULES:
                    if imp.startswith(forbidden):
                        rel_path = os.path.relpath(filepath, STREAMLIT_DIR)
                        violations.append(f"{rel_path}: imports '{imp}'")

        assert violations == [], (
            "Architecture boundary violated! Streamlit must only use HTTP API.\n"
            "Violations:\n" + "\n".join(f"  - {v}" for v in violations)
        )

    def test_streamlit_files_exist(self):
        assert os.path.exists(os.path.join(STREAMLIT_DIR, "app.py"))
        assert os.path.exists(os.path.join(STREAMLIT_DIR, "client.py"))
        assert os.path.exists(os.path.join(STREAMLIT_DIR, "views", "triage.py"))
        assert os.path.exists(os.path.join(STREAMLIT_DIR, "views", "status.py"))
        assert os.path.exists(os.path.join(STREAMLIT_DIR, "components", "decision.py"))
        assert os.path.exists(os.path.join(STREAMLIT_DIR, "components", "state.py"))
