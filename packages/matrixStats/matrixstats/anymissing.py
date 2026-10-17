"""anyMissing, ported from matrixStats 1.5.0."""

from __future__ import annotations

import numpy as np

import anymissing as _anymissing

# R's NA_INTEGER. Integer arrays use this sentinel for a missing value.
NA_INTEGER = -2147483648

# 0-based stand-in for an NA subscript, produced by the Rust index validator.
_NA_POSITION = np.iinfo(np.int64).min


def anyMissing(x, idxs=None):
    """Return True if any selected value is missing.

    Mirrors ``matrixStats::anyMissing``. ``idxs`` is 1-based, as in R.
    ``None`` selects every element. A double missing value is NaN. An integer
    missing value is ``None`` or the R integer NA sentinel. A list or dict is
    missing when any element is missing; a dict is treated as a data frame of
    columns. The scan stops at the first missing value.
    """
    if isinstance(x, dict):
        for column in x.values():
            if _column_any_missing(column, idxs):
                return True
        return False
    if _is_record_list(x):
        for element in x:
            if isinstance(element, (list, tuple, dict)):
                continue
            if _atomic_any_missing(element, idxs):
                return True
        return False
    return _atomic_any_missing(x, idxs)


def _is_record_list(x):
    return isinstance(x, (list, tuple)) and any(
        isinstance(element, (list, tuple, dict, np.ndarray)) for element in x
    )


def _column_any_missing(column, idxs):
    """One data-frame column. A nested list or dict is not inspected."""
    if isinstance(column, dict):
        return False
    if isinstance(column, (list, tuple)):
        if _is_record_list(column):
            return False
        return _atomic_any_missing(column, idxs)
    return _atomic_any_missing(column, idxs)


def _atomic_any_missing(x, idxs):
    if x is None:
        values = np.array([np.nan])
    elif isinstance(x, (list, tuple)):
        values = _sequence_to_array(x)
    elif isinstance(x, str):
        values = np.array([x], dtype=object)
    else:
        values = np.asarray(x)
    if values.ndim != 1:
        values = np.ravel(values, order="F")
    if values.size == 0:
        return False
    if values.dtype != object and not values.flags.c_contiguous:
        values = np.ascontiguousarray(values)
    positions = _resolve_positions(idxs, int(values.size))
    if positions is not None and positions.size == 0:
        return False
    return _scan(values, positions)


def _sequence_to_array(seq):
    if len(seq) == 0:
        return np.array([], dtype=np.float64)
    if any(value is None or _is_float(value) or _is_complex(value) for value in seq):
        if any(_is_complex(value) for value in seq):
            converted = [
                np.nan if value is None else complex(value) for value in seq
            ]
            return np.asarray(converted, dtype=np.complex128)
        converted = []
        for value in seq:
            if value is None:
                converted.append(np.nan)
            elif isinstance(value, (bool, np.bool_)):
                converted.append(float(value))
            else:
                converted.append(float(value))
        return np.asarray(converted, dtype=np.float64)
    if all(isinstance(value, (bool, np.bool_)) for value in seq):
        return np.asarray(seq, dtype=bool)
    if all(_is_int(value) or isinstance(value, (bool, np.bool_)) for value in seq):
        return np.asarray([int(value) for value in seq], dtype=np.int64)
    return np.asarray(seq, dtype=object)


def _is_int(value):
    return isinstance(value, (int, np.integer)) and not isinstance(value, (bool, np.bool_))


def _is_float(value):
    return isinstance(value, (float, np.floating)) and not isinstance(value, (bool, np.bool_))


def _is_complex(value):
    return isinstance(value, (complex, np.complexfloating))


def _prepare_idxs(idxs):
    if idxs is None:
        return "all", None
    if isinstance(idxs, (bool, np.bool_)):
        return "logical", np.array([1 if idxs else 0], dtype=np.int8)
    if _is_int(idxs):
        return "integer", np.array([int(idxs)], dtype=np.int64)
    if _is_float(idxs):
        return "real", np.array([float(idxs)], dtype=np.float64)
    if isinstance(idxs, (list, tuple)):
        return _prepare_idx_sequence(idxs)
    if isinstance(idxs, np.ndarray):
        return _prepare_idx_array(idxs)
    array = np.asarray(idxs)
    return _prepare_idx_array(array)


