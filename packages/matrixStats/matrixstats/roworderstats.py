"""Row and column order statistics, ported from matrixStats."""

from __future__ import annotations

import math
import warnings

import numpy as np
import colorderstats as _colorderstats
import roworderstats as _roworderstats

_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_MISSING = object()

__all__ = ["rowOrderStats", "colOrderStats"]


def rowOrderStats(x, rows=None, cols=None, which=_MISSING, dim=None, use_names=True):
    """Order statistic of each row.

    Mirrors ``matrixStats::rowOrderStats``. ``which`` is the 1-based order,
    counted on the selected columns. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``dim`` is ``dim.``: a one-dimensional
    ``x`` is filled in column-major order. A missing value anywhere in ``x``
    is an error. Integer input stays int32. ``use_names`` does not change
    the numbers.
    """
    return _order_stats(x, rows, cols, which, dim, use_names, by_row=True)


def colOrderStats(x, rows=None, cols=None, which=_MISSING, dim=None, use_names=True):
    """Order statistic of each column.

    Mirrors ``matrixStats::colOrderStats``. ``which`` is counted on the
    selected rows. The other arguments match :func:`rowOrderStats`.
    """
    return _order_stats(x, rows, cols, which, dim, use_names, by_row=False)


def _order_stats(x, rows, cols, which, dim, use_names, by_row):
    if which is _MISSING:
        raise TypeError("missing required argument: 'which'")
    if _any_missing(x):
        raise ValueError("Argument 'x' must not contain missing values")
    matrix, integer = _prepare_matrix(x, dim)
    which_i = _as_which(which)
    _flag(use_names, "useNames")
    row_index, row_kind = _coerce_index(rows, "rows")
    col_index, col_kind = _coerce_index(cols, "cols")
    if integer:
        if by_row:
            return _roworderstats.row_order_stats_i32(
                matrix, which_i, row_index, row_kind, col_index, col_kind
            )
        return _colorderstats.col_order_stats_i32(
            matrix, which_i, row_index, row_kind, col_index, col_kind
        )
    if by_row:
        return _roworderstats.row_order_stats_f64(
            matrix, which_i, row_index, row_kind, col_index, col_kind
        )
    return _colorderstats.col_order_stats_f64(
        matrix, which_i, row_index, row_kind, col_index, col_kind
    )


def _any_missing(x) -> bool:
    if isinstance(x, (bool, np.bool_)):
        return False
    if isinstance(x, (float, np.floating)):
        return bool(math.isnan(float(x)))
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return int(x) == _INT_MIN
    if x is None:
        return True
    values = np.asarray(x)
    if values.dtype == object:
        for item in values.reshape(-1):
            if item is None:
                return True
            if isinstance(item, (float, np.floating)) and math.isnan(float(item)):
                return True
            if isinstance(item, (int, np.integer)) and not isinstance(item, bool):
                if int(item) == _INT_MIN:
                    return True
        return False
    if np.issubdtype(values.dtype, np.floating):
        return bool(values.size and np.isnan(values).any())
    if np.issubdtype(values.dtype, np.signedinteger):
        if values.dtype == np.uint64:
            return False
        as_i64 = np.asarray(values, dtype=np.int64)
        if as_i64.size == 0:
            return False
        smallest = int(as_i64.min())
        largest = int(as_i64.max())
        if smallest < _INT_MIN or largest > _INT_MAX:
            return False
        return bool(np.any(as_i64 == _INT_MIN))
    return False


def _flag(value, r_name):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        number = int(value)
        if number in (0, 1):
            return bool(number)
        raise ValueError(f"Argument '{r_name}' must be either TRUE or FALSE")
    arr = np.asarray(value)
    if arr.ndim > 1 or arr.size != 1:
        raise ValueError(f"Argument '{r_name}' must be a single value")
    item = arr.reshape(-1)[0]
    if isinstance(item, (bool, np.bool_)) or (
        arr.dtype == np.bool_ or np.issubdtype(arr.dtype, np.integer)
    ):
        return _flag(item.item() if hasattr(item, "item") else item, r_name)
    raise ValueError(f"Argument '{r_name}' must be a logical")


