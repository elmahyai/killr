"""Row and column log-sum-exp, ported from matrixStats."""

from __future__ import annotations

import numpy as np
import rowlogsumexps as _rowlogsumexps


def rowLogSumExps(lx, rows=None, cols=None, na_rm=False, dim=None, use_names=True):
    """Log-sum-exp of each row.

    Mirrors ``matrixStats::rowLogSumExps``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``na_rm`` is ``na.rm``. ``dim`` is
    ``dim.``: when ``lx`` is one-dimensional it is filled in column-major
    order. A missing double is NaN. The result is a plain float64 vector.
    """
    return _log_sum_exps(lx, rows, cols, na_rm, dim, use_names, by_row=True)


def colLogSumExps(lx, rows=None, cols=None, na_rm=False, dim=None, use_names=True):
    """Log-sum-exp of each column.

    Mirrors ``matrixStats::colLogSumExps``. Arguments match
    :func:`rowLogSumExps`.
    """
    return _log_sum_exps(lx, rows, cols, na_rm, dim, use_names, by_row=False)


def _log_sum_exps(lx, rows, cols, na_rm, dim, use_names, by_row):
    _check_flag(na_rm, "na_rm")
    _check_flag(use_names, "use_names")
    matrix = _prepare_matrix(lx, dim)
    row_index = _coerce_index(rows, "rows")
    col_index = _coerce_index(cols, "cols")
    na_rm = bool(na_rm)
    if by_row:
        return _rowlogsumexps.row_log_sum_exps(matrix, row_index, col_index, na_rm)
    return _rowlogsumexps.col_log_sum_exps(matrix, row_index, col_index, na_rm)


def _check_flag(value, name):
    if isinstance(value, (bool, np.bool_)):
        return
    raise TypeError(f"Argument '{name}' must be either TRUE or FALSE")


def _prepare_matrix(lx, dim):
    values = np.asarray(lx)
    if values.dtype == np.bool_:
        values = values.astype(np.float64, copy=False)
    elif np.issubdtype(values.dtype, np.integer):
        values = values.astype(np.float64, copy=False)
    elif np.issubdtype(values.dtype, np.floating):
        values = values.astype(np.float64, copy=False)
    elif values.dtype.kind in "SU":
        raise ValueError(
            "Argument 'lx' must be of type logical, integer or numeric, not 'character'"
        )
    else:
        raise ValueError(
            "Argument 'lx' must be of type logical, integer or numeric, "
            f"not '{values.dtype.name}'"
        )
    if values.ndim > 2:
        raise ValueError("Argument 'lx' must be a matrix or a vector")

    if dim is None:
        if values.ndim != 2:
            raise ValueError("Argument 'dim' must be an integer vector of length two")
        return _contiguous_2d(values)

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
    if nrow * ncol != values.size:
        raise ValueError(
            "Argument 'dim' does not match length of argument 'x': "
            f"{nrow} * {ncol} != {values.size}"
        )
    if values.ndim == 1:
        flat = np.ascontiguousarray(values, dtype=np.float64)
        return np.reshape(flat, (nrow, ncol), order="F")
    if values.shape == (nrow, ncol):
        return _contiguous_2d(values)
    flat = np.ravel(np.asfortranarray(values), order="F")
    return np.reshape(flat, (nrow, ncol), order="F")


def _contiguous_2d(values):
    if values.flags.c_contiguous or values.flags.f_contiguous:
        return values
    return np.ascontiguousarray(values)


def _coerce_index(index, name):
    if index is None:
        return None
    if isinstance(index, bool):
        return np.asarray([index], dtype=np.bool_)
    if isinstance(index, (int, np.integer)):
        return np.asarray([int(index)], dtype=np.int64)
    if isinstance(index, float):
        return np.asarray([float(index)], dtype=np.float64)

    arr = np.asarray(index)
    if arr.ndim == 0:
        arr = arr.reshape(1)
    if arr.ndim != 1:
        raise ValueError(f"Argument '{name}' must be a vector")
    if arr.dtype == np.bool_:
        return np.ascontiguousarray(arr)
    if np.issubdtype(arr.dtype, np.integer):
        return np.ascontiguousarray(arr, dtype=np.int64)
    if np.issubdtype(arr.dtype, np.floating):
        return np.ascontiguousarray(arr, dtype=np.float64)
    raise ValueError("idxs can only be integer, numeric, or logical")
