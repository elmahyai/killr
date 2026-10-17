"""Coerce values to lattice shingles (lattice 0.23-1 ``as.shingle``)."""

from __future__ import annotations

import math

import numpy as np


class Shingle:
    """Numeric vector with interval levels, matching R class ``shingle``."""

    __slots__ = ("values", "levels")

    def __init__(self, values, levels):
        self.values = np.asarray(values, dtype=float).reshape(-1)
        self.levels = levels


def as_shingle(x):
    """Return ``x`` if it is already a shingle, otherwise build one with ``shingle(x)``."""
    if isinstance(x, Shingle):
        return x
    return _shingle(x)


def _shingle(x, intervals=None):
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


def _make_list_from_intervals(matrix):
    matrix = np.asarray(matrix, dtype=float)
    if matrix.ndim != 2 or matrix.shape[1] != 2:
        raise ValueError("x must be matrix with 2 columns")
    return [matrix[i, :].tolist() for i in range(matrix.shape[0])]


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
