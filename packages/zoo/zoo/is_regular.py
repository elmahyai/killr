"""Regularity and frequency replacement.

A series is strictly regular when every step matches the first step.
It is regular when every step is an integer multiple of the smallest
step, or when the steps themselves are integers. A zooreg is regular
until ``strict`` is true. ``frequency<-`` on a plain zoo rounds a
near-integer frequency above 1.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from zoo.index import (
    all_equal_true,
    index_default,
    numeric_diff,
    r_round,
    r_round_values,
)
from zoo.series import Zoo


def is_regular(x: Any, strict: bool = False) -> bool:
    """Whether ``x`` is regular, or strictly regular when ``strict`` is true."""
    if isinstance(x, Zoo):
        if _is_zooreg(x):
            if strict:
                return _regular_zoo(x, True)
            return True
        return _regular_zoo(x, bool(strict))
    if getattr(x, "tsp", None) is not None:
        return True
    series = Zoo(x, index_default(x))
    return _regular_zoo(series, bool(strict))


def frequency_set(x: Any, value: Any) -> Zoo:
    """Assign ``frequency<-``. The series becomes a zooreg when the spacing fits."""
    if not isinstance(x, Zoo):
        raise ValueError("no applicable method for 'frequency<-'")
    if _is_zooreg(x):
        return _set_zooreg(x, value)
    return _set_zoo(x, value)


def _regular_zoo(x: Zoo, strict: bool) -> bool:
    try:
        delta = numeric_diff(x.index)
    except (TypeError, ValueError):
        return False
    if any(math.isnan(item) for item in delta):
        return False
    if len(delta) < 1:
        return False
    if strict:
        repeated = [delta[0]] * len(delta)
        return all_equal_true(delta, repeated)
    unique = _unique(delta)
    smallest = min(unique)
    ratio = [_divide(item, smallest) for item in unique]
    rounded = r_round_values(ratio)
    if all_equal_true(ratio, rounded):
        return True
    return all_equal_true(unique, r_round_values(unique))


def _set_zoo(x: Zoo, value: Any) -> Zoo:
    freq_ok = _zoo_frequency_ok(x, value)
    if not freq_ok:
        raise ValueError("freqOK is not TRUE")
    stored = float(value)
    if stored > 1.0 and all_equal_true(stored, r_round(stored)):
        stored = float(r_round(stored))
    return Zoo(
        np.array(x.data, copy=True, order="F"),
        _copy_index(x.index),
        frequency=stored,
        regular=True,
    )


def _set_zooreg(x: Zoo, value: Any) -> Zoo:
    delta = numeric_diff(x.index)
    scaled = [item * float(value) for item in delta]
    if not all_equal_true(scaled, r_round_values(scaled)):
        raise ValueError(
            "identical(all.equal(delta * value, round(delta * value)), TRUE) is not TRUE"
        )
    return Zoo(
        np.array(x.data, copy=True, order="F"),
        _copy_index(x.index),
        frequency=float(value),
        regular=True,
    )


def _zoo_frequency_ok(x: Zoo, value: Any) -> bool:
    try:
        delta = numeric_diff(x.index)
    except (TypeError, ValueError):
        return False
    if any(math.isnan(item) for item in delta):
        return False
    if len(delta) < 1:
        return True
    scaled = [item * float(value) for item in delta]
    return all_equal_true(scaled, r_round_values(scaled))


def _is_zooreg(x: Zoo) -> bool:
    return bool(x.regular) or x.frequency is not None


def _unique(values: list[float]) -> list[float]:
    found: list[float] = []
    for value in values:
        if not any(_same(value, earlier) for earlier in found):
            found.append(value)
    return found


def _same(left: float, right: float) -> bool:
    if math.isnan(left) and math.isnan(right):
        return True
    return left == right


def _divide(item: float, smallest: float) -> float:
    try:
        return item / smallest
    except ZeroDivisionError:
        if item == 0.0:
            return float("nan")
        return math.inf if item > 0.0 else -math.inf


def _copy_index(index: Any) -> Any:
    if isinstance(index, np.ndarray):
        return np.array(index, copy=True)
    if isinstance(index, (list, tuple)):
        return list(index)
    return index
