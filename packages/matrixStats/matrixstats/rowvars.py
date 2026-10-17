"""Row and column variances, ported from matrixStats."""

from __future__ import annotations

import numpy as np
import rowvars as _rowvars

_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_NA_INTEGER = np.int32(_INT_MIN)

__all__ = ["rowVars", "colVars"]


def rowVars(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    refine=True,
    center=None,
    dim=None,
    use_names=True,
):
    """Sample variance of each row.

    Mirrors ``matrixStats::rowVars``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``na_rm`` is ``na.rm``. ``dim`` is
    ``dim.``: a one-dimensional ``x`` is filled in column-major order.
    ``refine`` adds the residual pass from the C code when ``center`` is
    omitted and ``x`` is floating point. ``center`` is an optional vector of
    row means; a length-1 value is an error. The result is a float64 vector.
    """
    return _vars(x, rows, cols, na_rm, refine, center, dim, use_names, True)


def colVars(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    refine=True,
    center=None,
    dim=None,
    use_names=True,
):
    """Sample variance of each column.

    Mirrors ``matrixStats::colVars``. Arguments match :func:`rowVars`.
    ``center`` has one value per column. The result length is the number of
    selected columns.
    """
    return _vars(x, rows, cols, na_rm, refine, center, dim, use_names, False)


def _vars(x, rows, cols, na_rm, refine, center, dim, use_names, by_row):
    na_rm = _flag(na_rm, "na.rm")
    refine_on = _flag(refine, "refine")
    _flag(use_names, "useNames")
    matrix, integer = _prepare_matrix(x, dim)
    if integer:
        matrix = _integer_to_float(matrix)
        refine_on = False
    elif matrix.dtype != np.float64:
        matrix = np.asarray(matrix, dtype=np.float64)
    row_index, row_kind = _coerce_index(rows, "rows")
    col_index, col_kind = _coerce_index(cols, "cols")
    center_arr = _prepare_center(center, matrix.shape, by_row, rows if by_row else cols)
    return _rowvars.vars_f64(
        matrix,
        na_rm,
        refine_on,
        by_row,
        center_arr,
        row_index,
        row_kind,
        col_index,
        col_kind,
    )


def _prepare_center(center, shape, by_row, margin_index):
    if center is None:
        return None
    values = _as_center(center)
    margin = int(shape[0] if by_row else shape[1])
    which = "rows" if by_row else "columns"
    if values.size != margin:
        if values.size == 1 and margin_index is None:
            raise ValueError(
                "[matrixStats (>= 0.58.0)] Argument 'center' should be of the "
                f"same length as number of {which} of 'x'. Use of a scalar value "
                f"is defunct: 1 != {margin} "
                "(See also ?matrixStats::matrixStats.options)"
            )
        raise ValueError(
            "Argument 'center' should be of the same length as number of "
            f"{which} of 'x': {int(values.size)} != {margin}"
        )
    return np.ascontiguousarray(values, dtype=np.float64)


def _as_center(center):
    values = np.asarray(center)
    if values.dtype == np.bool_:
        flat = np.ravel(values, order="F") if values.ndim > 1 else np.ravel(values)
        return flat.astype(np.float64)
    if values.ndim == 0:
        values = values.reshape(1)
    elif values.ndim > 1:
        values = np.ravel(values, order="F")
    else:
        values = np.ravel(values)
    if np.issubdtype(values.dtype, np.integer):
        wide = values.astype(np.int64, copy=False)
        out = wide.astype(np.float64)
        out[wide == _INT_MIN] = np.nan
        return out
    if np.issubdtype(values.dtype, np.floating):
        return np.asarray(values, dtype=np.float64)
    raise ValueError("non-numeric argument to binary operator")


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


def _prepare_matrix(x, dim):
    values = np.asarray(x)
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim > 2:
        raise ValueError("Argument 'x' must be a matrix or a vector")
    if values.dtype == np.bool_:
        raise ValueError("Argument 'x' cannot be logical")
    if np.issubdtype(values.dtype, np.integer):
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


def _integer_to_float(values):
    out = values.astype(np.float64)
    missing = values == _NA_INTEGER
    if np.any(missing):
        out[missing] = np.nan
    return out


def _as_i32(values):
    if values.dtype == np.int32:
        return values
    if np.issubdtype(values.dtype, np.unsignedinteger):
        if values.size and np.any(values > _INT_MAX):
            raise ValueError(
                "Argument 'x' integer values do not fit in a 32-bit integer"
            )
        return values.astype(np.int32)
    wide = values.astype(np.int64, copy=False)
    if values.size and (np.any(wide < _INT_MIN) or np.any(wide > _INT_MAX)):
        raise ValueError(
            "Argument 'x' integer values do not fit in a 32-bit integer"
        )
    return wide.astype(np.int32)


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
