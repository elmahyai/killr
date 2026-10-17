"""Allocate a vector, matrix, or array filled with one value.

Mirrors ``matrixStats::allocVector``, ``allocMatrix``, and ``allocArray``.
The storage mode is the mode of ``value``. A Python ``float`` is double, a
Python ``int`` is integer, and a Python ``bool`` is logical. ``None`` is R's
bare ``NA``, which is logical. Integer NA is ``-2147483648``. Double NA is
``nan``.

Logical results use R's integer storage: ``1`` for TRUE, ``0`` for FALSE, and
``-2147483648`` for NA. A matrix uses axis 0 for rows and axis 1 for columns,
so a constant fill prints in the same row and column positions as R.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

import allocmatrix as _allocmatrix

_NA = -2_147_483_648
_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_MISSING = object()

__all__ = ["allocArray", "allocMatrix", "allocVector"]


def allocMatrix(nrow, ncol, value=0.0, *_args, **_kwargs):
    """Allocate a matrix filled with ``value``.

    Mirrors ``matrixStats::allocMatrix``. ``nrow`` and ``ncol`` are coerced
    with R's ``as.integer``, truncating toward zero. The default ``value``
    is ``0.0``, a double, so the matrix is float64. Pass an ``int`` for an
    integer matrix and a ``bool`` for a logical matrix. Extra arguments are
    ignored, as R's ``...`` is.
    """
    nr = _one_integer(nrow, "nrow")
    nc = _one_integer(ncol, "ncol")
    kind, real, integer = _classify(value)
    return _allocmatrix.alloc_matrix_py(nr, nc, kind, real, integer)


def allocVector(length, value=0.0, *_args, **_kwargs):
    """Allocate a vector filled with ``value``.

    Mirrors ``matrixStats::allocVector``. ``length`` is coerced with
    ``as.numeric`` and then truncated toward zero. A negative length is an
    error. ``NaN`` and infinities are reported as a negative length, matching
    the installed cast. The result is a 1-d array of that length.
    """
    lengths = _coerce_numeric(length)
    if lengths.size != 1:
        raise ValueError("Argument 'length' must be a single numeric")
    kind, real, integer = _classify(value)
    return _allocmatrix.alloc_vector_py(float(lengths[0]), kind, real, integer)


def allocArray(dim=_MISSING, value=0.0, *_args, dim_=_MISSING, **_kwargs):
    """Allocate an array filled with ``value``.

    Mirrors ``matrixStats::allocArray``. ``dim`` is the dimension vector, the
    same name R uses for this function. ``dim_`` is accepted as an alias when
    ``dim`` is omitted. Other matrixStats functions spell that argument
    ``dim.``; their Python name is ``dim`` as well.

    Axis 0 is the first dimension. A length-two ``dim`` is a matrix, with
    axis 0 as rows and axis 1 as columns.
    """
    if dim is _MISSING:
        dim = dim_
    if dim is _MISSING:
        raise TypeError("allocArray() missing 1 required positional argument: 'dim'")
    dims = _coerce_integer(dim)
    if dims.size == 0:
        raise ValueError("Argument 'dim' must be an integer vector of at least length one")
    kind, real, integer = _classify(value)
    return _allocmatrix.alloc_array_py([int(item) for item in dims], kind, real, integer)


def _one_integer(values, name: str) -> int:
    coerced = _coerce_integer(values)
    if coerced.size != 1:
        raise ValueError(f"Argument '{name}' must be a single integer")
    return int(coerced.reshape(-1)[0])


def _classify(value):
    """Return ``(kind, real, integer)`` for ``fillWithValue``.

    ``kind`` is ``double``, ``integer``, ``logical``, ``bad``, or
    ``not_scalar``. ``bad`` is an atomic scalar of some other type.
    """
    if value is None:
        return "logical", 0.0, _NA
    if isinstance(value, (bool, np.bool_)):
        return "logical", 0.0, 1 if bool(value) else 0
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return _classify_int(int(value))
    if isinstance(value, (float, np.floating)):
        return "double", float(value), 0
    if isinstance(value, (complex, np.complexfloating)):
        return "bad", 0.0, 0
    if isinstance(value, str):
        return "bad", 0.0, 0
    if isinstance(value, (bytes, bytearray)):
        return ("bad" if len(value) == 1 else "not_scalar"), 0.0, 0
    return _classify_array(value)


def _classify_int(value: int):
    if value < _INT_MIN or value > _INT_MAX:
        return "double", float(value), 0
    return "integer", 0.0, value


def _classify_array(value):
    try:
        array = np.asarray(value)
    except (TypeError, ValueError):
        return "not_scalar", 0.0, 0
    if array.dtype.kind in "SU":
        return ("bad" if array.size == 1 else "not_scalar"), 0.0, 0
    if array.dtype == object:
        flat = array.ravel(order="F")
        if flat.size != 1:
            return "not_scalar", 0.0, 0
        item = flat[0]
        if isinstance(item, (list, tuple, dict, np.ndarray)):
            return "not_scalar", 0.0, 0
        return _classify(item)
    if array.dtype.kind in "mM":
        return ("bad" if array.size == 1 else "not_scalar"), 0.0, 0
    if array.size != 1:
        return "not_scalar", 0.0, 0
    if array.dtype == bool or array.dtype.kind == "b":
        return _classify(bool(array.reshape(-1)[0]))
    if np.issubdtype(array.dtype, np.number):
        return _classify(array.reshape(-1)[0].item())
    return "not_scalar", 0.0, 0


def _coerce_integer(values) -> np.ndarray:
    """R ``as.integer``, including its two NA warnings."""
    converted, coercion, ranged = _convert_integer(values)
    if coercion:
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=3)
    if ranged:
        warnings.warn(
            "NAs introduced by coercion to integer range", UserWarning, stacklevel=3
        )
    return converted


def _convert_integer(values):
    if values is None:
        return np.zeros(0, dtype=np.int32), False, False
    if isinstance(values, (bool, np.bool_)):
        return np.array([1 if bool(values) else 0], dtype=np.int32), False, False
    if isinstance(values, str):
        return _strings_to_i32([values])
    if isinstance(values, (int, np.integer)) and not isinstance(values, bool):
        converted, flag = _one_int(int(values))
        return np.array([converted], dtype=np.int32), False, flag == "range"
    if isinstance(values, (float, np.floating)):
        return _floats_to_i32(np.array([float(values)], dtype=np.float64))
    if isinstance(values, (complex, np.complexfloating)):
        return np.array([np.int32(_NA)], dtype=np.int32), True, False

    try:
        array = np.asarray(values)
    except (TypeError, ValueError) as err:
        raise ValueError("Argument is not numeric or logical") from err
    if array.ndim == 0:
        return _convert_integer(array.item())
    if array.dtype.kind in "SU":
        return _strings_to_i32([str(item) for item in array.ravel(order="F")])
    if array.dtype == object:
        return _objects_to_i32(list(array.ravel(order="F")))
    if array.dtype == bool or array.dtype.kind == "b":
        flat = np.ravel(array, order="F")
        out = np.zeros(flat.shape, dtype=np.int32)
        out[flat] = 1
        return out, False, False
    if np.issubdtype(array.dtype, np.floating):
        flat = np.ascontiguousarray(np.ravel(array, order="F"), dtype=np.float64)
        return _floats_to_i32(flat)
    if np.issubdtype(array.dtype, np.integer):
        flat = np.ascontiguousarray(np.ravel(array, order="F"), dtype=np.int64)
        return _ints_to_i32(flat)
    raise ValueError("Argument is not numeric or logical")


def _one_int(value: int):
    if value < _INT_MIN or value > _INT_MAX:
        return _NA, "range"
    return value, None


def _floats_to_i32(flat: np.ndarray):
    flat = np.ascontiguousarray(flat, dtype=np.float64)
    out = np.empty(flat.shape, dtype=np.int32)
    missing = np.isnan(flat)
    if np.any(missing):
        bits = flat.view(np.uint64)
        r_na = missing & ((bits & np.uint64(0xFFFFFFFF)) == np.uint64(0x7A2))
    else:
        r_na = missing
    plain_nan = missing & ~r_na
    out_of_range = (~missing) & ((flat >= 2_147_483_648.0) | (flat <= -2_147_483_648.0))
    usable = ~missing & ~out_of_range
    out[missing | out_of_range] = np.int32(_NA)
    if np.any(usable):
        out[usable] = np.trunc(flat[usable]).astype(np.int32)
    return out, bool(np.any(plain_nan)), bool(np.any(out_of_range))


def _ints_to_i32(flat: np.ndarray):
    flat = np.ascontiguousarray(flat, dtype=np.int64)
    out = np.empty(flat.shape, dtype=np.int32)
    bad = (flat < _INT_MIN) | (flat > _INT_MAX)
    out[bad] = np.int32(_NA)
    if np.any(~bad):
        out[~bad] = flat[~bad].astype(np.int32)
    return out, False, bool(np.any(bad))


def _strings_to_i32(texts):
    coercion = False
    ranged = False
    out = np.empty(len(texts), dtype=np.int32)
    for index, text in enumerate(texts):
        if text == "":
            out[index] = np.int32(_NA)
            continue
        try:
            number = float(text)
        except ValueError:
            out[index] = np.int32(_NA)
            coercion = True
            continue
        converted, nan_warning, range_warning = _floats_to_i32(
            np.array([number], dtype=np.float64)
        )
        out[index] = converted[0]
        coercion = coercion or nan_warning
        ranged = ranged or range_warning
    return out, coercion, ranged


def _objects_to_i32(items):
    coercion = False
    ranged = False
    out = np.empty(len(items), dtype=np.int32)
    for index, item in enumerate(items):
        if isinstance(item, np.ndarray) and item.shape == ():
            item = item.item()
        if item is None:
            out[index] = np.int32(_NA)
            continue
        if isinstance(item, (list, tuple, dict)):
            out[index] = np.int32(_NA)
            coercion = True
            continue
        converted, item_coercion, item_range = _convert_integer(item)
        if converted.size != 1:
            out[index] = np.int32(_NA)
            coercion = True
            continue
        out[index] = converted.reshape(-1)[0]
        coercion = coercion or item_coercion
        ranged = ranged or item_range
    return out, coercion, ranged


def _coerce_numeric(values) -> np.ndarray:
    """R ``as.numeric`` for a length argument."""
    converted, coercion = _convert_numeric(values)
    if coercion:
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=3)
    return converted


def _convert_numeric(values):
    if values is None:
        return np.zeros(0, dtype=np.float64), False
    if isinstance(values, (bool, np.bool_)):
        return np.array([1.0 if bool(values) else 0.0], dtype=np.float64), False
    if isinstance(values, (int, np.integer)) and not isinstance(values, bool):
        return np.array([float(int(values))], dtype=np.float64), False
    if isinstance(values, (float, np.floating)):
        return np.array([float(values)], dtype=np.float64), False
    if isinstance(values, str):
        return _strings_to_f64([values])
    if isinstance(values, (complex, np.complexfloating)):
        return np.array([np.nan], dtype=np.float64), True

    try:
        array = np.asarray(values)
    except (TypeError, ValueError) as err:
        raise ValueError("Argument 'length' must be a single numeric") from err
    if array.ndim == 0:
        return _convert_numeric(array.item())
    if array.dtype.kind in "SU":
        return _strings_to_f64([str(item) for item in array.ravel(order="F")])
    if array.dtype == object:
        return _objects_to_f64(list(array.ravel(order="F")))
    if array.dtype == bool or array.dtype.kind == "b":
        flat = np.ravel(array, order="F")
        return flat.astype(np.float64), False
    if np.issubdtype(array.dtype, np.number):
        return np.ascontiguousarray(np.ravel(array, order="F"), dtype=np.float64), False
    return np.array([np.nan], dtype=np.float64), True


def _strings_to_f64(texts):
    coercion = False
    out = np.empty(len(texts), dtype=np.float64)
    for index, text in enumerate(texts):
        if text == "":
            out[index] = np.nan
            coercion = True
            continue
        try:
            out[index] = float(text)
        except ValueError:
            out[index] = np.nan
            coercion = True
    return out, coercion


def _objects_to_f64(items):
    coercion = False
    out = np.empty(len(items), dtype=np.float64)
    for index, item in enumerate(items):
        if isinstance(item, np.ndarray) and item.shape == ():
            item = item.item()
        if item is None or (isinstance(item, float) and math.isnan(item)):
            out[index] = np.nan
            continue
        converted, item_coercion = _convert_numeric(item)
        if converted.size != 1:
            out[index] = np.nan
            coercion = True
            continue
        out[index] = converted.reshape(-1)[0]
        coercion = coercion or item_coercion
    return out, coercion
