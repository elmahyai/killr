"""Combination matrix for merging mixture components (``combMat``)."""

from __future__ import annotations

from typing import Any

import numpy as np

__all__ = ["combMat"]


def combMat(K: int, l1: Any, l2: Any) -> np.ndarray:
    """Build the matrix that merges mixture components ``l1`` and ``l2``."""
    k = int(K)
    lo = _min_r(l1, l2)
    hi = _max_r(l1, l2)
    len1 = _length_r(l1)
    len2 = _length_r(l2)

    if len1 == 0 or len2 == 0:
        row_idx = None
        col_idx = int(hi)
    else:
        row_idx = int(lo)
        col_idx = int(hi)

    l2 = col_idx
    top_left = np.eye(l2 - 1)
    top_right = np.zeros((l2 - 1, k - l2 + 1))
    bottom_left = np.zeros((k - l2, l2))
    bottom_right = np.eye(k - l2)
    m = np.vstack(
        [np.hstack([top_left, top_right]), np.hstack([bottom_left, bottom_right])]
    )
    if row_idx is not None:
        m[row_idx - 1, col_idx - 1] = 1.0
    return m


def _length_r(x: Any) -> int:
    if isinstance(x, (int, float, np.integer, np.floating)):
        return 1
    arr = np.asarray(x)
    if arr.ndim == 0:
        return 1
    return int(arr.size)


def _values_r(x: Any) -> list[float]:
    if _length_r(x) == 0:
        return []
    if isinstance(x, (int, float, np.integer, np.floating)):
        return [float(x)]
    arr = np.asarray(x, dtype=float).ravel()
    return [float(v) for v in arr]


def _min_r(a: Any, b: Any) -> float:
    vals = _values_r(a) + _values_r(b)
    if not vals:
        return float("inf")
    return min(vals)


def _max_r(a: Any, b: Any) -> float:
    vals = _values_r(a) + _values_r(b)
    if not vals:
        return float("-inf")
    return max(vals)
