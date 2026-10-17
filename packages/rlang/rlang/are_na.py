"""Vectorised missing-value tests."""

from __future__ import annotations

import math

from rlang import abort, is_atomic
from rlang.na_or import Double, Logical, _atomic_kind, _is_na


def _stop_input_type(x, what: str) -> None:
    if isinstance(x, list):
        friendly = "a list"
    elif isinstance(x, dict):
        friendly = "an environment"
    else:
        friendly = f"a {type(x).__name__}"
    abort(f"`x` must be {what}, not {friendly}.")


def _is_na_like(value, kind) -> bool:
    if kind is Double:
        return isinstance(value, float) and math.isnan(value)
    return _is_na(value, kind)


def _values_and_kind(x):
    kind = _atomic_kind(x)
    if kind is not None:
        if isinstance(x, kind):
            return kind, list(x.values)
        return kind, [x]
    if x is None or not is_atomic(x):
        return None, None
    kind = _atomic_kind(x)
    if kind is None:
        return None, None
    return kind, [x]


def are_na(x):
    kind, values = _values_and_kind(x)
    if kind is None:
        _stop_input_type(x, "an atomic vector")
    return Logical([_is_na_like(value, kind) for value in values])
