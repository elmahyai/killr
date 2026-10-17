"""Lagged row and column differences, ported from matrixStats."""

from __future__ import annotations

import math
import warnings

import numpy as np
import rowdiffs as _rowdiffs

from matrixstats._values import as_logical, prepare_idxs

_I32_MIN = int(np.iinfo(np.int32).min)
_I32_MAX = int(np.iinfo(np.int32).max)
_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647


def rowDiffs(x, rows=None, cols=None, lag=1, differences=1, dim=None, use_names=True):
    """Lagged differences across each row.

    Mirrors ``matrixStats::rowDiffs``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``dim`` is ``dim.``: a one-dimensional
    ``x`` is filled in column-major order. Integer ``x`` returns int32 and
    the subtraction wraps. Double missing values are NaN. ``use_names`` is
    accepted and the result is a plain array.
    """
    return _diffs(x, rows, cols, lag, differences, dim, use_names, by_row=True)


def colDiffs(x, rows=None, cols=None, lag=1, differences=1, dim=None, use_names=True):
    """Lagged differences down each column.

    Mirrors ``matrixStats::colDiffs``. Arguments match :func:`rowDiffs`.
    """
    return _diffs(x, rows, cols, lag, differences, dim, use_names, by_row=False)


def _diffs(x, rows, cols, lag, differences, dim, use_names, by_row):
    storage, matrix = _prepare_matrix(x, dim)
    lag_i = _as_positive_r_integer(lag, "lag")
    differences_i = _as_positive_r_integer(differences, "differences")
    as_logical(use_names, "use_names")
    row_kind, row_index = prepare_idxs(rows)
    col_kind, col_index = prepare_idxs(cols)
    if storage == "double":
        if by_row:
            return _rowdiffs.row_diffs_f64(
                matrix, row_index, col_index, row_kind, col_kind, lag_i, differences_i
            )
        return _rowdiffs.col_diffs_f64(
            matrix, row_index, col_index, row_kind, col_kind, lag_i, differences_i
        )
    if by_row:
        return _rowdiffs.row_diffs_i32(
            matrix, row_index, col_index, row_kind, col_kind, lag_i, differences_i
        )
    return _rowdiffs.col_diffs_i32(
        matrix, row_index, col_index, row_kind, col_kind, lag_i, differences_i
    )


def _prepare_matrix(x, dim):
    storage, values = _as_storage(x)
    if dim is None:
        if values.ndim != 2:
            raise ValueError("Argument 'dim.' must be an integer vector of length two")
        return storage, _contiguous_2d(values)

    dim_arr = np.asarray(dim)
    if dim_arr.ndim > 1 or dim_arr.size != 2 or not np.issubdtype(dim_arr.dtype, np.integer):
        raise ValueError("Argument 'dim.' must be an integer vector of length two")
    nrow = int(dim_arr.reshape(-1)[0])
    ncol = int(dim_arr.reshape(-1)[1])
    if nrow < 0:
        raise ValueError(
            f"Argument 'dim.' specifies a negative number of rows (dim.[1]): {nrow}"
        )
    if ncol < 0:
        raise ValueError(
            f"Argument 'dim.' specifies a negative number of columns (dim.[2]): {ncol}"
        )
    if values.ndim == 0:
        values = values.reshape(1)
    if nrow * ncol != values.size:
        raise ValueError(
            "Argument 'dim.' does not match length of argument 'x': "
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
        raise ValueError("Argument 'x' cannot be logical")
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return _integer_values(np.array([int(x)], dtype=np.int64))
    if isinstance(x, (float, np.floating)):
        return "double", np.array([float(x)], dtype=np.float64)

    array = np.asarray(x)
    if array.dtype.kind in "SU":
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'character'"
        )
    if np.issubdtype(array.dtype, np.complexfloating):
        raise ValueError(
            "Argument 'x' must be of type logical, integer or numeric, not 'complex'"
        )
    if array.dtype == object:
        from matrixstats._values import prepare_x

        storage, flat = prepare_x(array)
        if storage == "logical":
            raise ValueError("Argument 'x' cannot be logical")
        shape = array.shape if array.ndim > 0 else (flat.size,)
        return storage, np.reshape(flat, shape, order="F")
    if array.dtype == np.bool_:
        raise ValueError("Argument 'x' cannot be logical")
    if np.issubdtype(array.dtype, np.floating):
        if array.dtype == np.float64:
            return "double", array
        return "double", np.asarray(array, dtype=np.float64)
    if np.issubdtype(array.dtype, np.integer):
        return _integer_values(array)
    raise ValueError(
        f"Argument 'x' must be of type logical, integer or numeric, not '{array.dtype.name}'"
    )


def _integer_values(array):
    if array.dtype == np.uint64:
        return "double", np.asarray(array, dtype=np.float64)
    as_i64 = np.asarray(array, dtype=np.int64)
    if as_i64.size:
        smallest = int(as_i64.min())
        largest = int(as_i64.max())
        if smallest < _I32_MIN or largest > _I32_MAX:
            return "double", np.asarray(array, dtype=np.float64)
    if array.dtype == np.int32:
        return "integer", array
    return "integer", np.ascontiguousarray(as_i64, dtype=np.int32)


def _contiguous_2d(values):
    if values.flags.c_contiguous or values.flags.f_contiguous:
        return values
    return np.ascontiguousarray(values)


def _as_positive_r_integer(value, name: str) -> int:
    """R's ``as.integer`` on the first element, then the positive check."""
    if value is None:
        raise ValueError(f"Argument '{name}' must be a positive integer")
    array = np.asarray(value)
    if array.size == 0:
        raise ValueError(f"Argument '{name}' must be a positive integer")
    raw = array.reshape(-1)[0]
    try:
        number = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Argument '{name}' must be a positive integer") from exc
    out_of_range = math.isinf(number) or (
        math.isfinite(number) and (number > _INT_MAX or number <= _INT_MIN)
    )
    if out_of_range:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            RuntimeWarning,
            stacklevel=3,
        )
    if not math.isfinite(number) or number > _INT_MAX or number <= _INT_MIN:
        raise ValueError(f"Argument '{name}' must be a positive integer")
    integer = int(math.trunc(number))
    if integer < 1:
        raise ValueError(f"Argument '{name}' must be a positive integer")
    return integer
