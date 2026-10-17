"""accumarray and uniq from accumarray.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, require


def uniq(a, first=False):
    if a is None or np.asarray(a).size == 0:
        return {"b": np.array([]), "m": np.array([]), "n": np.array([])}
    require(is_numeric(a), "Argument 'a' must be a numeric vector.")
    values = np.asarray(a, dtype=float)
    if values.ndim != 1:
        raise PracmaError("Argument 'a' must be a numeric vector.")
    order = []
    seen = set()
    for value in values:
        key = float(value)
        if key not in seen:
            seen.add(key)
            order.append(key)
    unique = np.array(order, dtype=float)
    where = np.zeros(unique.size, dtype=float)
    index = np.zeros(values.size, dtype=float)
    for slot, value in enumerate(unique):
        hits = np.flatnonzero(values == value)
        where[slot] = float((hits[0] if first else hits[-1]) + 1)
        index[hits] = slot + 1
    return {"b": unique, "m": where, "n": index}


def _sum(values):
    array = np.asarray(values, dtype=float).reshape(-1)
    if array.size == 0:
        return 0.0
    return float(np.sum(array))


def accumarray(subs, val, sz=None, func=None, fillval=0):
    require(is_numeric(subs), "is.numeric(subs) is not TRUE")
    require(is_numeric(val), "is.numeric(val) is not TRUE")
    if func is None:
        func = _sum
    indices = np.floor(np.asarray(subs, dtype=float))
    if np.any(indices < 1):
        raise PracmaError("Argument 'subs' must be a matrix of integer indices.")
    matrix_input = indices.ndim == 2
    if indices.ndim <= 1:
        indices = indices.reshape(-1, 1)
        matrix_input = False
    rows, cols = indices.shape
    values = np.asarray(val, dtype=float).reshape(-1)
    if values.size < rows:
        raise PracmaError("Length of 'vals' must not be smaller than no. of rows of 'subs'.")
    extent = np.max(indices, axis=0)
    if sz is not None:
        requested = np.asarray(sz, dtype=float).reshape(-1)
        if requested.size != cols or np.any(requested < extent):
            raise PracmaError("Argument 'sz' does not fit with 'subs'.")
        extent = requested
    extent = np.array(np.rint(extent), dtype=int)
    if cols == 1:
        accumulated = np.full(int(extent[0]), fillval, dtype=float)
        column = indices[:, 0].astype(int)
        for group in np.unique(column):
            accumulated[int(group) - 1] = func(values[column == group])
        if matrix_input:
            accumulated = accumulated.reshape(-1, 1)
        return accumulated
    strides = np.cumprod(extent[:-1])
    linear = np.zeros(rows, dtype=int)
    for row in range(rows):
        linear[row] = int(indices[row, 0] + np.sum(strides * (indices[row, 1:] - 1)))
    accumulated = np.full(int(np.prod(extent)), fillval, dtype=float)
    for group in np.unique(linear):
        accumulated[int(group) - 1] = func(values[linear == group])
    return accumulated.reshape(tuple(int(item) for item in extent), order="F")
