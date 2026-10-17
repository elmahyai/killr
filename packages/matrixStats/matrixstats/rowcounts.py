"""Row counts, column counts, and count, ported from matrixStats."""

from __future__ import annotations

import math
import warnings

import numpy as np

import colcounts as _colcounts
import rowcounts as _rowcounts

_WHAT_ALL = 0
_WHAT_ANY = 1
_WHAT_COUNT = 2
_NA_INTEGER = -2_147_483_648
_INT_MAX = 2_147_483_647
_NA_COUNT = float(-(2**63))

__all__ = ["rowCounts", "colCounts", "count"]


def rowCounts(x, rows=None, cols=None, value=True, na_rm=False, dim=None, use_names=True):
    """Count how many times ``value`` occurs in each row.

    Mirrors ``matrixStats::rowCounts``. ``rows`` and ``cols`` are 1-based.
    ``None`` uses every row or column. ``dim`` is ``dim.``: a one-dimensional
    ``x`` is filled in column-major order. Double missing values are ``nan``.
    Integer missing values are ``None`` or ``-2147483648``. The result is
    int32, and an integer missing count is ``-2147483648``. ``use_names`` does
    not change the numbers.
    """
    return _matrix_question(
        x, rows, cols, value, na_rm, dim, use_names, _WHAT_COUNT, by_row=True
    )


def colCounts(x, rows=None, cols=None, value=True, na_rm=False, dim=None, use_names=True):
    """Count how many times ``value`` occurs in each column.

    Mirrors ``matrixStats::colCounts``. Arguments match :func:`rowCounts`.
    The result has one integer per selected column.
    """
    return _matrix_question(
        x, rows, cols, value, na_rm, dim, use_names, _WHAT_COUNT, by_row=False
    )


def count(x, idxs=None, value=True, na_rm=False):
    """Count how many times ``value`` occurs in a vector.

    Mirrors ``matrixStats::count``. ``idxs`` is 1-based. ``None`` selects
    every element. A positive index past the end is a missing element. The
    result is a Python ``int`` when the count is at most ``.Machine$integer.max``,
    a ``float`` when it is larger, and ``None`` when the count is missing.
    """
    _flag(na_rm, "na.rm")
    values, storage = _prepare_vector(x)
    coerced = _coerce_value(value, storage, length_style="scalar", on_character="na")
    index, kind = _coerce_index(idxs, "idxs")
    if storage == "double":
        raw = _colcounts.count_f64(values, _WHAT_COUNT, float(coerced), na_rm, index, kind)
    else:
        raw = _colcounts.count_i32(values, _WHAT_COUNT, int(coerced), na_rm, index, kind)
    return _finish_scalar(raw)


def _matrix_question(x, rows, cols, value, na_rm, dim, use_names, what, by_row, *, length_style="scalar", on_character="na"):
    _flag(na_rm, "na.rm")
    _flag(use_names, "useNames")
    matrix, storage = _prepare_matrix(x, dim)
    coerced = _coerce_value(value, storage, length_style=length_style, on_character=on_character)
    return _call_matrix(matrix, storage, rows, cols, coerced, na_rm, what, by_row)


def _vector_question(x, idxs, value, na_rm, what, *, length_style="single", on_character="error"):
    _flag(na_rm, "na.rm")
    values, storage = _prepare_vector(x)
    coerced = _coerce_value(value, storage, length_style=length_style, on_character=on_character)
    index, kind = _coerce_index(idxs, "idxs")
    if storage == "double":
        raw = _colcounts.count_f64(values, what, float(coerced), na_rm, index, kind)
    else:
        raw = _colcounts.count_i32(values, what, int(coerced), na_rm, index, kind)
    return _finish_scalar(raw)