def _prepare_idx_sequence(seq):
    if len(seq) == 0:
        return "integer", np.array([], dtype=np.int64)
    if all(value is None or isinstance(value, (bool, np.bool_)) for value in seq):
        flags = np.empty(len(seq), dtype=np.int8)
        for i, value in enumerate(seq):
            if value is None:
                flags[i] = -1
            else:
                flags[i] = 1 if value else 0
        return "logical", flags
    if all(value is None or _is_int(value) for value in seq):
        out = np.empty(len(seq), dtype=np.int64)
        for i, value in enumerate(seq):
            out[i] = NA_INTEGER if value is None else int(value)
        return "integer", out
    if all(value is None or _is_int(value) or _is_float(value) for value in seq):
        out = np.empty(len(seq), dtype=np.float64)
        for i, value in enumerate(seq):
            out[i] = np.nan if value is None else float(value)
        return "real", out
    raise ValueError("idxs can only be integer, numeric, or logical")


def _prepare_idx_array(arr):
    flat = np.ravel(arr)
    if flat.size == 0:
        return "integer", np.array([], dtype=np.int64)
    if flat.dtype == bool:
        return "logical", np.ascontiguousarray(flat, dtype=np.int8)
    if flat.dtype.kind == "f":
        return "real", np.ascontiguousarray(flat, dtype=np.float64)
    if flat.dtype.kind == "i":
        return "integer", np.ascontiguousarray(flat, dtype=np.int64)
    if flat.dtype.kind == "u":
        return "real", np.ascontiguousarray(flat, dtype=np.float64)
    if flat.dtype == object:
        return _prepare_idx_sequence(flat.tolist())
    raise ValueError("idxs can only be integer, numeric, or logical")


def _resolve_positions(idxs, n):
    kind, values = _prepare_idxs(idxs)
    if kind == "all":
        return None
    if kind == "integer":
        positions = _anymissing.positions_integer(values, n, True)
    elif kind == "real":
        positions = _anymissing.positions_real(values, n, True)
    elif kind == "logical":
        positions = _anymissing.positions_logical(values, n, True)
        if positions is None:
            return None
    else:
        raise ValueError("idxs can only be integer, numeric, or logical")
    return np.asarray(positions, dtype=np.int64)


def _scan(values, positions):
    kind = values.dtype.kind
    if kind == "f":
        if values.dtype == np.float32:
            return bool(_anymissing.scan_f32(values, positions))
        if values.dtype != np.float64:
            values = np.ascontiguousarray(values, dtype=np.float64)
        return bool(_anymissing.scan_f64(values, positions))
    if kind == "i":
        if values.dtype == np.int32:
            return bool(_anymissing.scan_i32(values, positions))
        if values.dtype != np.int64:
            values = np.ascontiguousarray(values, dtype=np.int64)
        return bool(_anymissing.scan_i64(values, positions))
    if kind == "c":
        return _scan_complex(values, positions)
    if kind == "O":
        return _scan_object(values, positions)
    return _na_index_only(positions)


def _na_index_only(positions):
    if positions is None:
        return False
    return bool(np.any(positions == _NA_POSITION))


def _scan_complex(values, positions):
    flat = np.ascontiguousarray(values).ravel()
    if positions is None and flat.dtype == np.complex128:
        return bool(_anymissing.scan_f64(flat.view(np.float64)))
    indexes = range(flat.size) if positions is None else positions
    for index in indexes:
        if index == _NA_POSITION:
            return True
        number = flat[int(index)]
        if np.isnan(number.real) or np.isnan(number.imag):
            return True
    return False


def _scan_object(values, positions):
    flat = values.ravel()
    indexes = range(flat.size) if positions is None else positions
    for index in indexes:
        if index == _NA_POSITION or _object_missing(flat[int(index)]):
            return True
    return False


def _object_missing(item):
    if item is None:
        return True
    if isinstance(item, (bool, np.bool_)):
        return False
    if _is_int(item):
        return int(item) == NA_INTEGER
    if _is_float(item):
        return bool(np.isnan(item))
    if _is_complex(item):
        return bool(np.isnan(item.real) or np.isnan(item.imag))
    return False
