"""Small helpers shared by the pracma ports."""

from __future__ import annotations

import math

import numpy as np


class PracmaError(Exception):
    """An error raised with the same message R would stop on."""


def as_1d(value) -> np.ndarray:
    """A numeric vector. A scalar becomes length 1. None is empty."""
    if value is None:
        return np.array([], dtype=float)
    array = np.asarray(value)
    if array.dtype == bool:
        return array.astype(float).reshape(-1)
    if not np.issubdtype(array.dtype, np.number):
        raise PracmaError("value must be numeric")
    return np.array(array, dtype=float, copy=True).reshape(-1)


def as_matrix(value) -> np.ndarray:
    """A 2-d array stored in row order, matching a written matrix."""
    array = np.asarray(value, dtype=float)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim != 2:
        raise PracmaError("value must be a vector or a matrix")
    return np.array(array, dtype=float, copy=True)


def is_numeric(value) -> bool:
    if value is None:
        return False
    if isinstance(value, (bool, np.bool_)):
        return False
    if isinstance(value, (int, float, np.integer, np.floating)):
        return True
    if isinstance(value, (list, tuple)):
        return all(is_numeric(item) or isinstance(item, (list, tuple)) for item in value)
    array = np.asarray(value)
    return array.dtype != object and np.issubdtype(array.dtype, np.number) and array.dtype != bool