def _call_matrix(matrix, storage, rows, cols, coerced, na_rm, what, by_row):
    row_index, row_kind = _coerce_index(rows, "rows")
    col_index, col_kind = _coerce_index(cols, "cols")
    if storage == "double":
        fn = _rowcounts.row_counts_f64 if by_row else _colcounts.col_counts_f64
        return fn(matrix, what, float(coerced), na_rm, row_index, row_kind, col_index, col_kind)
    fn = _rowcounts.row_counts_i32 if by_row else _colcounts.col_counts_i32
    return fn(matrix, what, int(coerced), na_rm, row_index, row_kind, col_index, col_kind)


def _finish_scalar(raw):
    if raw == _NA_COUNT or (isinstance(raw, float) and math.isnan(raw)):
        return None
    if raw > _INT_MAX:
        return float(raw)
    return int(raw)


def _flag(value, r_name):
    if isinstance(value, np.ndarray):
        if value.size != 1:
            raise ValueError(f"Argument '{r_name}' must be a single value")
        value = value.reshape(-1)[0]
        if isinstance(value, np.generic):
            value = value.item()
    if isinstance(value, (bool, np.bool_)):
        return
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        number = int(value)
        if number in (0, 1):
            return
        raise ValueError(f"Argument '{r_name}' must be either TRUE or FALSE")
    if isinstance(value, (list, tuple)):
        if len(value) != 1:
            raise ValueError(f"Argument '{r_name}' must be a single value")
        return _flag(value[0], r_name)
    raise ValueError(f"Argument '{r_name}' must be a logical")


def _prepare_matrix(x, dim):
    values, storage = _as_array(x, what="matrix")
    if dim is None:
        if values.ndim != 2:
            raise ValueError("Argument 'dim.' must be an integer vector of length two")
        return _contiguous_2d(values), storage
    nrow, ncol = _parse_dim(dim, int(values.size))
    if values.ndim == 1:
        flat = np.ascontiguousarray(values.reshape(-1))
        return np.reshape(flat, (nrow, ncol), order="F"), storage
    if values.shape == (nrow, ncol):
        return _contiguous_2d(values), storage
    flat = np.ravel(values, order="F")
    return np.reshape(np.ascontiguousarray(flat), (nrow, ncol), order="F"), storage


def _prepare_vector(x):
    if isinstance(x, np.ndarray) and x.ndim >= 2:
        raise ValueError(f"Argument 'x' is not a vector: {_mode_of(x)}")
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], (list, tuple, dict)):
        raise ValueError("Argument 'x' is not a vector: list")
    values, storage = _as_array(x, what="vector")
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim != 1:
        raise ValueError(f"Argument 'x' is not a vector: {_mode_of(x)}")
    if not values.flags.c_contiguous:
        values = np.ascontiguousarray(values)
    return values, storage


def _as_array(x, what):
    if isinstance(x, dict):
        kind = "list"
        raise ValueError(_shape_error(what, kind))
    if isinstance(x, (bool, np.bool_)):
        return np.array([1 if bool(x) else 0], dtype=np.int32), "logical"
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        return _fit_integer(np.array([int(x)], dtype=np.int64))
    if isinstance(x, (float, np.floating)):
        return np.array([float(x)], dtype=np.float64), "double"
    if isinstance(x, str):
        raise ValueError(_type_error("character"))
    if isinstance(x, (list, tuple)):
        if any(isinstance(item, (list, tuple, dict)) for item in x):
            raise ValueError(_shape_error(what, "list"))
        if any(item is None or isinstance(item, (bool, np.bool_, str)) for item in x):
            return _from_object(np.array(x, dtype=object))
        values = np.asarray(x)
    else:
        values = np.asarray(x)

    if values.dtype.kind in "SU":
        raise ValueError(_type_error("character"))
    if values.dtype.kind == "c":
        raise ValueError(_type_error("complex"))
    if values.ndim == 0:
        values = values.reshape(1)
    if values.ndim > 2:
        raise ValueError(_shape_error(what, _mode_of(values)))
    if values.dtype == object:
        return _from_object(values)
    if values.dtype == np.bool_:
        out = np.zeros(values.shape, dtype=np.int32)
        out[values] = 1
        return out, "logical"
    if np.issubdtype(values.dtype, np.floating):
        return values.astype(np.float64, copy=False), "double"
    if np.issubdtype(values.dtype, np.integer):
        return _fit_integer(values.astype(np.int64, copy=False))
    raise ValueError(_type_error(values.dtype.name))


