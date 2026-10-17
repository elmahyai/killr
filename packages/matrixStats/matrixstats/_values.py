"""Turn Python values into the vectors sum2 and mean2 pass to Rust.

Storage follows R. A logical vector is 0/1 with missing values. An integer
vector uses 32-bit values and R's integer NA. A double vector uses NaN for
a missing value. ``idxs`` stays 1-based; ``None`` means every element.
"""

from __future__ import annotations

import math

import numpy as np

_I32_MIN = int(np.iinfo(np.int32).min)
_I32_MAX = int(np.iinfo(np.int32).max)


def as_logical(value, name: str) -> bool:
    """Require one R logical, and reject NA."""
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise ValueError(f"Argument '{name}' must be a single value")
        value = value.reshape(-1)[0]
    if isinstance(value, np.bool_):
        value = bool(value)
    if not isinstance(value, bool):
        raise ValueError(f"Argument '{name}' is not logical: {_r_mode(value)}")
    return value


def prepare_x(x):
    """Return ``(storage, array)``.

    ``storage`` is ``double``, ``integer``, or ``logical``. The array is
    float64 for doubles and int32 for integer and logical data.
    """
    if isinstance(x, (bool, np.bool_)):
        return "logical", np.array([1 if bool(x) else 0], dtype=np.int32)
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return _integers_from_i64(np.array([int(x)], dtype=np.int64))
    if isinstance(x, (float, np.floating)):
        return "double", np.array([float(x)], dtype=np.float64)

    array = np.asarray(x)
    if array.dtype.kind in "SU":
        raise ValueError("Argument 'x' is not numeric or logical: character")
    if array.dtype == object:
        storage, values = _from_object(np.ravel(array, order="F"), argument="x")
        if storage == "logical":
            return "logical", _logical_data(values)
        if storage == "integer":
            return "integer", values
        return "double", values
    if array.ndim == 0:
        array = array.reshape(1)
    else:
        array = np.ravel(array, order="F")
    if array.dtype == bool:
        out = np.zeros(array.shape, dtype=np.int32)
        out[array] = 1
        return "logical", np.ascontiguousarray(out)
    if np.issubdtype(array.dtype, np.floating):
        return "double", np.ascontiguousarray(array, dtype=np.float64)
    if np.issubdtype(array.dtype, np.integer):
        return _integers_from_i64(np.ascontiguousarray(array, dtype=np.int64))
    raise ValueError(f"Argument 'x' is not numeric or logical: {array.dtype.name}")


def prepare_idxs(idxs):
    """Return ``(kind, array)``.

    ``kind`` is ``none``, ``integer``, ``double``, or ``logical``. The array
    is ``None`` when every element is selected.
    """
    if idxs is None:
        return "none", None
    if isinstance(idxs, (bool, np.bool_)):
        return "logical", np.array([1 if bool(idxs) else 0], dtype=np.int8)
    if isinstance(idxs, (int, np.integer)) and not isinstance(idxs, bool):
        return "integer", np.array([int(idxs)], dtype=np.int64)
    if isinstance(idxs, (float, np.floating)):
        return "double", np.array([float(idxs)], dtype=np.float64)

    array = np.asarray(idxs)
    if array.dtype.kind in "SU":
        raise ValueError("idxs can only be integer, numeric, or logical")
    if array.dtype == object:
        storage, values = _from_object(np.ravel(array, order="F"), argument="idxs")
        if storage == "logical":
            return "logical", _logical_index(values)
        if storage == "integer":
            return "integer", values.astype(np.int64, copy=False)
        return "double", values
    if array.ndim == 0:
        array = array.reshape(1)
    else:
        array = np.ravel(array, order="F")
    if array.dtype == bool:
        out = np.zeros(array.shape, dtype=np.int8)
        out[array] = 1
        return "logical", np.ascontiguousarray(out)
    if np.issubdtype(array.dtype, np.floating):
        return "double", np.ascontiguousarray(array, dtype=np.float64)
    if np.issubdtype(array.dtype, np.integer):
        return "integer", np.ascontiguousarray(array, dtype=np.int64)
    raise ValueError("idxs can only be integer, numeric, or logical")


def _r_mode(value) -> str:
    if isinstance(value, (bool, np.bool_)):
        return "logical"
    if isinstance(value, (int, np.integer, float, np.floating)):
        return "numeric"
    if isinstance(value, str):
        return "character"
    return type(value).__name__


def _scalar_kind(value) -> str:
    if value is None:
        return "missing"
    if isinstance(value, (bool, np.bool_)):
        return "logical"
    if isinstance(value, (int, np.integer)):
        return "integer"
    if isinstance(value, (float, np.floating)):
        return "double"
    return "other"


def _fits_i32(value: int) -> bool:
    return _I32_MIN <= value <= _I32_MAX


def _integers_from_i64(array: np.ndarray):
    if array.size == 0:
        return "integer", np.zeros(0, dtype=np.int32)
    smallest = int(array.min())
    largest = int(array.max())
    if smallest < _I32_MIN or largest > _I32_MAX:
        return "double", np.ascontiguousarray(array, dtype=np.float64)
    return "integer", np.ascontiguousarray(array, dtype=np.int32)


def _from_object(flat: np.ndarray, argument: str):
    items = [flat[i] for i in range(flat.size)]
    kinds: set[str] = set()
    for value in items:
        kind = _scalar_kind(value)
        if kind == "other":
            if argument == "idxs":
                raise ValueError("idxs can only be integer, numeric, or logical")
            mode = "character" if isinstance(value, str) else type(value).__name__
            raise ValueError(f"Argument '{argument}' is not numeric or logical: {mode}")
        kinds.add(kind)

    promote_double = "double" in kinds
    if not promote_double:
        for value in items:
            if _scalar_kind(value) == "integer" and not _fits_i32(int(value)):
                promote_double = True
                break
    if promote_double:
        out = np.empty(len(items), dtype=np.float64)
        for i, value in enumerate(items):
            kind = _scalar_kind(value)
            if kind == "missing":
                out[i] = np.nan
            elif kind == "logical":
                out[i] = 1.0 if value else 0.0
            elif kind == "double" and math.isnan(float(value)):
                out[i] = np.nan
            else:
                out[i] = float(value)
        return "double", out
    if "integer" in kinds:
        out = np.empty(len(items), dtype=np.int32)
        for i, value in enumerate(items):
            kind = _scalar_kind(value)
            if kind == "missing":
                out[i] = _I32_MIN
            elif kind == "logical":
                out[i] = 1 if value else 0
            else:
                out[i] = int(value)
        return "integer", out
    return "logical", items


def _logical_data(items) -> np.ndarray:
    out = np.empty(len(items), dtype=np.int32)
    for i, value in enumerate(items):
        if value is None:
            out[i] = _I32_MIN
        else:
            out[i] = 1 if value else 0
    return out


def _logical_index(items) -> np.ndarray:
    out = np.empty(len(items), dtype=np.int8)
    for i, value in enumerate(items):
        if value is None:
            out[i] = -1
        else:
            out[i] = 1 if value else 0
    return out
