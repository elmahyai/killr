"""Row and column tabulation, ported from matrixStats 1.5.0.

``rowTabulates`` and ``colTabulates`` are R. They subset with ``[``, then
count each requested value. There is no ``.Call`` in ``R/rowTabulates.R``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from matrixstats._values import as_logical

_NA = -2_147_483_648
_INT_MIN = -2_147_483_647
_INT_MAX = 2_147_483_647
_RANGE = "NAs introduced by coercion to integer range"
_COERCE = "NAs introduced by coercion"
_RAW = "out-of-range values treated as 0 in coercion to raw"

__all__ = ["colTabulates", "rowTabulates"]


def rowTabulates(x, rows=None, cols=None, values=None, use_names=True):
    """Count values within each row.

    Mirrors ``matrixStats::rowTabulates``. ``rows`` and ``cols`` are 1-based
    subscripts, and ``None`` keeps every row or column. ``values=None`` counts
    each observed value. The columns are those values in ascending order, with
    a missing-value column last when one occurs. An explicit ``values`` vector
    keeps its order. The result is an int32 array with one row per selected
    row. Names are not attached.

    ``x`` is an integer matrix, a logical matrix, or a raw matrix stored as
    ``uint8``. A logical missing value is ``None``. An integer missing value
    is ``None`` or R's integer NA sentinel. A double matrix is rejected.
    """
    return _tabulate(x, rows, cols, values, use_names, by_row=True)


def colTabulates(x, rows=None, cols=None, values=None, use_names=True):
    """Count values within each column.

    Mirrors ``matrixStats::colTabulates``. Arguments match :func:`rowTabulates`.
    The result has one row per selected column.
    """
    return _tabulate(x, rows, cols, values, use_names, by_row=False)


def _tabulate(x, rows, cols, values, use_names, by_row):
    storage, data = _prepare_matrix(x)
    as_logical(use_names, "use_names")
    row_idx = None if rows is None else _resolve_index(rows, data.shape[0])
    col_idx = None if cols is None else _resolve_index(cols, data.shape[1])
    fill = 0 if storage == "raw" else _NA
    data = _subset(data, row_idx, col_idx, fill)
    if not by_row:
        data = np.transpose(data)
    data = np.ascontiguousarray(data)
    if storage == "raw":
        data = data.astype(np.int32, copy=False)
    if values is None:
        targets = _observed(data, storage)
    else:
        targets = [_coerce(kind, value, storage) for kind, value in _iter_scalars(values)]
    return _counts(data, targets)


def _prepare_matrix(x):
    if x is None:
        raise ValueError("Argument 'x' is not integer, logical, or raw: NULL")
    if isinstance(x, str):
        raise ValueError("Argument 'x' is not integer, logical, or raw: character")
    if isinstance(x, (bool, np.bool_)):
        raise ValueError("non-numeric matrix extent")
    if isinstance(x, (int, np.integer)) and not isinstance(x, bool):
        raise ValueError("non-numeric matrix extent")
    if isinstance(x, (float, np.floating)):
        raise ValueError("Argument 'x' is not integer, logical, or raw: double")
    if isinstance(x, (complex, np.complexfloating)):
        raise ValueError("Argument 'x' is not integer, logical, or raw: complex")

    array = np.asarray(x)
    if array.dtype == object:
        return _from_object(array)
    return _from_array(array)


def _from_array(array):
    storage = _array_storage(array)
    if storage in ("double", "character", "complex"):
        raise ValueError(f"Argument 'x' is not integer, logical, or raw: {storage}")
    if storage == "reject":
        raise ValueError(f"Argument 'x' is not integer, logical, or raw: {array.dtype.name}")
    _require_matrix(array)
    if storage == "raw":
        return "raw", array
    if storage == "logical":
        out = np.zeros(array.shape, dtype=np.int32)
        out[array] = 1
        return "logical", out
    return "integer", _as_i32(array)


def _from_object(array):
    _require_matrix(array)
    items = array.ravel(order="C").tolist()
    kinds = {_scalar_kind(value) for value in items}
    if "character" in kinds:
        raise ValueError("Argument 'x' is not integer, logical, or raw: character")
    if "other" in kinds:
        alien = next(value for value in items if _scalar_kind(value) == "other")
        raise ValueError(
            f"Argument 'x' is not integer, logical, or raw: {type(alien).__name__}"
        )
    if "double" in kinds:
        raise ValueError("Argument 'x' is not integer, logical, or raw: double")
    if "raw" in kinds and kinds <= {"raw", "missing"}:
        out = np.zeros(array.shape, dtype=np.uint8)
        for index, value in enumerate(items):
            out.ravel()[index] = 0 if value is None else value[0]
        return "raw", out.reshape(array.shape)
    if "integer" in kinds or "raw" in kinds:
        out = np.empty(items.__len__(), dtype=np.int32)
        for index, value in enumerate(items):
            out[index] = _object_integer(value)
        return "integer", out.reshape(array.shape)
    out = np.full(items.__len__(), _NA, dtype=np.int32)
    for index, value in enumerate(items):
        if value is not None:
            out[index] = 1 if value else 0
    return "logical", out.reshape(array.shape)


def _object_integer(value):
    if value is None:
        return _NA
    if isinstance(value, (bool, np.bool_)):
        return 1 if value else 0
    if isinstance(value, (bytes, bytearray)):
        return int(value[0])
    number = int(value)
    if number < _NA or number > _INT_MAX:
        raise ValueError("Argument 'x' is not integer, logical, or raw: double")
    return number


def _array_storage(array):
    if array.dtype == np.uint8:
        return "raw"
    if array.dtype == np.bool_:
        return "logical"
    if np.issubdtype(array.dtype, np.integer):
        return "integer"
    if np.issubdtype(array.dtype, np.floating):
        return "double"
    if array.dtype.kind in "SU":
        return "character"
    if np.issubdtype(array.dtype, np.complexfloating):
        return "complex"
    return "reject"


def _require_matrix(array):
    if array.ndim == 2:
        return
    if array.ndim < 2:
        raise ValueError("non-numeric matrix extent")
    raise ValueError("Argument 'x' is not a matrix or a vector")


def _as_i32(array):
    if array.dtype == np.int32:
        return array
    if array.size and (
        int(np.min(array)) < _NA or int(np.max(array)) > _INT_MAX
    ):
        raise ValueError("Argument 'x' is not integer, logical, or raw: double")
    return array.astype(np.int32, copy=False)


def _scalar_kind(value):
    if value is None:
        return "missing"
    if isinstance(value, (bool, np.bool_)):
        return "logical"
    if isinstance(value, (int, np.integer)):
        return "integer"
    if isinstance(value, (float, np.floating)):
        return "double"
    if isinstance(value, str):
        return "character"
    if isinstance(value, (bytes, bytearray)) and len(value) == 1:
        return "raw"
    return "other"


def _subset(data, row_idx, col_idx, fill):
    if row_idx is None and col_idx is None:
        return data
    row_na = row_idx is not None and any(item is None for item in row_idx)
    col_na = col_idx is not None and any(item is None for item in col_idx)
    if not row_na and not col_na:
        if row_idx is None:
            return data[:, np.asarray(col_idx, dtype=np.intp)]
        if col_idx is None:
            return data[np.asarray(row_idx, dtype=np.intp), :]
        return data[
            np.ix_(
                np.asarray(row_idx, dtype=np.intp),
                np.asarray(col_idx, dtype=np.intp),
            )
        ]
    rows = row_idx if row_idx is not None else list(range(data.shape[0]))
    cols = col_idx if col_idx is not None else list(range(data.shape[1]))
    out = np.full((len(rows), len(cols)), fill, dtype=data.dtype)
    row_pos = np.array([-1 if item is None else item for item in rows], dtype=np.intp)
    col_pos = np.array([-1 if item is None else item for item in cols], dtype=np.intp)
    row_ok = np.flatnonzero(row_pos >= 0)
    col_ok = np.flatnonzero(col_pos >= 0)
    if row_ok.size and col_ok.size:
        out[np.ix_(row_ok, col_ok)] = data[np.ix_(row_pos[row_ok], col_pos[col_ok])]
    return out


def _observed(data, storage):
    if data.size == 0:
        return []
    if storage == "raw":
        return [int(value) for value in np.unique(data)]
    if storage == "logical":
        targets = []
        if np.any(data == 0):
            targets.append(0)
        if np.any(data == 1):
            targets.append(1)
        if np.any(data == _NA):
            targets.append(None)
        return targets
    unique = np.unique(data)
    has_na = unique.size > 0 and int(unique[0]) == _NA
    if has_na:
        unique = unique[1:]
    targets = [int(value) for value in unique]
    if has_na:
        targets.append(None)
    return targets


def _counts(data, targets):
    nrow, ncol = data.shape
    width = len(targets)
    out = np.zeros((nrow, width), dtype=np.int32)
    if nrow == 0 or width == 0 or ncol == 0:
        return out
    na_columns = [index for index, target in enumerate(targets) if target is None]
    if na_columns:
        na_count = np.count_nonzero(data == _NA, axis=1).astype(np.int32, copy=False)
        for index in na_columns:
            out[:, index] = na_count
    groups: dict[int, list[int]] = {}
    for index, target in enumerate(targets):
        if target is None:
            continue
        groups.setdefault(int(target), []).append(index)
    if not groups:
        return out
    ordered = np.asarray(sorted(groups), dtype=np.int64)
    if _dense_span(ordered, nrow):
        table = _dense_bins(data, int(ordered[0]), int(ordered[-1]))
        origin = int(ordered[0])
        for value, columns in groups.items():
            found = table[:, value - origin]
            for column in columns:
                out[:, column] = found
        return out
    table = _search_bins(data, ordered)
    for bin_index, value in enumerate(ordered.tolist()):
        found = table[:, bin_index]
        for column in groups[int(value)]:
            out[:, column] = found
    return out


def _dense_span(ordered, nrow):
    span = int(ordered[-1] - ordered[0]) + 1
    return span <= 65536 and nrow * span <= 50_000_000


def _dense_bins(data, vmin, vmax):
    span = vmax - vmin + 1
    shifted = data.astype(np.int64, copy=False) - vmin
    valid = (data != _NA) & (shifted >= 0) & (shifted < span)
    placed = np.where(valid, shifted, span)
    flat = (
        np.arange(data.shape[0], dtype=np.int64)[:, None] * (span + 1) + placed
    ).ravel()
    counts = np.bincount(flat, minlength=data.shape[0] * (span + 1))
    return counts.reshape(data.shape[0], span + 1)[:, :span]


def _search_bins(data, ordered):
    width = int(ordered.size)
    work = data.astype(np.int64, copy=False)
    pos = np.searchsorted(ordered, work)
    clipped = np.clip(pos, 0, width - 1)
    matched = (pos < width) & (ordered[clipped] == work) & (data != _NA)
    codes = np.where(matched, clipped, -1)
    flat = (
        np.arange(data.shape[0], dtype=np.int64)[:, None] * (width + 1) + (codes + 1)
    ).ravel()
    counts = np.bincount(flat, minlength=data.shape[0] * (width + 1))
    return counts.reshape(data.shape[0], width + 1)[:, 1:]


def _resolve_index(index, length):
    if isinstance(index, (bool, np.bool_)):
        return _logical_positions([bool(index)], length)
    if isinstance(index, str):
        raise ValueError("invalid subscript type 'character'")
    if isinstance(index, (int, np.integer)) and not isinstance(index, bool):
        number, _warned = _index_int(int(index), True)
        return _positions_from_numbers([number], length)
    if isinstance(index, (float, np.floating)):
        number, _warned = _index_float(float(index), True)
        return _positions_from_numbers([number], length)
    if isinstance(index, (list, tuple)):
        return _positions_from_sequence(list(index), length)
    array = np.asarray(index)
    if array.ndim == 0:
        return _resolve_index(array.item(), length)
    flat = np.ravel(array, order="F")
    if flat.dtype == np.bool_:
        return _logical_positions([bool(value) for value in flat.tolist()], length)
    if flat.dtype == object:
        return _positions_from_sequence(flat.tolist(), length)
    if flat.dtype.kind in "SU":
        raise ValueError("invalid subscript type 'character'")
    if np.issubdtype(flat.dtype, np.floating):
        return _positions_from_numbers(_index_floats(flat), length)
    if np.issubdtype(flat.dtype, np.integer):
        return _positions_from_numbers(_index_ints(flat), length)
    raise ValueError("invalid subscript type 'list'")


def _positions_from_sequence(values, length):
    if not values:
        return []
    if all(_is_logical_mark(value) for value in values):
        flags = [None if value is None else bool(value) for value in values]
        return _logical_positions(flags, length)
    warned = [False]
    numbers = [_sequence_number(value, warned) for value in values]
    return _positions_from_numbers(numbers, length)


def _is_logical_mark(value):
    return value is None or isinstance(value, (bool, np.bool_))


def _logical_positions(flags, length):
    if len(flags) > length:
        raise ValueError("(subscript) logical subscript too long")
    if not flags or length == 0:
        return []
    width = len(flags)
    chosen = []
    for position in range(length):
        bit = flags[position % width]
        if bit is None:
            chosen.append(None)
        elif bit:
            chosen.append(position)
    return chosen


def _positions_from_numbers(numbers, length):
    has_negative = any(value is not None and value < 0 for value in numbers)
    has_positive = any(value is not None and value > 0 for value in numbers)
    has_missing = any(value is None for value in numbers)
    if has_negative and (has_positive or has_missing):
        raise ValueError("only 0's may be mixed with negative subscripts")
    if has_negative:
        excluded = set()
        for value in numbers:
            if value is None or value == 0:
                continue
            position = -value
            if 1 <= position <= length:
                excluded.add(position - 1)
        return [position for position in range(length) if position not in excluded]
    chosen = []
    for value in numbers:
        if value is None:
            chosen.append(None)
            continue
        if value == 0:
            continue
        if value < 1 or value > length:
            raise ValueError("subscript out of bounds")
        chosen.append(value - 1)
    return chosen


def _index_ints(flat):
    warned = False
    numbers = []
    for value in flat.tolist():
        number, did_warn = _index_int(int(value), not warned)
        if did_warn:
            warned = True
        numbers.append(number)
    return numbers


def _index_floats(flat):
    warned = False
    numbers = []
    for value in flat.tolist():
        number, did_warn = _index_float(float(value), not warned)
        if did_warn:
            warned = True
        numbers.append(number)
    return numbers


def _index_int(value, warn):
    if value == _NA:
        return None, False
    if value < _INT_MIN or value > _INT_MAX:
        if warn:
            _warn(_RANGE)
        return None, True
    return value, False


def _index_float(value, warn):
    if math.isnan(value):
        return None, False
    if not math.isfinite(value):
        if warn:
            _warn(_RANGE)
        return None, True
    truncated = math.trunc(value)
    if truncated < _INT_MIN or truncated > _INT_MAX:
        if warn:
            _warn(_RANGE)
        return None, True
    return truncated, False


def _sequence_number(value, warned):
    if isinstance(value, str):
        raise ValueError("invalid subscript type 'character'")
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return 1 if value else 0
    if isinstance(value, (int, np.integer)):
        number, did_warn = _index_int(int(value), not warned[0])
        if did_warn:
            warned[0] = True
        return number
    if isinstance(value, (float, np.floating)):
        number, did_warn = _index_float(float(value), not warned[0])
        if did_warn:
            warned[0] = True
        return number
    raise ValueError("invalid subscript type 'list'")


def _iter_scalars(values):
    if isinstance(values, (bool, np.bool_)):
        yield ("logical", bool(values))
        return
    if isinstance(values, (int, np.integer)) and not isinstance(values, bool):
        yield ("integer", int(values))
        return
    if isinstance(values, (float, np.floating)):
        number = float(values)
        if math.isnan(number):
            yield ("missing", None)
        else:
            yield ("double", number)
        return
    if isinstance(values, str):
        yield ("character", values)
        return
    if isinstance(values, (bytes, bytearray)):
        for byte in values:
            yield ("raw", int(byte))
        return
    array = np.asarray(values)
    if array.ndim == 0:
        yield from _iter_scalars(array.item())
        return
    flat = np.ravel(array, order="F")
    if flat.dtype == object:
        for value in flat.tolist():
            yield _classify_scalar(value)
        return
    if flat.dtype == np.uint8:
        for value in flat.tolist():
            yield ("raw", int(value))
        return
    if flat.dtype == np.bool_:
        for value in flat.tolist():
            yield ("logical", bool(value))
        return
    if flat.dtype.kind in "SU":
        for value in flat.tolist():
            yield ("character", str(value))
        return
    if np.issubdtype(flat.dtype, np.floating):
        for value in flat.tolist():
            if math.isnan(float(value)):
                yield ("missing", None)
            else:
                yield ("double", float(value))
        return
    if np.issubdtype(flat.dtype, np.integer):
        for value in flat.tolist():
            yield ("integer", int(value))
        return
    raise ValueError("Argument 'values' must be a vector")


def _classify_scalar(value):
    if value is None:
        return ("missing", None)
    if isinstance(value, (bool, np.bool_)):
        return ("logical", bool(value))
    if isinstance(value, (int, np.integer)):
        return ("integer", int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return ("missing", None)
        return ("double", number)
    if isinstance(value, str):
        return ("character", value)
    if isinstance(value, (bytes, bytearray)) and len(value) == 1:
        return ("raw", int(value[0]))
    raise ValueError("Argument 'values' must be a vector")


def _coerce(kind, value, storage):
    if storage == "raw":
        return _coerce_raw(kind, value)
    if storage == "logical":
        return _coerce_logical(kind, value)
    return _coerce_integer(kind, value)


def _coerce_integer(kind, value):
    if kind == "missing":
        return None
    if kind == "logical":
        return 1 if value else 0
    if kind == "raw":
        return int(value)
    if kind == "integer":
        number = int(value)
        if number == _NA:
            return None
        if number < _INT_MIN or number > _INT_MAX:
            _warn(_RANGE)
            return None
        return number
    if kind == "double":
        return _double_to_i32(value)
    if kind == "character":
        parsed = _character_to_i32(value)
        return parsed
    raise ValueError("Argument 'values' must be a vector")


def _coerce_logical(kind, value):
    if kind == "missing":
        return None
    if kind == "logical":
        return 1 if value else 0
    if kind == "raw":
        return 0 if int(value) == 0 else 1
    if kind == "integer":
        number = int(value)
        if number == _NA:
            return None
        return 0 if number == 0 else 1
    if kind == "double":
        number = float(value)
        if math.isnan(number):
            return None
        return 0 if number == 0.0 else 1
    if kind == "character":
        return _character_to_logical(value)
    raise ValueError("Argument 'values' must be a vector")


def _coerce_raw(kind, value):
    if kind == "missing":
        _warn(_RAW)
        return 0
    if kind == "logical":
        return 1 if value else 0
    if kind == "raw":
        return int(value)
    if kind == "integer":
        number = int(value)
        if number == _NA or number < 0 or number > 255:
            _warn(_RAW)
            return 0
        return number
    if kind == "double":
        number = float(value)
        if not math.isfinite(number):
            _warn(_RAW)
            return 0
        truncated = math.trunc(number)
        if truncated < 0 or truncated > 255:
            _warn(_RAW)
            return 0
        return truncated
    if kind == "character":
        parsed = _character_to_i32(value)
        if parsed is None or parsed < 0 or parsed > 255:
            _warn(_RAW)
            return 0
        return parsed
    raise ValueError("Argument 'values' must be a vector")


def _double_to_i32(value):
    number = float(value)
    if math.isnan(number):
        return None
    if not math.isfinite(number):
        _warn(_RANGE)
        return None
    truncated = math.trunc(number)
    if truncated < _INT_MIN or truncated > _INT_MAX:
        _warn(_RANGE)
        return None
    return truncated


def _character_to_i32(text):
    if text in ("NA", "NaN", "NA_integer_", "NA_real_", "NA_character_"):
        return None
    try:
        number = float(text)
    except ValueError:
        _warn(_COERCE)
        return None
    return _double_to_i32(number)


def _character_to_logical(text):
    token = text.lower()
    if token in ("true", "t"):
        return 1
    if token in ("false", "f"):
        return 0
    if token in ("na", "nan"):
        return None
    _warn(_COERCE)
    return None


def _warn(message):
    warnings.warn(message, RuntimeWarning, stacklevel=3)
