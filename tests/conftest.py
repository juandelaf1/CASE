"""Global pytest configuration for deterministic local runs.

- Ensures src/ is importable.
- Isolates default provider selection from local .env to keep non-live suites stable.
  (Live/external tests can set CASE_PROVIDER explicitly when intended.)
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure src is importable for all test environments
SRC = Path(__file__).resolve().parents[1] / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def pytest_configure(config):  # type: ignore[no-untyped-def]
    """Keep deterministic defaults for non-live runs.

    Local `.env` may set CASE_PROVIDER to a live provider; force mock by default
    so deterministic suites are reproducible. Live-marked runs/tests can override
    explicitly in fixtures or by selecting `-m live`.
    """
    markexpr = getattr(config.option, "markexpr", "") or ""
    # If the user explicitly selects live tests, do not force mock globally.
    if "live" in markexpr.split():
        return
    os.environ["CASE_PROVIDER"] = "mock"
