"""Construct lattice shingles (lattice 0.23-1 ``shingle``)."""

from __future__ import annotations

import math

import numpy as np

from lattice.as_shingle import Shingle, _make_list_from_intervals


def shingle(x, intervals=None):
    """Build a shingle from numeric ``x`` and optional interval levels."""
    values = np.asarray(x, dtype=float).reshape(-1)
    if intervals is None:
        intervals = _sort_unique(values)
    matrix = np.asarray(intervals, dtype=float)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    if matrix.shape[1] == 1:
        matrix = np.column_stack([matrix[:, 0], matrix[:, 0]])
    elif matrix.shape[1] > 2:
        raise ValueError("bad value of 'intervals'")
    levels = _make_list_from_intervals(matrix)
    return Shingle(values, levels)


def _sort_unique(values):
    """``sort(unique(x))`` for numeric ``x`` in R (NA levels are dropped)."""
    uniq = []
    for value in np.asarray(values, dtype=float).reshape(-1):
        if math.isnan(value):
            if not any(math.isnan(item) for item in uniq):
                uniq.append(math.nan)
            continue
        if not any(not math.isnan(item) and item == value for item in uniq):
            uniq.append(float(value))
    return sorted(item for item in uniq if not math.isnan(item))
