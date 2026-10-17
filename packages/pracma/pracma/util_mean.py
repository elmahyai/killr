"""Geometric, harmonic, and trimmed means from mean.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_size import ndims
from pracma.util_support import is_numeric, require


def _dim_axis(x, dim):
    rank = ndims(x)
    if dim < 1 or dim > rank:
        raise PracmaError("Argument 'dim' must be between 1 and 'ndims(x)'.")
    array = np.asarray(x, dtype=float)
    if array.ndim <= 1:
        return array.reshape(-1), None
    return array, dim - 1


def harmmean(x, dim=1):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    array, axis = _dim_axis(x, dim)
    if axis is None:
        return np.array(1.0 / np.mean(1.0 / array))
    return 1.0 / np.mean(1.0 / array, axis=axis)


def geomean(x, dim=1):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    array, axis = _dim_axis(x, dim)
    if axis is None:
        return np.array(np.exp(np.sum(np.log(array)) / array.size))
    count = array.shape[axis]
    return np.exp(np.sum(np.log(array), axis=axis) / count)


def _trimmed(values, percent):
    ordered = np.sort(np.asarray(values, dtype=float).reshape(-1))
    count = ordered.size
    drop = int(np.round(count * percent / 100.0 / 2.0))
    if 2 * drop > count - 1:
        return np.nan
    return float(np.mean(ordered[drop : count - drop]))


def trimmean(x, percent=0):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    require(is_numeric(percent), "is.numeric(percent) is not TRUE")
    fraction = np.asarray(percent, dtype=float).reshape(-1)
    if fraction.size != 1 or fraction[0] < 0 or fraction[0] > 100:
        raise PracmaError("Argument 'percent' must be a scalar between 0 and 100.")
    rate = float(fraction[0])
    array = np.asarray(x, dtype=float)
    if array.ndim <= 1:
        return np.array(_trimmed(array, rate))
    if array.ndim == 2:
        return np.array([_trimmed(array[:, column], rate) for column in range(array.shape[1])])
    raise PracmaError("Function 'trimmean' not yet implemented for arrays.")
