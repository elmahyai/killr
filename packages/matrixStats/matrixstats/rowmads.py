"""Row and column median absolute deviations, ported from matrixStats."""

from __future__ import annotations

import numpy as np
import rowmads as _rowmads

_INT_MIN = -2_147_483_648
_INT_MAX = 2_147_483_647
_NA_REAL = np.float64(np.array(np.uint64(0x7FF00000000007A2).view(np.float64)))

__all__ = ["rowMads", "colMads"]


def rowMads(
    x,
    rows=None,
    cols=None,
    center=None,
    constant=1.4826,
    na_rm=False,
    dim=None,
    use_names=True,
):
    """Median absolute deviation of each row.

    Mirrors ``matrixStats::rowMads`` and ``stats::mad``. ``rows`` and
    ``cols`` are 1-based. ``None`` uses every row or column. ``constant``
    defaults to 1.4826. ``na_rm`` is ``na.rm``. ``dim`` is ``dim.``: a
    one-dimensional ``x`` is filled in column-major order. A margin with one
    counted value is 0. A missing value becomes R's NA.
    """
    return _mads(
        x,
        rows,
        cols,
        center,
        constant,
        na_rm,
        dim,
        use_names,
        by_row=True,
    )


def colMads(
    x,
    rows=None,
    cols=None,
    center=None,
    constant=1.4826,
    na_rm=False,
    dim=None,
    use_names=True,
):
    """Median absolute deviation of each column.

    Mirrors ``matrixStats::colMads``. Arguments match :func:`rowMads`.
    """
    return _mads(
        x,
        rows,
        cols,
        center,
        constant,
        na_rm,
        dim,
        use_names,
        by_row=False,
    )


def _mads(x, rows, cols, center, constant, na_rm, dim, use_names, by_row):
    na_rm = _flag(na_rm, "na.rm")
    scale = _scale(constant)
    matrix, integer = _prepare_matrix(x, dim)
    row_index, row_kind = _coerce_index(rows, "rows")
    col_index, col_kind = _coerce_index(cols, "cols")
    if center is None:
        result = _call(
            matrix,
            integer,
            by_row,
            na_rm,
            scale,
            None,
            False,
            row_index,
            row_kind,
            col_index,
            col_kind,
        )
    else:
        margin = "rows" if by_row else "columns"
        index_is_none = rows is None if by_row else cols is None
        n_margin = matrix.shape[0] if by_row else matrix.shape[1]
        center_values, integer_center = _prepare_center(
            center, n_margin, margin, index_is_none
        )
        if integer and integer_center:
            result = _call(
                matrix,
                True,
                by_row,
                na_rm,
                scale,
                center_values,
                by_row,
                row_index,
                row_kind,
                col_index,
                col_kind,
            )
        else:
            if integer:
                matrix = _promote_integer(matrix)
            result = _call(
                matrix,
                False,
                by_row,
                na_rm,
                scale,
                center_values,
                False,
                row_index,
                row_kind,
                col_index,
                col_kind,
            )
    _flag(use_names, "useNames")
    return result


def _call(
    matrix,
    integer,
    by_row,
    na_rm,
    scale,
    center,
    check_i32_overflow,
    row_index,
    row_kind,
    col_index,
    col_kind,
):
    if integer:
        return _rowmads.mads_i32(
            matrix,
            by_row,
            na_rm,
            scale,
            center,
            check_i32_overflow,
            row_index,
            row_kind,
            col_index,
            col_kind,
        )
    return _rowmads.mads_f64(
        matrix,
        by_row,
        na_rm,
        scale,
        center,
        row_index,
        row_kind,
        col_index,
        col_kind,
    )


def _scale(constant):
    if isinstance(constant, (bool, np.bool_)):
        return float(bool(constant))
    if isinstance(constant, (int, np.integer)) and not isinstance(constant, bool):
        return float(int(constant))
    if isinstance(constant, (float, np.floating)):
        return float(constant)
    if isinstance(constant, str):
        try:
            return float(constant)
        except ValueError as exc:
            raise ValueError("Argument 'constant' must be a numeric scale") from exc
    values = np.asarray(constant)
    if values.dtype.kind in "SU":
        if values.size != 1:
            raise ValueError("Argument 'constant' must be a numeric scale")
        return _scale(values.reshape(-1)[0].item())
    if values.dtype == object or values.size == 0:
        raise ValueError("Argument 'constant' must be a numeric scale")
    if values.dtype == np.bool_ or np.issubdtype(values.dtype, np.number):
        return float(np.asarray(values.reshape(-1)[0], dtype=np.float64))
    raise ValueError("Argument 'constant' must be a numeric scale")


