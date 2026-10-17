"""Helpers shared by the shuffle translations. Not an R function."""

from __future__ import annotations

import numpy as np


def as_flag(value) -> bool:
    """R's ``if (flag)`` for a logical of length one."""
    a = np.ravel(np.asarray(value, dtype=bool))
    if a.size != 1:
        raise ValueError("the condition has length != 1")
    return bool(a[0])


def n_of(n) -> int:
    """permute's ``n``: a vector, matrix, or data frame gives its number of observations."""
    arr = np.asarray(n)
    if arr.ndim >= 2 or (arr.ndim == 1 and arr.size > 1):
        return int(arr.shape[0])
    return int(np.ravel(arr)[0])


def levels_of(values) -> np.ndarray:
    """Sorted unique values, the levels R's factor() gives for numbers and lowercase text."""
    return np.unique(np.asarray(values))
