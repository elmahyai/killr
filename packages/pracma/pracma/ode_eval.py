"""Evaluate an ODE solution and detect when a component crosses a level."""

from __future__ import annotations

import warnings

import numpy as np

from pracma._util import PracmaError


def _numeric_vector(value, label):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.vector({label}, mode = \"numeric\") is not TRUE")
    array = np.asarray(value)
    if array.ndim != 1 or array.dtype == bool or not np.issubdtype(array.dtype, np.number):
        raise PracmaError(f"is.vector({label}, mode = \"numeric\") is not TRUE")
    return np.array(array, dtype=float, copy=True)


def _solution_matrix(y):
    if isinstance(y, (bool, np.bool_)):
        raise PracmaError("is.numeric(y) is not TRUE")
    array = np.asarray(y)
    if array.dtype == bool or not np.issubdtype(array.dtype, np.number):
        raise PracmaError("is.numeric(y) is not TRUE")
    array = np.array(array, dtype=float, copy=True)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim != 2:
        raise PracmaError("is.numeric(y) is not TRUE")
    return array


def _unsorted(x):
    if x.size <= 1:
        return False
    return bool(np.any(x[1:] < x[:-1]))


def _find_interval(values, breaks):
    """1-based R findInterval: breaks[i] <= value < breaks[i + 1]."""
    breaks = np.asarray(breaks, dtype=float).reshape(-1)
    values = np.asarray(values, dtype=float).reshape(-1)
    n = breaks.size
    out = np.empty(values.size, dtype=int)
    for i, value in enumerate(values):
        if n == 0 or value < breaks[0]:
            out[i] = 0
            continue
        if value >= breaks[-1]:
            out[i] = n
            continue
        lo = 0
        hi = n - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if breaks[mid] <= value:
                lo = mid
            else:
                hi = mid - 1
        out[i] = lo + 1
    return out


def _findintervals(x, xs):
    """Indices where xs crosses or hits the scalar x. 1-based, like pracma."""
    xs = np.asarray(xs, dtype=float).reshape(-1)
    if xs.size == 0:
        return np.array([], dtype=int)
    shifted = xs - float(x)
    exact = np.flatnonzero(shifted == 0) + 1
    if xs.size == 1:
        return exact.astype(int)
    crossed = np.flatnonzero(shifted[:-1] * shifted[1:] < 0) + 1
    if exact.size == 0 and crossed.size == 0:
        return np.array([], dtype=int)
    return np.sort(np.concatenate([exact, crossed])).astype(int)


def deval(x, y, xp, idx=None):
    x = _numeric_vector(x, "x")
    y = _solution_matrix(y)
    xp = _numeric_vector(xp, "xp")
    if x.size != y.shape[0]:
        raise PracmaError("Length of 'x' must be equal to the number of rows in 'y'.")
    if _unsorted(x):
        raise PracmaError("Argument vector 'x' must be sorted.")
    if idx is None:
        columns = np.arange(1, y.shape[1] + 1, dtype=float)
    else:
        columns = np.asarray(idx, dtype=float).reshape(-1)
        if np.any((columns < 1) | (columns > y.shape[1]) | (columns != np.trunc(columns))):
            raise PracmaError("Indices 'idx' must be between 1 and no. of columns of 'y'.")
    chosen = columns.astype(int) - 1
    places = _find_interval(xp, x)
    yp = np.full((xp.size, chosen.size), np.nan)
    last = x.size
    for i, fi in enumerate(places):
        if fi == 0:
            continue
        if fi < last:
            left = fi - 1
            right = fi
            weight = (xp[i] - x[left]) / (x[right] - x[left])
            yp[i, :] = y[left, chosen] + weight * (y[right, chosen] - y[left, chosen])
        elif xp[i] > x[-1]:
            continue
        else:
            yp[i, :] = y[fi - 1, chosen]
    if xp.size == 1:
        return yp.reshape(-1)
    return yp


def deeve(x, y, yv=0, idx=None):
    x = _numeric_vector(x, "x")
    y = _solution_matrix(y)
    yv = float(np.asarray(yv, dtype=float).reshape(-1)[0])
    if _unsorted(x):
        raise PracmaError("Argument vector 'x' must be sorted.")
    if x.size != y.shape[0]:
        raise PracmaError("Length of 'x' must be equal to the number of rows in 'y'.")
    if idx is None:
        column = y.shape[1]
    else:
        chosen = np.asarray(idx, dtype=float).reshape(-1)
        if chosen.size > 1:
            warnings.warn("Several indices found; only accepting the first one.")
        column = int(chosen[0])
    series = y[:, column - 1]
    if yv < float(np.min(series)) or yv > float(np.max(series)):
        return np.array([np.nan])
    places = _findintervals(yv, series)
    if places.size == 0:
        return None
    found = np.empty(places.size, dtype=float)
    last = series.size
    for i, fi in enumerate(places):
        if fi < last:
            left = fi - 1
            found[i] = (
                (yv - series[left]) / (series[left + 1] - series[left]) * (x[left + 1] - x[left])
                + x[left]
            )
        else:
            found[i] = x[fi - 1]
    return found
