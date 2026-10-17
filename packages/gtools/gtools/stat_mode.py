"""Most frequently occurring value (gtools 3.9.5 ``stat_mode``)."""

from __future__ import annotations

import numpy as np

from gtools.na_replace import (
    NA,
    _NA_INT,
    _NA_LOGICAL,
    _as_array,
    _is_logical_int8,
    _missing_mask,
)

_TIES = ("all", "first", "last", "missing")


def _match_arg(value: str, choices: tuple[str, ...]) -> str:
    if value not in choices:
        raise ValueError(f"'{value}' is not one of {', '.join(repr(c) for c in choices)}")
    return value


def _values_equal(left, right, dtype: np.dtype) -> bool:
    kind = dtype.kind
    if kind in "fd":
        if np.isnan(left) and np.isnan(right):
            return True
        return bool(left == right)
    if kind == "c":
        return (np.isnan(left.real) and np.isnan(right.real)) or left == right
    if _is_logical_int8(dtype) or kind == "b":
        return int(left) == int(right)
    if kind == "i":
        return int(left) == int(right)
    if kind == "O":
        if left is NA and right is NA:
            return True
        return left == right
    return left == right


def _unique_preserve(values: np.ndarray, dtype: np.dtype) -> np.ndarray:
    if values.size == 0:
        return np.array([], dtype=dtype)
    kept: list = []
    for item in values:
        if not any(_values_equal(item, seen, dtype) for seen in kept):
            kept.append(item)
    if dtype.kind == "O":
        return np.array(kept, dtype=object)
    return np.asarray(kept, dtype=dtype)


def _r_match(source: np.ndarray, uv: np.ndarray, dtype: np.dtype) -> np.ndarray:
    out = np.full(source.shape, np.nan, dtype=np.float64)
    for index, value in enumerate(source):
        for position, candidate in enumerate(uv, start=1):
            if _values_equal(value, candidate, dtype):
                out[index] = float(position)
                break
    return out


def _r_tabulate(match_indices: np.ndarray) -> np.ndarray:
    if match_indices.size == 0:
        return np.array([0], dtype=np.int64)
    valid = match_indices[~np.isnan(match_indices)]
    if valid.size == 0:
        return np.array([0], dtype=np.int64)
    max_idx = int(np.max(valid))
    counts = np.zeros(max_idx, dtype=np.int64)
    for idx in valid:
        counts[int(idx) - 1] += 1
    return counts


def _na_scalar(dtype: np.dtype):
    kind = dtype.kind
    if kind in "fd":
        return np.nan
    if kind == "c":
        return complex(np.nan, np.nan)
    if _is_logical_int8(dtype) or kind == "b":
        return _NA_LOGICAL
    if kind == "i":
        return _NA_INT
    if kind == "O":
        return NA
    return np.nan


def _empty_uv_modes(uv: np.ndarray, tab: np.ndarray, dtype: np.dtype) -> np.ndarray:
    if uv.size == 0 and tab.size == 1 and tab[0] == 0:
        return np.array([_na_scalar(dtype)], dtype=dtype if dtype.kind != "O" else object)
    max_count = int(np.max(tab))
    mask = tab == max_count
    return uv[mask]


def _logical_item(item):
    code = int(item)
    if code == int(_NA_LOGICAL):
        return NA
    return code == 1


def _int_item(item):
    if np.int32(item) == _NA_INT:
        return NA
    return int(item)


def _materialize(modes: np.ndarray, dtype: np.dtype, original):
    flat = modes.ravel(order="F")
    if flat.size == 0:
        if isinstance(original, list):
            return []
        return np.array([], dtype=dtype)

    def convert(item):
        if _is_logical_int8(dtype) or dtype.kind == "b":
            return _logical_item(item)
        if dtype.kind == "i":
            return _int_item(item)
        if dtype.kind == "O":
            return item
        if dtype.kind == "c":
            return complex(item)
        if dtype.kind in "fd":
            return float(item)
        return item

    if flat.size == 1 and not isinstance(original, np.ndarray):
        return convert(flat[0])

    converted = [convert(item) for item in flat]
    if isinstance(original, list):
        return converted
    if _is_logical_int8(dtype) or dtype.kind == "b":
        return np.asarray([np.int8(_NA_LOGICAL if v is NA else (1 if v else 0)) for v in converted], dtype=np.int8)
    if dtype.kind == "i":
        return np.asarray(
            [_NA_INT if v is NA else np.int32(v) for v in converted],
            dtype=np.int32,
        )
    if dtype.kind == "O":
        return np.array(converted, dtype=object)
    return np.asarray(converted, dtype=dtype)


def stat_mode(x, na_rm: bool = True, ties: str = "all", **kwargs):
    """Return the most frequently occurring value(s) in ``x``."""
    del kwargs
    ties = _match_arg(ties, _TIES)
    array, _, dtype = _as_array(x)
    flat = array.ravel(order="F")
    miss = _missing_mask(array).ravel(order="F")

    if na_rm:
        uv = _unique_preserve(flat[~miss], dtype)
    else:
        uv = _unique_preserve(flat, dtype)

    matched = _r_match(flat, uv, dtype)
    tab = _r_tabulate(matched)
    all_modes = _empty_uv_modes(uv, tab, dtype)

    if all_modes.size > 1:
        if ties == "first":
            all_modes = all_modes[:1]
        elif ties == "last":
            all_modes = all_modes[-1:]
        elif ties == "all":
            pass
        else:
            all_modes = np.array([_na_scalar(dtype)], dtype=dtype if dtype.kind != "O" else object)

    return _materialize(all_modes, dtype, x)
