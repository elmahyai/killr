"""Cumulative row and column sums, ported from matrixStats."""

from __future__ import annotations

import warnings

import numpy as np
import rowcumsums as _rowcumsums

from matrixstats._values import as_logical, prepare_idxs, prepare_x

_I32_MIN = int(np.iinfo(np.int32).min)
_I32_MAX = int(np.iinfo(np.int32).max)
_OVERFLOW = (
    "Integer overflow. Detected one or more elements whose absolute values "
    "were out of the range [-2147483647,2147483647] that can be used to for "
    "integers. Such values are set to NA_integer_."
)


def rowCumsums(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative sum of each row.

    Mirrors ``matrixStats::rowCumsums``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``dim`` is ``dim.``: a one-dimensional
    ``x`` is filled in column-major order. Logical input returns int32.
    Double missing values are NaN. ``use_names`` is accepted and the result
    is a plain array of the same shape as the selected matrix.
    """
    return _cumsums(x, rows, cols, dim, use_names, by_row=True)


def colCumsums(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative sum of each column.

    Mirrors ``matrixStats::colCumsums``. Arguments match :func:`rowCumsums`.
    """
    return _cumsums(x, rows, cols, dim, use_names, by_row=False)


def _cumsums(x, rows, cols, dim, use_names, by_row):
    as_logical(use_names, "use_names")
    storage, matrix = _prepare_matrix(x, dim)
    row_kind, row_index = prepare_idxs(rows)
    col_kind, col_index = prepare_idxs(cols)
    if storage == "double":
        if by_row:
            return _rowcumsums.row_cumsums_f64(
                matrix, row_index, col_index, row_kind, col_kind
            )
        return _rowcumsums.col_cumsums_f64(
            matrix, row_index, col_index, row_kind, col_kind
        )
    if by_row:
        result, overflow = _rowcumsums.row_cumsums_i32(
            matrix, row_index, col_index, row_kind, col_kind
        )
    else:
        result, overflow = _rowcumsums.col_cumsums_i32(
            matrix, row_index, col_index, row_kind, col_kind
        )
    if overflow:
        warnings.warn(_OVERFLOW, UserWarning, stacklevel=3)
    return result


def _prepare_matrix(x, dim):
    storage, values = _as_storage(x)
    if dim is None:
        if values.ndim != 2:
            raise ValueError("Argument 'dim' must be an integer vector of length two")
        return storage, _contiguous_2d(values)

    dim_arr = np.asarray(dim)
    if dim_arr.ndim > 1 or dim_arr.size != 2 or not np.issubdtype(dim_arr.dtype, np.integer):
        raise ValueError("Argument 'dim' must be an integer vector of length two")
    nrow = int(dim_arr.reshape(-1)[0])
    ncol = int(dim_arr.reshape(-1)[1])
    if nrow < 0:
        raise ValueError(
            f"Argument 'dim' specifies a negative number of rows (dim[1]): {nrow}"
        )
    if ncol < 0:
        raise ValueError(
            f"Argument 'dim' specifies a negative number of columns (dim[2]): {ncol}"
        )
    if values.ndim == 0:
        values = values.reshape(1)
    if nrow * ncol != values.size:
        raise ValueError(
            "Argument 'dim' does not match length of argument 'x': "
            f"{nrow} * {ncol} != {values.size}"
        )
    if values.ndim == 1:
        flat = np.ascontiguousarray(values)
        return storage, np.reshape(flat, (nrow, ncol), order="F")
    if values.shape == (nrow, ncol):
        return storage, _contiguous_2d(values)
    flat = np.ravel(np.asfortranarray(values), order="F")
    return storage, np.reshape(flat, (nrow, ncol), order="F")


def _as_storage(x):
    if isinstance(x, (bool, np.bool_)):
        return "logical", np.array([1 if bool(x) else 0], dtype=np.int32)
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return _integer_values(np.array([int(x)], dtype=np.int64))
    if isinstance(x, (float, np.floating)):
        return "double", np.array([float(x)], dtype=np.float64)

    array = np.asarray(x)
    if array.dtype.kind in "SU":
        raise ValueError("Argument 'x' is not numeric or logical: character")
    if array.dtype == object:
        storage, flat = prepare_x(array)
        shape = array.shape if array.ndim > 0 else (flat.size,)
        return storage, np.reshape(flat, shape, order="F")
    if array.dtype == np.bool_:
        out = np.zeros(array.shape, dtype=np.int32)
        out[array] = 1
        return "logical", out
    if np.issubdtype(array.dtype, np.floating):
        if array.dtype == np.float64:
            return "double", array
        return "double", np.ascontiguousarray(array, dtype=np.float64)
    if np.issubdtype(array.dtype, np.integer):
        return _integer_values(array)
    raise ValueError(f"Argument 'x' is not numeric or logical: {array.dtype.name}")


def _integer_values(array):
    if array.dtype == np.uint64:
        return "double", np.ascontiguousarray(array, dtype=np.float64)
    as_i64 = np.asarray(array, dtype=np.int64)
    if as_i64.size:
        smallest = int(as_i64.min())
        largest = int(as_i64.max())
        if smallest < _I32_MIN or largest > _I32_MAX:
            return "double", np.ascontiguousarray(array, dtype=np.float64)
    if array.dtype == np.int32:
        return "integer", array
    return "integer", np.ascontiguousarray(as_i64, dtype=np.int32)


def _contiguous_2d(values):
    if values.flags.c_contiguous or values.flags.f_contiguous:
        return values
    return np.ascontiguousarray(values)
