"""Row-major matrix indexes to column-major indexes, from matrixStats."""

from __future__ import annotations

import math

import numpy as np

import indexbyrow as _indexbyrow

_NA = -2_147_483_648
_INT_MIN = -2_147_483_647
_INT_MAX = 2_147_483_647

__all__ = ["indexByRow"]


def indexByRow(dim, idxs=None):
    """Translate row-major matrix indexes into column-major indexes.

    Mirrors ``matrixStats::indexByRow``. ``dim`` is a length-two vector, the
    template matrix in column-major order. ``idxs`` is 1-based and counts
    cells in row-major order. ``None`` visits every cell and returns those
    column-major positions, in that same visit order.

    Zero and negative indexes are errors. This function does not drop or
    exclude them. A numeric value is truncated toward zero. A value outside
    the 32-bit integer range becomes an integer NA, which the index check
    rejects. A two-dimensional ``dim`` is the defunct matrix form.
    """
    if isinstance(dim, np.ndarray) and dim.ndim == 2:
        raise ValueError(
            "indexByRow(x) where 'x' is a matrix is defunct. "
            "Use indexByRow(dim(x)) instead."
        )
    dims = _as_integer(dim, "dim")
    if dims.size != 2:
        raise ValueError("Argument 'dim' must be an integer vector of length two")
    nrow = int(dims[0])
    ncol = int(dims[1])
    if idxs is None:
        return _indexbyrow.index_by_row(nrow, ncol, None)
    chosen = np.ascontiguousarray(_as_integer(idxs, "idxs"))
    return _indexbyrow.index_by_row(nrow, ncol, chosen)


def _as_integer(values, name):
    """R ``as.integer`` for the values this function accepts."""
    if isinstance(values, (bool, np.bool_)):
        return np.array([1 if bool(values) else 0], dtype=np.int32)
    if isinstance(values, (int, np.integer)) and not isinstance(values, bool):
        return np.array([_scalar_to_i32(values)], dtype=np.int32)
    if isinstance(values, (float, np.floating)):
        return np.array([_scalar_to_i32(values)], dtype=np.int32)
    if isinstance(values, str):
        return np.array([_NA], dtype=np.int32)

    try:
        array = np.asarray(values)
    except (TypeError, ValueError) as err:
        raise ValueError(_type_message(name)) from err
    if array.dtype.kind in "SU":
        out = np.full(np.ravel(array, order="F").shape, np.int32(_NA), dtype=np.int32)
        return out
    if array.ndim == 0:
        array = array.reshape(1)
    else:
        array = np.ravel(array, order="F")
    if array.dtype == object:
        return np.array([_scalar_to_i32(item, name) for item in array], dtype=np.int32)
    if array.dtype == np.bool_:
        out = np.zeros(array.shape, dtype=np.int32)
        out[array] = 1
        return np.ascontiguousarray(out)
    if np.issubdtype(array.dtype, np.unsignedinteger):
        out = np.full(array.shape, np.int32(_NA), dtype=np.int32)
        ok = array <= _INT_MAX
        out[ok] = array[ok].astype(np.int32)
        return np.ascontiguousarray(out)
    if np.issubdtype(array.dtype, np.integer):
        wide = np.ascontiguousarray(array, dtype=np.int64)
        out = np.full(wide.shape, np.int32(_NA), dtype=np.int32)
        ok = (wide >= _INT_MIN) & (wide <= _INT_MAX)
        out[ok] = wide[ok].astype(np.int32)
        return out
    if np.issubdtype(array.dtype, np.floating):
        wide = np.ascontiguousarray(array, dtype=np.float64)
        truncated = np.trunc(wide)
        out = np.full(wide.shape, np.int32(_NA), dtype=np.int32)
        ok = np.isfinite(truncated) & (truncated >= _INT_MIN) & (truncated <= _INT_MAX)
        out[ok] = truncated[ok].astype(np.int32)
        return out
    raise ValueError(_type_message(name))


def _scalar_to_i32(value, name="idxs"):
    if value is None:
        return _NA
    if isinstance(value, (bool, np.bool_)):
        return 1 if bool(value) else 0
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        number = int(value)
        if number < _INT_MIN or number > _INT_MAX:
            return _NA
        return number
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if not math.isfinite(number):
            return _NA
        truncated = math.trunc(number)
        if truncated < _INT_MIN or truncated > _INT_MAX:
            return _NA
        return truncated
    if isinstance(value, str):
        return _NA
    raise ValueError(_type_message(name))


def _type_message(name):
    if name == "dim":
        return "Argument 'dim' must be an integer vector of length two"
    return "Argument 'idxs' must be NULL or a vector"
