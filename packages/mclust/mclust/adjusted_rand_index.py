"""Adjusted Rand index (``adjustedRandIndex``)."""

from __future__ import annotations

import math
from typing import Any, Sequence

import numpy as np

__all__ = ["adjusted_rand_index"]


def adjusted_rand_index(x: Sequence[Any], y: Sequence[Any]) -> float:
    """Compare two class label vectors with the adjusted Rand index."""
    xv = np.asarray(x, dtype=object).ravel().tolist()
    yv = np.asarray(y, dtype=object).ravel().tolist()
    if len(xv) != len(yv):
        raise ValueError("arguments must be vectors of the same length")

    tab = _table_two(xv, yv)
    if tab.shape == (1, 1):
        return 1.0

    a = _sum_choose2(tab)
    row_sums = tab.sum(axis=1)
    col_sums = tab.sum(axis=0)
    b = _sum_choose2(row_sums) - a
    c = _sum_choose2(col_sums) - a
    n = float(tab.sum())
    d = _choose2(n) - a - b - c
    denom_total = a + b + c + d
    expected = (a + b) * (a + c) / denom_total
    numer = a - expected
    denom = (a + b + a + c) / 2 - expected
    return numer / denom


def _canonical(value: Any) -> tuple[str, Any]:
    if isinstance(value, (str, np.str_)):
        return ("str", str(value))
    if isinstance(value, (bool, np.bool_)):
        return ("bool", bool(value))
    if isinstance(value, (int, np.integer, float, np.floating)):
        return ("num", float(value))
    return ("str", str(value))


def _unique_sorted(values: list[Any]) -> list[Any]:
    seen: dict[tuple[str, Any], Any] = {}
    for item in values:
        key = _canonical(item)
        if key not in seen:
            seen[key] = item
    items = list(seen.values())
    if items and all(_canonical(v)[0] == "str" for v in items):
        return sorted(items, key=str)
    return sorted(items, key=lambda v: _canonical(v)[1] if _canonical(v)[0] == "num" else str(v))


def _table_two(x: list[Any], y: list[Any]) -> np.ndarray:
    row_levels = _unique_sorted(x)
    col_levels = _unique_sorted(y)
    row_index = {_canonical(v): i for i, v in enumerate(row_levels)}
    col_index = {_canonical(v): i for i, v in enumerate(col_levels)}
    tab = np.zeros((len(row_levels), len(col_levels)), dtype=np.float64)
    for a, b in zip(x, y):
        tab[row_index[_canonical(a)], col_index[_canonical(b)]] += 1.0
    return tab


def _choose2(n: float) -> float:
    n_int = int(n)
    if n_int < 2:
        return 0.0
    return float(math.comb(n_int, 2))


def _sum_choose2(values: np.ndarray) -> float:
    total = 0.0
    for value in np.ravel(values):
        total += _choose2(float(value))
    return total
