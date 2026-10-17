"""Row and column means, ported from matrixStats ``rowMeans2``."""

from __future__ import annotations

import numpy as np
from rowmeans2 import means2

_R_NAMES = {
    "na_rm": "na.rm",
    "refine": "refine",
    "use_names": "useNames",
}


def rowMeans2(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    refine=True,
    dim=None,
    use_names=True,
):
    """Mean of each row.

    ``x`` is a 2-d array whose axis 0 is rows and axis 1 is columns, matching
    the printed R matrix, or a 1-d vector with ``dim`` filled column-major.
    ``rows`` and ``cols`` are 1-based; None selects the whole margin.
    ``na_rm`` drops NaN. ``refine`` turns on the two-pass residual correction
    for floating-point data. The result is a plain float64 vector.
    """
    return _means(x, rows, cols, na_rm, refine, dim, use_names, True)


def colMeans2(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    refine=True,
    dim=None,
    use_names=True,
):
    """Mean of each column.

    Arguments match :func:`rowMeans2`. The result length is the number of
    selected columns.
    """
    return _means(x, rows, cols, na_rm, refine, dim, use_names, False)


def _means(x, rows, cols, na_rm, refine, dim, use_names, by_row: bool):
    _flag(na_rm, "na_rm")
    refine_on = _flag(refine, "refine")
    _flag(use_names, "use_names")

    arr = np.asarray(x)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.dtype == np.bool_ or np.issubdtype(arr.dtype, np.integer):
        # The C dispatcher forces refine off for integer and logical input.
        refine_on = False
    elif not np.issubdtype(arr.dtype, np.floating):
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
    return means2(
        flat,
        nrow,
        ncol,
        column_major,
        row_values,
        row_logical,
        col_values,
        col_logical,
        bool(na_rm),
        refine_on,
        by_row,
    )


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
    """Contiguous float64 storage and whether it is column-major."""
    if arr.ndim == 1:
        return np.ascontiguousarray(arr, dtype=np.float64), True
    same_shape = arr.shape == (nrow, ncol)
    if same_shape and arr.dtype == np.float64 and arr.flags.c_contiguous:
        return np.ascontiguousarray(arr.reshape(-1, order="C")), False
    if (
        same_shape
        and arr.dtype == np.float64
        and arr.flags.f_contiguous
        and not arr.flags.c_contiguous
    ):
        return np.ascontiguousarray(arr.reshape(-1, order="F")), True
    fort = np.asfortranarray(arr, dtype=np.float64)
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
