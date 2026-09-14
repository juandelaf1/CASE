from __future__ import annotations

import tomllib
from pathlib import Path


def _read_version() -> str:
    pyproject_path = Path(__file__).parent.parent.parent / "pyproject.toml"
    if pyproject_path.exists():
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)
        project = data.get("project", {})
        version = project.get("version", "0.0.0")
        if isinstance(version, str):
            return version
    return "0.0.0"


VERSION: str = _read_version()
