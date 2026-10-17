"""Replace missing values (gtools 3.9.5 ``na.replace``)."""

from __future__ import annotations

import math
import numpy as np

_NA_BITS = np.uint64(0x7FF00000000007A2)
_NA_REAL = np.array([_NA_BITS]).view(np.float64)[0]
_NA_INT = np.int32(-(2**31))
_NA_LOGICAL = np.int8(2)


class _Missing:
    """R ``NA`` for character vectors in object storage."""

    def __repr__(self) -> str:
        return "NA"


NA = _Missing()


def _is_na_scalar(value, kind: str) -> bool:
    if kind == "f":
        if isinstance(value, (float, np.floating)):
            return math.isnan(float(value))
        return False
    if kind == "c":
        if isinstance(value, complex):
            return math.isnan(value.real) or math.isnan(value.imag)
        return False
    if kind == "i":
        if isinstance(value, (bool, np.bool_)):
            return False
        try:
            return np.int32(value) == _NA_INT
        except (TypeError, ValueError, OverflowError):
            return False
    if kind == "b":
        if isinstance(value, (bool, np.bool_)):
            return False
        try:
            return np.int8(value) == _NA_LOGICAL
        except (TypeError, ValueError, OverflowError):
            return value is NA
    if kind == "O":
        return value is NA or value is None
    if kind == "U":
        return value is NA
    return False


def _is_logical_int8(dtype: np.dtype) -> bool:
    return dtype.kind == "i" and dtype.itemsize == 1


def _missing_mask(array: np.ndarray) -> np.ndarray:
    kind = array.dtype.kind
    if kind in "fd":
        return np.isnan(array)
    if kind == "c":
        return np.isnan(array.real) | np.isnan(array.imag)
    if _is_logical_int8(array.dtype):
        return array == _NA_LOGICAL
    if kind == "i":
        return array == _NA_INT
    if kind == "b":
        return array.view(np.int8) == _NA_LOGICAL
    if kind == "O":
        return np.array([item is NA or item is None for item in array.ravel(order="F")], dtype=bool).reshape(
            array.shape, order="F"
        )
    if kind in "US":
        return np.array([item is NA for item in array.ravel(order="F")], dtype=bool).reshape(array.shape, order="F")
    return np.zeros(array.shape, dtype=bool)


def _as_array(x):
    if isinstance(x, np.ndarray):
        return np.array(x, copy=True, order="F"), x.ndim, x.dtype
    if isinstance(x, (list, tuple)):
        if not x:
            return np.array([], dtype=np.float64), 1, np.dtype(np.float64)
        if any(isinstance(item, str) for item in x):
            values = [NA if item is NA else str(item) for item in x]
            return np.array(values, dtype=object), 1, np.dtype(object)
        if any(isinstance(item, complex) and not isinstance(item, (float, int)) for item in x):
            return np.asarray(x, dtype=np.complex128), 1, np.dtype(np.complex128)
        if any(isinstance(item, bool) for item in x):
            out = []
            for item in x:
                if item is NA:
                    out.append(_NA_LOGICAL)
                elif item is True:
                    out.append(np.int8(1))
                elif item is False:
                    out.append(np.int8(0))
                else:
                    out.append(item)
            return np.asarray(out, dtype=np.int8), 1, np.dtype(np.int8)
        if any(isinstance(item, int) and not isinstance(item, bool) for item in x):
            values = []
            for item in x:
                if item is NA:
                    values.append(_NA_INT)
                else:
                    values.append(np.int32(item))
            return np.asarray(values, dtype=np.int32), 1, np.dtype(np.int32)
        return np.asarray(x, dtype=np.float64), 1, np.dtype(np.float64)
    if isinstance(x, bool):
        return np.asarray([np.int8(1 if x else 0)], dtype=np.int8), 1, np.dtype(np.int8)
    if isinstance(x, int) and not isinstance(x, bool):
        return np.asarray([np.int32(x)], dtype=np.int32), 1, np.dtype(np.int32)
    if isinstance(x, float):
        return np.asarray([x], dtype=np.float64), 1, np.dtype(np.float64)
    if isinstance(x, complex):
        return np.asarray([x], dtype=np.complex128), 1, np.dtype(np.complex128)
    if isinstance(x, str):
        return np.array([x], dtype=object), 1, np.dtype(object)
    if x is NA:
        return np.array([NA], dtype=object), 1, np.dtype(object)
    return np.asarray([x], dtype=np.float64), 1, np.dtype(np.float64)


def _coerce_replace(replace_value, dtype: np.dtype):
    kind = dtype.kind
    if kind in "fd":
        return np.asarray(replace_value, dtype=np.float64).reshape(())
    if kind == "c":
        return np.asarray(replace_value, dtype=np.complex128).reshape(())
    if _is_logical_int8(dtype):
        value = np.asarray(replace_value).reshape(())
        if isinstance(value, (bool, np.bool_)):
            return np.int8(1 if value else 0)
        return np.int8(value)
    if kind == "i":
        value = np.asarray(replace_value).reshape(())
        return np.int32(value)
    if kind == "b":
        value = np.asarray(replace_value).reshape(())
        if isinstance(value, (bool, np.bool_)):
            return np.int8(1 if value else 0)
        return np.int8(value)
    if kind == "O":
        if isinstance(replace_value, str):
            return replace_value
        item = np.asarray(replace_value).reshape(()).item()
        return str(item) if item is not NA else NA
    if kind in "US":
        return str(np.asarray(replace_value).reshape(()).item())
    return replace_value


def na_replace(x, replace, **kwargs):
    """Replace ``NA`` entries in ``x`` with ``replace``, or with ``replace(x, ...)`` when it is callable."""
    rep = replace(x, **kwargs) if callable(replace) else replace

    array, ndim, dtype = _as_array(x)
    mask = _missing_mask(array)
    if not mask.any():
        return _restore(array, ndim, dtype, x)

    value = _coerce_replace(rep, dtype)
    array = array.copy(order="F")
    array[mask] = value
    return _restore(array, ndim, dtype, x)


def _restore(array: np.ndarray, ndim: int, dtype: np.dtype, original):
    if isinstance(original, list):
        flat = array.ravel(order="F")
        if dtype.kind == "O":
            return [item for item in flat]
        if _is_logical_int8(dtype) or dtype.kind == "b":
            out = []
            for item in flat:
                code = int(item)
                if code == int(_NA_LOGICAL):
                    out.append(NA)
                else:
                    out.append(code == 1)
            return out
        if dtype.kind == "i":
            return [int(item) for item in flat]
        if dtype.kind == "c":
            return [complex(item) for item in flat]
        return [float(item) for item in flat]
    if isinstance(original, tuple):
        return tuple(_restore(array, ndim, dtype, list(original)))
    if ndim == 2 and array.ndim == 2:
        return array
    if array.size == 1 and ndim <= 1 and not isinstance(original, np.ndarray):
        item = array.reshape(()).item()
        if dtype.kind == "O" and item is not NA:
            return item
        return item
    return array
