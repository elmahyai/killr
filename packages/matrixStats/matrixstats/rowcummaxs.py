"""Row and column cumulative maxima, ported from matrixStats ``rowCummaxs``."""

from __future__ import annotations

import numpy as np
from rowcummaxs import cummaxs_f64, cummaxs_i32

_R_NAMES = {
    "use_names": "useNames",
}

_I32_MIN = np.iinfo(np.int32).min
_I32_MAX = np.iinfo(np.int32).max

__all__ = ["colCummaxs", "rowCummaxs"]


def rowCummaxs(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative maximum of each row.

    ``x`` is a 2-d array whose axis 0 is rows and axis 1 is columns, matching
    the printed R matrix, or a 1-d vector with ``dim`` filled column-major.
    ``rows`` and ``cols`` are 1-based; None selects the whole margin. A missing
    value ends that row: every later column on the row is missing too. Logical
    input returns int32, with True as 1 and False as 0. Integer input returns
    int32, and the R integer NA value ``-2147483648`` is missing. Floating
    input returns float64, and NaN is missing.
    """
    return _cummaxs(x, rows, cols, dim, use_names, True)


def colCummaxs(x, rows=None, cols=None, dim=None, use_names=True):
    """Cumulative maximum of each column.

    Arguments match :func:`rowCummaxs`. A missing value ends that column:
    every later row in the column is missing too. The result has one row per
    selected row and one column per selected column.
    """
    return _cummaxs(x, rows, cols, dim, use_names, False)


def _cummaxs(x, rows, cols, dim, use_names, by_row: bool):
    _flag(use_names, "use_names")

    arr = np.asarray(x)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    kind = _kind(arr)
    if arr.ndim not in (1, 2):
        raise ValueError("Argument 'x' must be a matrix or a vector")

    nrow, ncol = _dimensions(arr, dim)
    if kind == "i":
        _fit_int32(arr)
    flat, column_major = _buffer(arr, nrow, ncol, np.float64 if kind == "f" else np.int32)
    row_values, row_logical = _indices(rows, "rows")
    col_values, col_logical = _indices(cols, "cols")
    if kind == "f":
        values, out_nrow, out_ncol = cummaxs_f64(
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
    else:
        values, out_nrow, out_ncol = cummaxs_i32(
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
    return np.reshape(np.asarray(values), (out_nrow, out_ncol), order="F")


def _kind(arr: np.ndarray) -> str:
    if arr.dtype == np.bool_:
        return "i"
    if np.issubdtype(arr.dtype, np.integer):
        return "i"
    if np.issubdtype(arr.dtype, np.floating):
        return "f"
    raise ValueError(
        "Argument 'x' must be of type logical, integer or numeric, not "
        f"'{arr.dtype}'"
    )


def _fit_int32(arr: np.ndarray) -> None:
    if arr.dtype == np.bool_ or arr.dtype == np.int32 or arr.size == 0:
        return
    if np.issubdtype(arr.dtype, np.unsignedinteger):
        fits = bool(np.all(arr <= _I32_MAX))
    else:
        fits = bool(np.all((arr >= _I32_MIN) & (arr <= _I32_MAX)))
    if not fits:
        raise ValueError("Argument 'x' integer values do not fit in a 32-bit integer")


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


def _buffer(arr: np.ndarray, nrow: int, ncol: int, dtype) -> tuple[np.ndarray, bool]:
    """Contiguous storage and whether it is column-major."""
    want = np.dtype(dtype)
    if arr.ndim == 1:
        return np.ascontiguousarray(arr, dtype=want), True
    same_shape = arr.shape == (nrow, ncol)
    if same_shape and arr.flags.c_contiguous and arr.dtype == want:
        return np.ravel(arr, order="C"), False
    if (
        same_shape
        and arr.flags.f_contiguous
        and not arr.flags.c_contiguous
        and arr.dtype == want
    ):
        return np.ravel(arr, order="F"), True
    if same_shape and arr.flags.c_contiguous:
        return np.ascontiguousarray(np.ravel(arr, order="C"), dtype=want), False
    if same_shape and arr.flags.f_contiguous and not arr.flags.c_contiguous:
        return np.ascontiguousarray(np.ravel(arr, order="F"), dtype=want), True
    fort = np.asfortranarray(arr)
    return np.ascontiguousarray(np.ravel(fort, order="F"), dtype=want), True


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
