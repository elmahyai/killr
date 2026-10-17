"""Fast element counting in non-overlapping bins."""

from __future__ import annotations

import numpy as np
from bincounts import bin_counts as _bin_counts


def binCounts(x, bx, idxs=None, right=True):
    """Count elements of ``x`` in the non-overlapping bins of ``bx``.

    ``bx`` holds ``B + 1`` ordered break points. ``right=True`` uses the
    right-closed, left-open bins ``(bx[j], bx[j + 1]]``. ``right=False`` uses
    the left-closed, right-open bins ``[bx[j], bx[j + 1])``. Missing values in
    ``x`` are dropped. Missing values in ``bx`` are an error. ``idxs`` is a
    1-based subscript, the same rules as R ``x[idxs]``.

    Returns a one-dimensional ``int32`` array of length ``B``.
    """
    sample = _as_float_vector("x", x)
    breaks = _as_float_vector("bx", bx)
    return _bin_counts(sample, breaks, idxs, bool(_flag("right", right)))


def _flag(name: str, value) -> bool:
    if isinstance(value, np.ndarray):
        if value.shape == () or value.size == 1:
            value = value.reshape(-1)[0]
        else:
            raise ValueError(f"Argument '{name}' must be a single value")
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value is None or (isinstance(value, float) and np.isnan(value)):
        raise ValueError(f"Argument '{name}' must be either TRUE or FALSE")
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool) and int(value) in (0, 1):
        return bool(int(value))
    raise ValueError(f"Argument '{name}' must be either TRUE or FALSE")


def _as_float_vector(name: str, value) -> np.ndarray:
    if isinstance(value, str):
        raise ValueError(f"Argument '{name}' is not numeric: character")
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"Argument '{name}' is not numeric: logical")
    array = np.asarray(value)
    if array.dtype == object:
        array = _object_to_float(name, array)
    elif np.issubdtype(array.dtype, np.bool_):
        raise ValueError(f"Argument '{name}' is not numeric: logical")
    elif np.issubdtype(array.dtype, np.integer) or np.issubdtype(array.dtype, np.floating):
        array = array.astype(np.float64, copy=False)
    else:
        raise ValueError(f"Argument '{name}' is not numeric: {array.dtype.kind}")
    if array.ndim == 0:
        array = array.reshape(1)
    if array.ndim != 1:
        raise ValueError(f"Argument '{name}' must be a vector")
    return np.ascontiguousarray(array, dtype=np.float64)


def _object_to_float(name: str, array: np.ndarray) -> np.ndarray:
    values = []
    for item in array.reshape(-1).tolist():
        if item is None:
            values.append(np.nan)
        elif isinstance(item, bool):
            raise ValueError(f"Argument '{name}' is not numeric: logical")
        elif isinstance(item, (int, float)):
            values.append(float(item))
        else:
            raise ValueError(f"Argument '{name}' is not numeric: character")
    return np.asarray(values, dtype=np.float64)