def _from_object(values):
    flat = np.ravel(values, order="F")
    items = [flat[i] for i in range(flat.size)]
    kinds = set()
    for item in items:
        kind = _item_kind(item)
        if kind == "other":
            mode = "character" if isinstance(item, str) else type(item).__name__
            raise ValueError(_type_error(mode))
        kinds.add(kind)
    if "double" in kinds or _object_needs_double(items):
        out = np.empty(flat.size, dtype=np.float64)
        for i, item in enumerate(items):
            kind = _item_kind(item)
            if kind in ("missing", "double") and (item is None or (isinstance(item, (float, np.floating)) and math.isnan(float(item)))):
                out[i] = np.nan
            elif kind == "logical":
                out[i] = 1.0 if item else 0.0
            else:
                out[i] = float(item)
        storage = "double"
    elif "integer" in kinds:
        out = np.empty(flat.size, dtype=np.int32)
        for i, item in enumerate(items):
            kind = _item_kind(item)
            if kind == "missing":
                out[i] = _NA_INTEGER
            elif kind == "logical":
                out[i] = 1 if item else 0
            else:
                out[i] = int(item)
        storage = "integer"
    else:
        out = np.empty(flat.size, dtype=np.int32)
        for i, item in enumerate(items):
            if item is None:
                out[i] = _NA_INTEGER
            else:
                out[i] = 1 if item else 0
        storage = "logical"
    if values.ndim == 2:
        out = np.reshape(out, values.shape, order="F")
    return out, storage


def _object_needs_double(items):
    for item in items:
        if _item_kind(item) == "integer" and not _fits_i32(int(item)):
            return True
    return False


def _item_kind(value):
    if value is None:
        return "missing"
    if isinstance(value, (bool, np.bool_)):
        return "logical"
    if isinstance(value, (int, np.integer)):
        return "integer"
    if isinstance(value, (float, np.floating)):
        return "double"
    return "other"


def _fits_i32(value):
    return _NA_INTEGER <= int(value) <= _INT_MAX


def _fit_integer(values):
    if values.size:
        smallest = int(values.min())
        largest = int(values.max())
        if smallest < _NA_INTEGER or largest > _INT_MAX:
            raise ValueError(
                "Argument 'x' must be of type logical, integer or numeric, not "
                "an integer outside the R integer range"
            )
    return values.astype(np.int32, copy=False), "integer"


def _type_error(mode):
    return (
        "Argument 'x' must be of type logical, integer or numeric, not "
        f"'{mode}'"
    )


def _shape_error(what, mode):
    if what == "vector":
        return f"Argument 'x' is not a vector: {mode}"
    return f"Argument 'x' is not a matrix or a vector: {mode}"


def _mode_of(values):
    if isinstance(values, np.ndarray):
        if values.dtype == np.bool_:
            return "logical"
        if values.dtype.kind in "SU":
            return "character"
        if values.dtype.kind == "c":
            return "complex"
        if values.dtype == object:
            return "list"
        if np.issubdtype(values.dtype, np.integer) or np.issubdtype(values.dtype, np.floating):
            return "numeric"
    return "numeric"


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
        if not np.isfinite(raw) or raw > _INT_MAX or raw < _NA_INTEGER:
            nums.append(_NA_INTEGER)
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
    if values.size == 0:
        return values
    if values.flags.c_contiguous or values.flags.f_contiguous:
        return values
    return np.ascontiguousarray(values)


