"""Cumulative minima by row and by column, ported from matrixStats."""

from __future__ import annotations

import numpy as np
import rowcummins as _rowcummins

_R_NAMES = {
    "use_names": "useNames",
}

_INT32_MIN = np.iinfo(np.int32).min
_INT32_MAX = np.iinfo(np.int32).max


def rowCummins(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative minimum of each row.

    ``x`` is a 2-d array whose axis 0 is rows and axis 1 is columns, matching
    the printed R matrix, or a 1-d vector with ``dim`` filled column-major.
    ``rows`` and ``cols`` are 1-based; None selects the whole margin. The
    result is a matrix of the selected shape. A floating value is the minimum
    of the cells seen so far in that row. NaN is R's double NA: that cell and
    every cell to its right are NaN. Integer and logical input return int32.
    Logical values are 0 and 1. The int32 value -2147483648 is R's integer NA
    and stops the run the same way.
    """
    return _cummins(x, rows, cols, dim, use_names, True)


def colCummins(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative minimum of each column.

    Arguments match :func:`rowCummins`. The minimum runs down each column.
    A missing value makes that cell and every cell below it missing.
    """
    return _cummins(x, rows, cols, dim, use_names, False)


def _cummins(x, rows, cols, dim, use_names, by_row: bool):
    _flag(use_names, "use_names")

    arr = np.asarray(x)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    integer = _is_integer(arr)
    if integer:
        arr = _as_int32(arr)
    elif np.issubdtype(arr.dtype, np.floating):
        if arr.dtype != np.float64:
            arr = arr.astype(np.float64)
    else:
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not "
            f"'{arr.dtype}'"
        )
    if arr.ndim not in (1, 2):
        raise ValueError("Argument 'x' must be a matrix or a vector")

    nrow, ncol = _dimensions(arr, dim)
    flat, column_major = _buffer(arr, nrow, ncol)
    row_values, row_logical = _indices(rows, "rows")
    col_values, col_logical = _indices(cols, "cols")
    if integer:
        return _rowcummins.cummins_i32(
            flat,
            nrow,
            ncol,
            column_major,
            row_values,
            row_logical,
            col_values,
            col_logical,
            by_row,
        )
    return _rowcummins.cummins_f64(
        flat,
        nrow,
        ncol,
        column_major,
        row_values,
        row_logical,
        col_values,
        col_logical,
        by_row,
    )


def _is_integer(arr: np.ndarray) -> bool:
    return arr.dtype == np.bool_ or np.issubdtype(arr.dtype, np.integer)


def _as_int32(arr: np.ndarray) -> np.ndarray:
    if arr.dtype == np.bool_:
        return arr.astype(np.int32)
    if arr.dtype == np.int32:
        return arr
    if np.issubdtype(arr.dtype, np.unsignedinteger):
        if arr.size and np.any(arr > _INT32_MAX):
            raise ValueError(
                "Argument 'x' integer values do not fit in a 32-bit integer"
            )
        return arr.astype(np.int32)
    wide = arr.astype(np.int64, copy=False)
    if arr.size and (np.any(wide < _INT32_MIN) or np.any(wide > _INT32_MAX)):
        raise ValueError(
            "Argument 'x' integer values do not fit in a 32-bit integer"
        )
    return wide.astype(np.int32)


def _flag(value, name: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    label = _R_NAMES[name]
    raise ValueError(f"Argument '{label}' must be either TRUE or FALSE")


def _dimensions(arr: np.ndarray, dim) -> tuple[int, int]:
    if arr.ndim == 1:
        if dim is None:
            raise ValueError("Argument 'dim.' must be an integer vector of length two")
        return _parse_dim(dim, int(arr.size))
    if dim is None:
        return int(arr.shape[0]), int(arr.shape[1])
    return _parse_dim(dim, int(arr.size))


def _parse_dim(dim, length: int) -> tuple[int, int]:
    vals = np.asarray(dim)
    if vals.ndim == 0:
        vals = vals.reshape(1)
    if vals.ndim != 1 or vals.size != 2:
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    if not (
        np.issubdtype(vals.dtype, np.integer) or np.issubdtype(vals.dtype, np.floating)
    ):
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    floats = vals.astype(np.float64)
    if not np.all(np.isfinite(floats)):
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    nums = np.trunc(floats).astype(np.int64)
    nrow = int(nums[0])
    ncol = int(nums[1])
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


def _buffer(arr: np.ndarray, nrow: int, ncol: int) -> tuple[np.ndarray, bool]:
    """Contiguous storage and whether it is column-major."""
    if arr.ndim == 1:
        return np.ascontiguousarray(arr), True
    same_shape = arr.shape == (nrow, ncol)
    if same_shape and arr.flags.c_contiguous:
        return np.ascontiguousarray(arr.reshape(-1, order="C")), False
    if same_shape and arr.flags.f_contiguous and not arr.flags.c_contiguous:
        return np.ascontiguousarray(arr.reshape(-1, order="F")), True
    fort = np.asfortranarray(arr)
    return np.ascontiguousarray(fort.reshape(-1, order="F")), True


def _indices(value, name: str) -> tuple[np.ndarray | None, bool]:
    if value is None:
        return None, False
    arr = np.asarray(value)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError(f"Argument '{name}' must be a vector")
    if arr.dtype == np.bool_:
        return np.ascontiguousarray(arr, dtype=np.float64), True
    if not (
        np.issubdtype(arr.dtype, np.integer) or np.issubdtype(arr.dtype, np.floating)
    ):
        raise ValueError("idxs can only be integer, numeric, or logical")
    return np.ascontiguousarray(arr, dtype=np.float64), False
