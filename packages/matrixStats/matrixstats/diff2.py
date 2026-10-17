"""Fast lagged differences, ported from matrixStats `diff2`."""

from __future__ import annotations

import math

import numpy as np
from diff2 import diff2 as _diff2

_INT_MAX = 2_147_483_647
_INT_MIN = -2_147_483_648

__all__ = ["diff2"]


def diff2(x, idxs=None, lag=1, differences=1, use_names=True):
    """Lagged and iterated differences of a numeric vector.

    Mirrors ``matrixStats::diff2``. ``idxs`` is 1-based; ``None`` selects
    every element. ``lag`` and ``differences`` default to 1. The result is a
    one-dimensional float64 array. ``use_names`` is accepted and does not
    change the numeric result.
    """
    if not isinstance(use_names, (bool, np.bool_)):
        raise ValueError("Argument 'use_names' must be either TRUE or FALSE")

    values = _as_numeric_vector(x)
    lag_i = _as_positive_r_integer(lag, "lag")
    differences_i = _as_positive_r_integer(differences, "differences")
    kind, index_values = _prepare_idxs(idxs)
    return _diff2(values, kind, index_values, lag_i, differences_i)


def _as_numeric_vector(x) -> np.ndarray:
    array = np.asarray(x)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError("Argument 'x' must be a numeric vector")
    if array.dtype == np.bool_:
        raise ValueError("Argument 'x' cannot be logical")
    if not np.issubdtype(array.dtype, np.number) or np.issubdtype(
        array.dtype, np.complexfloating
    ):
        try:
            array = np.asarray(array, dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ValueError("Argument 'x' must be numeric") from exc
    if array.dtype == object or not np.issubdtype(array.dtype, np.number):
        raise ValueError("Argument 'x' must be numeric")
    return np.ascontiguousarray(array, dtype=np.float64)


def _as_positive_r_integer(value, name: str) -> int:
    """R's length check, then ``as.integer``, then the C positive check."""
    if value is None:
        raise ValueError(f"Argument '{name}' is not a scalar: 0")
    array = np.asarray(value)
    if array.ndim == 0:
        size = 1
        raw = array
    else:
        flat = np.reshape(array, -1)
        size = int(flat.size)
        raw = flat[0] if size else None
    if size != 1:
        raise ValueError(f"Argument '{name}' is not a scalar: {size}")
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Argument '{name}' must be a positive integer") from exc
    if not math.isfinite(number) or number > _INT_MAX or number < _INT_MIN:
        integer = None
    else:
        integer = int(math.trunc(number))
    if integer is None or integer < 1:
        raise ValueError(f"Argument '{name}' must be a positive integer")
    return integer


def _prepare_idxs(idxs):
    """Classify ``idxs`` only. Validation stays in the Rust crate.

    Kind 0 is every element. Kind 1 is integer, 2 is real, 3 is logical
    with 0 false, 1 true, and negative missing.
    """
    if idxs is None:
        return 0, None
    if isinstance(idxs, (list, tuple)) and _is_logical_object_sequence(idxs):
        return 3, _logical_from_sequence(idxs)

    array = np.asarray(idxs)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError("idxs can only be integer, numeric, or logical")
    if array.dtype == object:
        return 3, _logical_from_sequence(array.tolist())
    if array.dtype == np.bool_:
        logical = np.ascontiguousarray(array, dtype=np.int8)
        return 3, logical
    if np.issubdtype(array.dtype, np.integer):
        return 1, np.ascontiguousarray(array, dtype=np.int64)
    if np.issubdtype(array.dtype, np.floating):
        return 2, np.ascontiguousarray(array, dtype=np.float64)
    raise ValueError("idxs can only be integer, numeric, or logical")


def _is_logical_object_sequence(values) -> bool:
    if len(values) == 0:
        return False
    return all(_is_bool_or_missing(item) for item in values)


def _is_bool_or_missing(item) -> bool:
    if item is None:
        return True
    if isinstance(item, (bool, np.bool_)):
        return True
    return False


def _logical_from_sequence(values) -> np.ndarray:
    out = np.empty(len(values), dtype=np.int8)
    for i, item in enumerate(values):
        if item is None:
            out[i] = -1
        elif isinstance(item, (bool, np.bool_)):
            out[i] = 1 if item else 0
        else:
            raise ValueError("idxs can only be integer, numeric, or logical")
    return out
