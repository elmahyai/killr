"""Fast mean calculations in non-overlapping bins."""

from __future__ import annotations

import numpy as np
from binmeans import bin_means as _bin_means

from matrixstats.bincounts import _as_float_vector, _flag


class BinMeansResult(np.ndarray):
    """Bin means with the integer ``count`` of each bin."""

    def __new__(cls, means: np.ndarray, count: np.ndarray):
        obj = np.array(means, dtype=np.float64, copy=True).view(cls)
        obj.count = np.array(count, dtype=np.int32, copy=True)
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.count = getattr(obj, "count", None)


def binMeans(y, x, bx, idxs=None, na_rm=True, count=True, right=True):
    """Mean of ``y`` inside the non-overlapping bins of ``x``.

    ``bx`` holds ``B + 1`` ordered break points. ``right=True`` uses the
    right-closed, left-open bins ``(bx[j], bx[j + 1]]``. ``right=False`` uses
    the left-closed, right-open bins ``[bx[j], bx[j + 1])``. A point with
    missing ``x`` is dropped. Missing ``y`` is dropped when ``na_rm`` is true.
    Infinite ``y`` is an error unless ``y`` is integer or logical. Missing
    ``bx`` is an error. ``idxs`` is a 1-based subscript applied to both ``y``
    and ``x``. ``na_rm`` is ``na.rm`` in R.

    Returns a one-dimensional float array of length ``B``. Empty bins are
    NaN. When ``count`` is true, the integer bin counts are the ``count``
    attribute.
    """
    values, kind = _as_y(y)
    positions = _as_float_vector("x", x)
    breaks = _as_float_vector("bx", bx)
    drop_missing = _flag("na_rm", na_rm)
    want_count = _flag("count", count)
    closed_right = _flag("right", right)
    means, counts = _bin_means(
        values,
        positions,
        breaks,
        idxs,
        bool(drop_missing),
        bool(closed_right),
        kind == "float",
    )
    if want_count:
        return BinMeansResult(means, counts)
    return np.asarray(means, dtype=np.float64)


def _as_y(value) -> tuple[np.ndarray, str]:
    if isinstance(value, str):
        raise ValueError("Argument 'y' is not numeric or logical: character")
    if isinstance(value, (bool, np.bool_)):
        return np.array([1.0 if value else 0.0], dtype=np.float64), "logical"
    array = np.asarray(value)
    if array.dtype == object:
        return _object_y(array)
    if np.issubdtype(array.dtype, np.bool_):
        data = array.astype(np.float64)
        kind = "logical"
    elif np.issubdtype(array.dtype, np.integer):
        data = array.astype(np.float64)
        kind = "int"
    elif np.issubdtype(array.dtype, np.floating):
        data = array.astype(np.float64, copy=False)
        kind = "float"
    else:
        raise ValueError(f"Argument 'y' is not numeric or logical: {array.dtype.kind}")
    if data.ndim == 0:
        data = data.reshape(1)
    if data.ndim != 1:
        raise ValueError("Argument 'y' must be a vector")
    return np.ascontiguousarray(data, dtype=np.float64), kind


def _object_y(array: np.ndarray) -> tuple[np.ndarray, str]:
    logical = True
    values = []
    for item in array.reshape(-1).tolist():
        if item is None:
            values.append(np.nan)
            continue
        if isinstance(item, bool):
            values.append(1.0 if item else 0.0)
            continue
        logical = False
        if isinstance(item, (int, float)):
            values.append(float(item))
            continue
        raise ValueError("Argument 'y' is not numeric or logical: character")
    data = np.asarray(values, dtype=np.float64)
    if data.ndim != 1:
        raise ValueError("Argument 'y' must be a vector")
    return data, ("logical" if logical else "float")
