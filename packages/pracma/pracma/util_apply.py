"""arrayfun and bsxfun from bsxfun.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, require


def arrayfun(func, *arrays):
    if len(arrays) < 1:
        raise PracmaError("Empty list of arrays: Result cannot be computed.")
    first = np.asarray(arrays[0])
    columns = [np.asarray(array).reshape(-1, order="F") for array in arrays]
    length = max(column.size for column in columns)
    values = [
        func(*[column[index % column.size] for column in columns]) for index in range(length)
    ]
    result = np.array(values, dtype=float)
    if first.ndim >= 2:
        if result.size != int(np.prod(first.shape)):
            raise PracmaError("dims do not match the length of object")
        return result.reshape(first.shape, order="F")
    return result


def bsxfun(func, x, y):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    require(is_numeric(y), "is.numeric(y) is not TRUE")
    left = np.asarray(x)
    right = np.asarray(y)
    if left.ndim <= 1 and right.ndim <= 1:
        return arrayfun(func, left.reshape(-1), right.reshape(-1))
    if left.ndim >= 2 and right.ndim >= 2 and left.shape == right.shape:
        # sweep(x, y, MARGIN=c(1, 2), FUN=func) names MARGIN, so y is STATS
        # and the function is applied elementwise.
        return arrayfun(func, left, right)
    raise PracmaError("Argument 'x', 'y' must be vectors or arrays of the same size.")
