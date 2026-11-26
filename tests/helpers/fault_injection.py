"""Test-only fault injection hooks. Inert unless CASE_TEST_FAULT_INJECTION=1."""
from __future__ import annotations

import os
from collections.abc import Callable

_hooks: dict[str, Callable[[], None]] = {}

def enabled() -> bool:
    return os.environ.get("CASE_TEST_FAULT_INJECTION") == "1"

def set_hook(point: str, fn: Callable[[], None] | None) -> None:
    if fn is None:
        _hooks.pop(point, None)
    else:
        _hooks[point] = fn

def clear() -> None:
    _hooks.clear()

def maybe_raise(point: str) -> None:
    if not enabled():
        return
    fn = _hooks.get(point)
    if fn is not None:
        fn()