def _as_which(which) -> int:
    if isinstance(which, (bool, np.bool_)):
        return 1 if bool(which) else 0
    if isinstance(which, (int, np.integer)) and not isinstance(which, bool):
        return _int_which(int(which))
    if isinstance(which, (float, np.floating)):
        return _real_which(float(which))
    if which is None:
        raise ValueError("Argument 'which' must be a single number")
    array = np.asarray(which)
    if array.dtype.kind in "SU":
        if array.size != 1:
            raise ValueError("Argument 'which' must be a single number")
        raise ValueError("Argument 'which' must be a numeric number")
    if array.dtype == object:
        if array.size != 1:
            raise ValueError("Argument 'which' must be a single number")
        return _as_which(array.reshape(-1)[0])
    if array.size != 1:
        raise ValueError("Argument 'which' must be a single number")
    item = array.reshape(-1)[0]
    if array.dtype == np.bool_ or isinstance(item, (bool, np.bool_)):
        return 1 if bool(item) else 0
    if np.issubdtype(array.dtype, np.integer):
        return _int_which(int(item))
    if np.issubdtype(array.dtype, np.floating):
        return _real_which(float(item))
    raise ValueError("Argument 'which' must be a numeric number")


def _int_which(number: int) -> int:
    if number < _INT_MIN or number > _INT_MAX:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=3,
        )
        return _INT_MIN
    return number


def _real_which(number: float) -> int:
    if math.isnan(number):
        return _INT_MIN
    if number >= (_INT_MAX + 1.0) or number <= _INT_MIN:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=3,
        )
        return _INT_MIN
    return int(math.trunc(number))


def _prepare_matrix(x, dim):
    values = np.asarray(x)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim > 2:
        raise ValueError("Argument 'x' must be a matrix or a vector")
    if values.dtype == np.bool_ or (
        values.dtype == object and _object_is_logical(values)
    ):
        raise ValueError("Argument 'x' cannot be logical")
    if values.dtype.kind in "SU" or (
        values.dtype == object and _object_is_character(values)
    ):
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'character'"
        )
    if np.issubdtype(values.dtype, np.complexfloating):
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'complex'"
        )
    if np.issubdtype(values.dtype, np.integer):
        values = _as_i32(values)
        integer = np.issubdtype(values.dtype, np.integer)
    elif np.issubdtype(values.dtype, np.floating):
        integer = False
        values = values.astype(np.float64, copy=False)
    elif values.dtype == object:
        integer, values = _from_object_numbers(values)
    else:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not "
            f"'{values.dtype.name}'"
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


def _object_is_logical(values) -> bool:
    items = list(values.reshape(-1))
    return bool(items) and all(isinstance(item, (bool, np.bool_)) for item in items)


def _object_is_character(values) -> bool:
    return any(isinstance(item, str) for item in values.reshape(-1))


def _from_object_numbers(values):
    items = list(values.reshape(-1))
    if any(isinstance(item, (float, np.floating)) for item in items):
        out = np.empty(len(items), dtype=np.float64)
        for i, item in enumerate(items):
            out[i] = float(item)
        return False, np.reshape(out, values.shape, order="F") if values.ndim else out
    out = np.empty(len(items), dtype=np.int32)
    for i, item in enumerate(items):
        if isinstance(item, (bool, np.bool_)):
            out[i] = 1 if item else 0
        else:
            out[i] = int(item)
    shaped = np.reshape(out, values.shape, order="F") if values.ndim else out
    return True, shaped


def _as_i32(values):
    if values.dtype == np.int32:
        return values
    if np.issubdtype(values.dtype, np.unsignedinteger):
        if values.size and np.any(values > _INT_MAX):
            return values.astype(np.float64)
        return values.astype(np.int32)
    wide = values.astype(np.int64, copy=False)
    if values.size and (np.any(wide < _INT_MIN) or np.any(wide > _INT_MAX)):
        return values.astype(np.float64)
    return wide.astype(np.int32)


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
        if not np.isfinite(raw) or raw >= (_INT_MAX + 1.0) or raw <= _INT_MIN:
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
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
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
