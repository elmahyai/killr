"""size, numel, ndims, nnz, and isempty from pracma size.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, is_numeric_or_complex, r_length


def _array(value):
    if isinstance(value, (str, bytes)):
        return np.asarray(list(value))
    return np.asarray(value) if value is not None else np.array([])


def size(x, k=None):
    if r_length(x) == 0:
        shape = np.array([0.0])
    else:
        array = _array(x)
        if array.ndim <= 1:
            shape = np.array([1.0, float(array.size)])
        elif array.ndim >= 2:
            shape = np.array(array.shape, dtype=float)
        else:
            return None
    if k is None:
        return shape
    if isinstance(k, (bool, np.bool_)) or not is_numeric(k):
        raise PracmaError("Requested dimension 'k' is out of range.")
    index = int(np.asarray(k).reshape(-1)[0])
    if index > shape.size:
        return np.array([1.0])
    if index >= 1:
        return np.array([shape[index - 1]])
    raise PracmaError("Requested dimension 'k' is out of range.")


def numel(x):
    shape = size(x)
    if shape is None:
        return None
    return float(np.prod(shape))


def nnz(x):
    if r_length(x) == 0:
        return 0.0
    if not is_numeric(x) and not is_numeric_or_complex(x):
        raise PracmaError("is.numeric(x) || is.complex(x) is not TRUE")
    array = np.asarray(x)
    return float(np.sum(array != 0))


def ndims(x):
    if r_length(x) == 0:
        return 0.0
    array = _array(x)
    if array.ndim <= 1:
        return 1.0
    if array.ndim >= 2:
        return float(array.ndim)
    return np.nan


def isempty(x):
    return r_length(x) == 0