def _coerce_value(value, storage, *, length_style, on_character):
    item, size = _value_item(value)
    if size != 1:
        if length_style == "scalar":
            raise ValueError(f"Argument 'value' is not a scalar: {size:.0f}")
        raise ValueError("Argument 'value' must be a single value")
    if isinstance(item, str):
        if on_character == "error":
            raise ValueError("Argument 'value' must be a numeric or a logical value")
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=3)
        return _missing(storage)
    if item is None:
        return _missing(storage)
    if isinstance(item, (bool, np.bool_)):
        if storage == "double":
            return 1.0 if bool(item) else 0.0
        return 1 if bool(item) else 0
    if isinstance(item, (int, np.integer)):
        return _coerce_int(int(item), storage)
    if isinstance(item, (float, np.floating)):
        return _coerce_float(float(item), storage)
    raise ValueError("Argument 'value' must be a numeric or a logical value")


def _value_item(value):
    if isinstance(value, str):
        return value, 1
    if isinstance(value, np.ndarray):
        if value.ndim == 0:
            item = value.reshape(1)[0]
            return _plain(item), 1
        return (_plain(value.reshape(-1)[0]) if value.size else None), int(value.size)
    if isinstance(value, (list, tuple)):
        if len(value) == 1:
            return _plain(value[0]), 1
        return (None, len(value))
    return value, 1


def _plain(item):
    if isinstance(item, np.generic):
        if isinstance(item, np.bool_):
            return bool(item)
        return item.item()
    return item


def _missing(storage):
    if storage == "double":
        return float("nan")
    return _NA_INTEGER


def _coerce_int(number, storage):
    if storage == "double":
        if number == _NA_INTEGER:
            return float("nan")
        return float(number)
    if storage == "logical":
        if number == _NA_INTEGER:
            return _NA_INTEGER
        return 0 if number == 0 else 1
    if number == _NA_INTEGER:
        return _NA_INTEGER
    if number > _INT_MAX or number < _NA_INTEGER:
        warnings.warn(
            "NAs introduced by coercion to integer range", UserWarning, stacklevel=3
        )
        return _NA_INTEGER
    return number


def _coerce_float(number, storage):
    if storage == "double":
        return number
    if storage == "logical":
        if math.isnan(number):
            return _NA_INTEGER
        return 0 if number == 0.0 else 1
    if math.isnan(number):
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=3)
        return _NA_INTEGER
    if math.isinf(number) or number > _INT_MAX or number <= _NA_INTEGER:
        warnings.warn(
            "NAs introduced by coercion to integer range", UserWarning, stacklevel=3
        )
        return _NA_INTEGER
    return int(math.trunc(number))


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


def _is_logical_scalar(value):
    if isinstance(value, (bool, np.bool_)):
        return True
    if value is None:
        return True
    if isinstance(value, np.ndarray) and value.dtype == np.bool_ and value.size == 1:
        return True
    return False


def _logical_is_na(value):
    return value is None


def _is_true(value):
    if isinstance(value, np.ndarray):
        value = value.reshape(-1)[0]
    return bool(value)


def _as_logical_counts(counts):
    counts = np.asarray(counts, dtype=np.int32)
    out = np.empty(counts.shape, dtype=object)
    missing = counts == _NA_INTEGER
    out[missing] = None
    if np.any(~missing):
        out[~missing] = np.asarray(counts[~missing] != 0, dtype=object)
    return out


def _counts_equal(counts, target):
    counts = np.asarray(counts, dtype=np.int32)
    out = np.empty(counts.shape, dtype=object)
    missing = counts == _NA_INTEGER
    out[missing] = None
    if np.any(~missing):
        out[~missing] = np.asarray(counts[~missing] == target, dtype=object)
    return out


def _scalar_logical(count):
    if count is None:
        return None
    return bool(int(count) != 0)


def _scalar_equal(count, target):
    if count is None:
        return None
    return bool(int(count) == target)
