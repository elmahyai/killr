"""Row and column cumulative products, ported from matrixStats."""

from __future__ import annotations

import warnings

import numpy as np
import rowcumprods as _rowcumprods

_OVERFLOW = (
    "Integer overflow. Detected one or more elements whose absolute values "
    "were out of the range [-2147483647,2147483647] that can be used to for "
    "integers. Such values are set to NA_integer_."
)
_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647

__all__ = ["rowCumprods", "colCumprods"]


def rowCumprods(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative product of each row.

    Mirrors ``matrixStats::rowCumprods``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``dim`` is ``dim.``: a one-dimensional
    ``x`` is filled in column-major order. The result is a matrix with one
    row per selected row and one column per selected column. Logical input
    returns int32. ``use_names`` does not change the numbers.
    """
    return _cumprods(x, rows, cols, dim, use_names, by_row=True)


def colCumprods(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative product of each column.

    Mirrors ``matrixStats::colCumprods``. Arguments match :func:`rowCumprods`.
    """
    return _cumprods(x, rows, cols, dim, use_names, by_row=False)


def _cumprods(x, rows, cols, dim, use_names, by_row):
    _flag(use_names)
    matrix, integer = _prepare_matrix(x, dim)
    row_index, row_kind = _coerce_index(rows, "rows")
    col_index, col_kind = _coerce_index(cols, "cols")
    if integer:
        fn = _rowcumprods.row_cumprods_i32 if by_row else _rowcumprods.col_cumprods_i32
        result, overflow = fn(matrix, row_index, row_kind, col_index, col_kind)
        if overflow:
            warnings.warn(_OVERFLOW, UserWarning, stacklevel=3)
        return result
    fn = _rowcumprods.row_cumprods_f64 if by_row else _rowcumprods.col_cumprods_f64
    return fn(matrix, row_index, row_kind, col_index, col_kind)


def _flag(value):
    if isinstance(value, (bool, np.bool_)):
        return
    raise ValueError("Argument 'useNames' must be either TRUE or FALSE")


def _prepare_matrix(x, dim):
    values = np.asarray(x)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim > 2:
        raise ValueError("Argument 'x' must be a matrix or a vector")

    if values.dtype == np.bool_:
        integer = True
        values = values.astype(np.int32, copy=False)
    elif np.issubdtype(values.dtype, np.integer):
        integer = True
        values = _as_i32(values)
    elif np.issubdtype(values.dtype, np.floating):
        integer = False
        values = values.astype(np.float64, copy=False)
    else:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not "
            f"'{_type_name(values.dtype)}'"
        )

    if dim is None:
        if values.ndim != 2:
            raise ValueError("Argument 'dim.' must be an integer vector of length two")
        return _contiguous_2d(values), integer

    nrow, ncol = _parse_dim(dim, int(values.size))
    if values.ndim == 1:
        flat = np.ascontiguousarray(values)
        return np.reshape(flat, (nrow, ncol), order="F"), integer
    if values.shape == (nrow, ncol):
        return _contiguous_2d(values), integer
    flat = np.ravel(np.asfortranarray(values), order="F")
    return np.reshape(flat, (nrow, ncol), order="F"), integer


def _as_i32(values):
    if values.dtype == np.int32:
        return values
    if values.size:
        as_float = values.astype(np.float64, copy=False)
        if np.any(as_float < _INT_MIN) or np.any(as_float > _INT_MAX):
            raise ValueError(
                "Argument 'x' must be of type logical, integer or numeric, not "
                "an integer outside the R integer range"
            )
    return values.astype(np.int32, copy=False)


def _type_name(dtype):
    if dtype.kind in ("U", "S"):
        return "character"
    if dtype.kind == "c":
        return "complex"
    return dtype.name


def _parse_dim(dim, length):
    vals = np.asarray(dim)
    if vals.ndim == 0:
        vals = vals.reshape(1)
    if vals.ndim != 1 or vals.size != 2 or not (
        np.issubdtype(vals.dtype, np.integer) or np.issubdtype(vals.dtype, np.floating)
    ):
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    nums = []
    for raw in np.asarray(vals, dtype=np.float64).reshape(-1):
        if not np.isfinite(raw) or raw > _INT_MAX or raw < _INT_MIN:
            nums.append(_INT_MIN)
        else:
            nums.append(int(np.trunc(raw)))
    nrow, ncol = nums
    if nrow < 0:
        raise ValueError(
            f"Argument 'dim.' specifies a negative number of rows (dim.[1]): {nrow}"
        )
    if ncol < 0:
        raise ValueError(
            f"Argument 'dim.' specifies a negative number of columns (dim.[2]): {ncol}"
        )
    if nrow * ncol != length:
        raise ValueError(
            "Argument 'dim.' does not match length of argument 'x': "
            f"{nrow} * {ncol} != {length}"
        )
    return nrow, ncol


def _contiguous_2d(values):
    if values.flags.c_contiguous or values.flags.f_contiguous:
        return values
    return np.ascontiguousarray(values)


def _coerce_index(index, name):
    if index is None:
        return None, "all"
    logical = _logical_codes(index, name)
    if logical is not None:
        return np.ascontiguousarray(logical, dtype=np.int8), "logical"
    if isinstance(index, (int, np.integer)):
        return np.asarray([int(index)], dtype=np.int64), "int"
    if isinstance(index, float):
        return np.asarray([float(index)], dtype=np.float64), "real"
    if isinstance(index, (list, tuple)) and any(v is None for v in index):
        return (
            np.ascontiguousarray(
                [np.nan if v is None else float(v) for v in index],
                dtype=np.float64,
            ),
            "real",
        )

    arr = np.asarray(index)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError(f"Argument '{name}' must be a vector")
    if arr.dtype == object:
        if any(v is None for v in arr.reshape(-1)):
            return (
                np.ascontiguousarray(
                    [np.nan if v is None else float(v) for v in arr.reshape(-1)],
                    dtype=np.float64,
                ),
                "real",
            )
        raise ValueError("idxs can only be integer, numeric, or logical")
    if np.issubdtype(arr.dtype, np.integer):
        return np.ascontiguousarray(arr, dtype=np.int64), "int"
    if np.issubdtype(arr.dtype, np.floating):
        return np.ascontiguousarray(arr, dtype=np.float64), "real"
    raise ValueError("idxs can only be integer, numeric, or logical")


def _logical_codes(index, name):
    if isinstance(index, (bool, np.bool_)):
        return np.array([1 if index else 0], dtype=np.int8)
    if isinstance(index, np.ndarray) and index.dtype == np.bool_:
        array = np.atleast_1d(index)
        if array.ndim != 1:
            raise ValueError(f"Argument '{name}' must be a vector")
        return np.ascontiguousarray(array, dtype=np.int8)
    if isinstance(index, (list, tuple)):
        values = list(index)
    else:
        return None
    if not values or not all(_is_logical_mark(v) for v in values):
        return None
    codes = np.empty(len(values), dtype=np.int8)
    for i, value in enumerate(values):
        if value is None:
            codes[i] = -1
        else:
            codes[i] = 1 if value else 0
    return codes


def _is_logical_mark(value):
    return value is None or isinstance(value, (bool, np.bool_))
