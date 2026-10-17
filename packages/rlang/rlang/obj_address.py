"""Address of an R object."""

from __future__ import annotations

from typing import Any

from rlang.as_label import MISSING

def _is_missing(x: Any) -> bool:
    return x is MISSING


def _maybe_missing(x: Any, default: Any = MISSING) -> Any:
    if _is_missing(x):
        return default
    return x


def obj_address(x: Any) -> str:
    """Return the memory address of ``x`` as a string."""
    x = _maybe_missing(x)
    return format(id(x), "#x")
