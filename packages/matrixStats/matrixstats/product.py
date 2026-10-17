"""Product of a numeric vector, ported from matrixStats ``product``."""

from __future__ import annotations

import math

import numpy as np
from product import (
    product_f64,
    product_f64_f64,
    product_f64_i64,
    product_f64_logical,
    product_i64,
    product_i64_f64,
    product_i64_i64,
    product_i64_logical,
)


def product(x, idxs=None, na_rm: bool = False) -> float:
    """Product of the values in ``x``.

    Mirrors ``matrixStats::product``. The product is the exponential of the
    sum of logs of absolute values, with the sign tracked separately. ``idxs``
    is 1-based. ``None`` uses every element. ``na_rm`` drops missing values.
    An empty selection returns 1.
    """
    kind, values = _as_values(x)
    na_rm = bool(na_rm)
    if idxs is None:
        if kind == "integer":
            return product_i64(values, na_rm)
        return product_f64(values, na_rm)

    index_kind, index = _as_idxs(idxs)
    if kind == "integer":
        if index_kind == "integer":
            return product_i64_i64(values, index, na_rm)
        if index_kind == "real":
            return product_i64_f64(values, index, na_rm)
        return product_i64_logical(values, index, na_rm)
    if index_kind == "integer":
        return product_f64_i64(values, index, na_rm)
    if index_kind == "real":
        return product_f64_f64(values, index, na_rm)
    return product_f64_logical(values, index, na_rm)


def _as_values(x):
    if isinstance(x, (list, tuple)) and any(v is None for v in x):
        values = np.array([math.nan if v is None else v for v in x], dtype=np.float64)
        return "real", np.ascontiguousarray(values)
    array = np.asarray(x)
    if array.dtype == object:
        values = [math.nan if v is None else v for v in array.reshape(-1)]
        array = np.array(values, dtype=np.float64)
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError("x must be a numeric vector")
    if array.dtype == np.bool_:
        raise ValueError("Argument 'x' cannot be logical")
    if np.issubdtype(array.dtype, np.integer):
        return "integer", np.ascontiguousarray(array, dtype=np.int64)
    if np.issubdtype(array.dtype, np.floating):
        return "real", np.ascontiguousarray(array, dtype=np.float64)
    raise ValueError("Argument 'x' must be of type integer or numeric")


def _as_idxs(idxs):
    logical = _logical_codes(idxs)
    if logical is not None:
        return "logical", logical
    if isinstance(idxs, (list, tuple)) and any(v is None for v in idxs):
        array = np.array(
            [math.nan if v is None else v for v in idxs],
            dtype=np.float64,
        )
    else:
        array = np.asarray(idxs)
        if array.dtype == object:
            array = np.array(
                [math.nan if v is None else v for v in array.reshape(-1)],
                dtype=np.float64,
            )
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError("idxs must be a vector")
    if np.issubdtype(array.dtype, np.integer):
        return "integer", np.ascontiguousarray(array, dtype=np.int64)
    if np.issubdtype(array.dtype, np.floating):
        return "real", np.ascontiguousarray(array, dtype=np.float64)
    raise ValueError("idxs can only be integer, numeric, or logical")


def _logical_codes(idxs):
    if isinstance(idxs, (bool, np.bool_)):
        return np.array([1 if idxs else 0], dtype=np.int8)
    if isinstance(idxs, np.ndarray) and idxs.dtype == np.bool_:
        array = np.atleast_1d(idxs)
        if array.ndim != 1:
            raise ValueError("idxs must be a vector")
        return np.ascontiguousarray(array, dtype=np.int8)
    if isinstance(idxs, np.ndarray) and idxs.dtype == object:
        values = list(idxs.reshape(-1))
    elif isinstance(idxs, (list, tuple)):
        values = list(idxs)
    else:
        return None
    if not values or not all(_is_logical_mark(v) for v in values):
        return None
    codes = np.empty(len(values), dtype=np.int8)
    for i, value in enumerate(values):
        if value is None or (isinstance(value, float) and math.isnan(value)):
            codes[i] = -1
        else:
            codes[i] = 1 if value else 0
    return codes


def _is_logical_mark(value) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return True
    if value is None:
        return True
    return isinstance(value, float) and math.isnan(value)
