"""Equal-count shingle intervals (lattice 0.23-1 ``equal.count``)."""

from __future__ import annotations

import numpy as np

from lattice.as_shingle import Shingle, _make_list_from_intervals, as_shingle
from lattice.is_shingle import is_shingle


def equal_count(x, number=6, overlap=0.5, **kwargs):
    """Convert ``x`` to a shingle using the equal-count algorithm."""
    if kwargs:
        unexpected = ", ".join(sorted(kwargs))
        raise TypeError(f"unexpected keyword argument(s): {unexpected}")
    values = np.asarray(x, dtype=float).reshape(-1)
    intervals = _co_intervals(values, number=number, overlap=overlap)
    levels = _make_list_from_intervals(intervals)
    shingle = Shingle(values, levels)
    if not is_shingle(shingle):
        raise TypeError("internal shingle construction failed")
    return as_shingle(shingle)


def _co_intervals(x, number=6, overlap=0.5):
    """``graphics::co.intervals`` (passed through from ``equal.count``)."""
    values = np.asarray(x, dtype=float).reshape(-1)
    sorted_x = np.sort(values[~np.isnan(values)])
    n = sorted_x.size
    if n == 0:
        return np.empty((0, 2), dtype=float)
    r = n / (number * (1.0 - overlap) + overlap)
    ii = np.arange(number, dtype=float) * (1.0 - overlap) * r
    one_based = np.round(1.0 + ii).astype(int)
    end_based = np.round(r + ii).astype(int)
    x1 = sorted_x[one_based - 1]
    xr = sorted_x[end_based - 1]
    keep = np.concatenate([[True], (np.diff(x1) > 0) | (np.diff(xr) > 0)])
    jump = np.diff(sorted_x)
    positive = jump[jump > 0]
    eps = 0.5 * (positive.min() if positive.size else 0.0)
    return np.column_stack([x1[keep] - eps, xr[keep] + eps])
