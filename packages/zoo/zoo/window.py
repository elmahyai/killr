"""Lag, difference, and window a zoo series.

lag.zoo is the R method in window.zoo.R. It does not call the C routine zoo_lag.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np

from zoo.merge import merge_zoo
from zoo.series import Zoo


def lag_zoo(x: Zoo, k: Any = 1, na_pad: bool = False, **_unused: Any) -> Zoo:
    """Shift observations by k positions. A positive k moves values earlier."""
    del _unused
    if isinstance(k, dict):
        names = [str(name) for name in k.keys()]
        values = [float(value) for value in k.values()]
        parts = [lag_zoo(x, k=value, na_pad=na_pad) for value in values]
        return merge_zoo(*parts, suffixes=names)
    k_arr = np.asarray(k, dtype=float).reshape(-1)
    if k_arr.size > 1:
        names = [_lag_label(value) for value in k_arr]
        parts = [lag_zoo(x, k=float(value), na_pad=na_pad) for value in k_arr]
        return merge_zoo(*parts, suffixes=names)
    shift = float(k_arr[0])
    rounded = float(round(shift))
    if shift != rounded:
        warnings.warn("k is not an integer", stacklevel=2)
        shift = rounded
    shift = int(shift)
    nrow = _nrow(x)
    if shift == 0:
        return x
    # A lag past either end is replaced by +nrow, including a large negative lag.
    if abs(shift) > nrow:
        shift = nrow
    original = np.asarray(x.index)
    if shift > 0:
        xx = _rows(x, np.arange(shift, nrow))
        xx.index = original[: nrow - shift] if shift else original
    else:
        keep = -shift
        xx = _rows(x, np.arange(0, nrow - keep))
        xx.index = original[keep:]
    if not na_pad:
        return xx
    empty = Zoo(np.array([], dtype=float), np.asarray(original), frequency=x.frequency)
    return merge_zoo(empty, xx, all=[True, False])


def window_zoo(
    x: Zoo,
    index_: Any = None,
    start: Any = None,
    end: Any = None,
    **_unused: Any,
) -> Zoo:
    """Keep the observations whose index lies in the requested window."""
    del _unused
    all_indexes = np.asarray(x.index)
    if index_ is None:
        index_ = all_indexes
    else:
        index_ = np.asarray(index_)
    frequency = x.frequency
    start = _period_bound(start, frequency, all_indexes)
    end = _period_bound(end, frequency, all_indexes)
    chosen = _match(all_indexes, index_) > 0
    if _missing(start):
        if _missing(end):
            mask = chosen
        else:
            mask = chosen & _compare(all_indexes, end, "le")
    elif _missing(end):
        mask = chosen & _compare(all_indexes, start, "ge")
    else:
        mask = chosen & _compare(all_indexes, start, "ge") & _compare(all_indexes, end, "le")
    return _rows(x, np.flatnonzero(mask))


def diff_zoo(
    x: Zoo,
    lag: Any = 1,
    differences: Any = 1,
    arithmetic: bool = True,
    na_pad: bool = False,
    log: bool = False,
    **_unused: Any,
) -> Zoo:
    """Differences of consecutive observations, optionally padded back to the original index."""
    del _unused
    if not (differences >= 1):
        raise ValueError("differences >= 1 is not TRUE")
    original = np.asarray(x.index)
    steps = int(math.floor(float(differences)))
    current = x
    if arithmetic or _all_positive(current):
        if (not arithmetic) or log:
            current = _apply(current, np.log)
        for _ in range(steps):
            shifted = lag_zoo(current, k=-float(lag))
            if float(lag) > 0:
                current = _binary(current, shifted, np.subtract)
            else:
                current = _binary(shifted, current, np.subtract)
        if not arithmetic:
            current = _apply(current, np.exp)
    else:
        for _ in range(steps):
            shifted = lag_zoo(current, k=-float(lag))
            if float(lag) > 0:
                current = _binary(current, shifted, np.divide)
            else:
                current = _binary(shifted, current, np.divide)
    if not na_pad:
        return current
    empty = Zoo(np.array([], dtype=float), original, frequency=x.frequency)
    return merge_zoo(empty, current, all=[True, False])


def _all_positive(x: Zoo) -> bool:
    data = np.asarray(x.data, dtype=float)
    compared = data > 0
    if np.any(np.isnan(data)):
        raise ValueError("missing value where TRUE/FALSE needed")
    return bool(np.all(compared))


def _lag_label(value: float) -> str:
    if float(value) == int(value):
        return f"lag{int(value)}"
    return f"lag{value}"


def _period_bound(bound: Any, frequency: float | None, indexes: np.ndarray) -> Any:
    if bound is None:
        return None
    values = np.atleast_1d(np.asarray(bound, dtype=float))
    numeric = np.issubdtype(np.asarray(indexes).dtype, np.number) or indexes.dtype.kind == "f"
    if values.size == 2 and frequency is not None and numeric:
        return float(math.floor(values[0] * frequency + (values[1] - 1) + 0.0001) / frequency)
    if values.size == 1:
        return float(values[0])
    return values


def _missing(bound: Any) -> bool:
    if bound is None:
        return True
    values = np.atleast_1d(np.asarray(bound, dtype=float))
    if values.size == 0:
        return True
    return bool(np.any(np.isnan(values)))


def _compare(indexes: np.ndarray, bound: Any, how: str) -> np.ndarray:
    left = np.asarray(indexes, dtype=float)
    right = np.asarray(bound, dtype=float)
    if how == "le":
        return left <= right
    return left >= right


def _rows(x: Zoo, keep: np.ndarray) -> Zoo:
    data = np.asarray(x.data)
    index = np.asarray(x.index)[keep]
    if data.ndim <= 1:
        values = np.asarray(data, dtype=float)[keep]
        obj = Zoo(values, index, frequency=x.frequency, regular=getattr(x, "regular", False))
        return obj
    values = np.asfortranarray(np.asarray(data, dtype=float)[keep, :])
    obj = Zoo(values, index, frequency=x.frequency, regular=getattr(x, "regular", False))
    columns = getattr(x, "columns", None)
    if columns is not None:
        obj.columns = list(columns)
    return obj


def _nrow(x: Zoo) -> int:
    data = np.asarray(x.data)
    if data.ndim == 0:
        return 1
    return int(data.shape[0])


def _apply(x: Zoo, func: Any) -> Zoo:
    data = np.asarray(x.data, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        values = func(data)
    if values.ndim == 2:
        values = np.asfortranarray(values)
    obj = Zoo(values, np.asarray(x.index), frequency=x.frequency, regular=getattr(x, "regular", False))
    columns = getattr(x, "columns", None)
    if columns is not None and values.ndim == 2:
        obj.columns = list(columns)
    return obj


def _binary(left: Zoo, right: Zoo, op: Any) -> Zoo:
    left_index = np.asarray(left.index, dtype=float)
    right_index = np.asarray(right.index, dtype=float)
    common = np.intersect1d(left_index, right_index)
    left_at = _match(common, left_index) - 1
    right_at = _match(common, right_index) - 1
    left_data = np.asarray(left.data, dtype=float)
    right_data = np.asarray(right.data, dtype=float)
    with np.errstate(invalid="ignore", divide="ignore"):
        if left_data.ndim <= 1 and right_data.ndim <= 1:
            values = op(left_data[left_at], right_data[right_at])
        else:
            if left_data.ndim == 1:
                left_data = left_data.reshape(-1, 1)
            if right_data.ndim == 1:
                right_data = right_data.reshape(-1, 1)
            values = np.asfortranarray(op(left_data[left_at, :], right_data[right_at, :]))
    obj = Zoo(values, common, frequency=left.frequency, regular=getattr(left, "regular", False))
    columns = getattr(left, "columns", None)
    if columns is not None and np.asarray(values).ndim == 2:
        obj.columns = list(columns)
    return obj


def _match(needles: np.ndarray, haystack: np.ndarray) -> np.ndarray:
    table: dict[float, int] = {}
    for position, value in enumerate(np.asarray(haystack, dtype=float).reshape(-1), start=1):
        table.setdefault(float(value), position)
    return np.asarray(
        [table.get(float(value), 0) for value in np.asarray(needles, dtype=float).reshape(-1)],
        dtype=int,
    )