def _prepare_center(center, n_margin, margin, index_is_none):
    integer_typed, values = _center_values(center)
    if values.size != n_margin:
        if values.size == 1 and index_is_none:
            raise ValueError(
                "[matrixStats (>= 0.58.0)] Argument 'center' should be of the same "
                f"length as number of {margin} of 'x'. Use of a scalar value is "
                f"defunct: {values.size} != {n_margin} "
                "(See also ?matrixStats::matrixStats.options)"
            )
        raise ValueError(
            "Argument 'center' should be of the same length as number of "
            f"{margin} of 'x': {values.size} != {n_margin}"
        )
    return np.ascontiguousarray(values, dtype=np.float64), integer_typed


def _center_values(center):
    if isinstance(center, (bool, np.bool_)):
        return False, np.array([1.0 if center else 0.0], dtype=np.float64)
    if isinstance(center, (int, np.integer)) and not isinstance(center, bool):
        number = int(center)
        if _INT_MIN <= number <= _INT_MAX:
            return True, np.array([_int_to_center(number)], dtype=np.float64)
        return False, np.array([float(number)], dtype=np.float64)
    if isinstance(center, (float, np.floating)):
        return False, np.array([np.float64(center)], dtype=np.float64)
    if isinstance(center, (list, tuple)):
        return _center_from_sequence(list(center))
    values = np.asarray(center)
    if values.ndim == 0:
        return _center_values(values.item())
    if values.dtype == object:
        return _center_from_sequence(list(np.ravel(values, order="F")))
    flat = np.ravel(values, order="F")
    if flat.dtype == np.bool_:
        out = np.zeros(flat.shape, dtype=np.float64)
        out[flat] = 1.0
        return False, out
    if np.issubdtype(flat.dtype, np.integer):
        return True, _integer_center_array(flat)
    if np.issubdtype(flat.dtype, np.floating):
        return False, np.ascontiguousarray(flat, dtype=np.float64)
    raise ValueError("Argument 'center' must be numeric")


def _center_from_sequence(values):
    if any(isinstance(item, (float, np.floating)) and not isinstance(item, (bool, np.bool_)) for item in values):
        out = np.empty(len(values), dtype=np.float64)
        for i, item in enumerate(values):
            if item is None:
                out[i] = _NA_REAL
            else:
                out[i] = np.float64(item)
        return False, out
    if all(_is_int_or_missing(item) for item in values):
        if any(_outside_i32(item) for item in values):
            out = np.empty(len(values), dtype=np.float64)
            for i, item in enumerate(values):
                out[i] = _NA_REAL if item is None else float(item)
            return False, out
        out = np.empty(len(values), dtype=np.float64)
        for i, item in enumerate(values):
            out[i] = _NA_REAL if item is None else _int_to_center(int(item))
        return True, out
    raise ValueError("Argument 'center' must be numeric")


def _integer_center_array(values):
    wide = np.asarray(values)
    if wide.dtype != np.int64:
        wide = wide.astype(np.int64, copy=False)
    if wide.size and (np.any(wide < _INT_MIN) or np.any(wide > _INT_MAX)):
        raise ValueError("Argument 'center' integer values do not fit in a 32-bit integer")
    out = wide.astype(np.float64)
    missing = wide == _INT_MIN
    if np.any(missing):
        out = np.array(out, dtype=np.float64, copy=True)
        out[missing] = _NA_REAL
    return out


def _int_to_center(number):
    if number == _INT_MIN:
        return np.float64(_NA_REAL)
    return np.float64(number)


def _is_int_or_missing(value):
    return value is None or (isinstance(value, (int, np.integer)) and not isinstance(value, bool))


def _outside_i32(value):
    return value is not None and (int(value) < _INT_MIN or int(value) > _INT_MAX)


def _promote_integer(matrix):
    out = matrix.astype(np.float64)
    missing = matrix == np.int32(_INT_MIN)
    if np.any(missing):
        out = np.array(out, copy=True)
        out[missing] = _NA_REAL
    return out


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
