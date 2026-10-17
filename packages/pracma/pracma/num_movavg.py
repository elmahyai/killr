"""Moving-average filters."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, match_arg


def movavg(x, n, type="s"):
    if not is_r_numeric(x):
        raise PracmaError("is.numeric(x) is not TRUE")
    if not is_r_numeric(n):
        raise PracmaError("is.numeric(n) is not TRUE")
    if not isinstance(type, str):
        raise PracmaError("is.character(type) is not TRUE")
    window = float(np.asarray(n).reshape(-1)[0])
    if np.asarray(n).size != 1 or math.ceil(window != math.floor(window)) or window <= 1:
        raise PracmaError("Window length 'n' must be a single integer greater 1.")
    series = np.asarray(x, dtype=float).reshape(-1)
    width = int(window)
    if width >= series.size:
        raise PracmaError("Window length 'n' must be greater then length of time series.")
    y = np.zeros(series.size)
    kind = match_arg(type, ("s", "t", "w", "m", "e", "r"))
    if kind == "s":
        for k in range(1, width):
            y[k - 1] = np.mean(series[:k])
        for k in range(width, series.size + 1):
            y[k - 1] = np.mean(series[k - width:k])
    elif kind == "t":
        narrowed = math.ceil((width + 1) / 2)
        return movavg(movavg(series, narrowed, "s"), narrowed, "s")
    elif kind == "w":
        for k in range(1, width):
            weights = np.arange(k, 0, -1)
            y[k - 1] = 2 * np.sum(weights * series[np.arange(k, 0, -1) - 1]) / (k * (k + 1))
        for k in range(width, series.size + 1):
            weights = np.arange(width, 0, -1)
            y[k - 1] = 2 * np.sum(weights * series[np.arange(k, k - width, -1) - 1]) / (width * (width + 1))
    elif kind == "m":
        y[0] = series[0]
        for k in range(1, series.size):
            y[k] = y[k - 1] + (series[k] - y[k - 1]) / width
    elif kind == "e":
        alpha = 2 / (width + 1)
        y[0] = series[0]
        for k in range(1, series.size):
            y[k] = alpha * series[k] + (1 - alpha) * y[k - 1]
    elif kind == "r":
        alpha = 1 / width
        y[0] = series[0]
        for k in range(1, series.size):
            y[k] = alpha * series[k] + (1 - alpha) * y[k - 1]
    else:
        raise PracmaError("The type must be one of 's', 't', 'w', 'm', 'e', or 'r'.")
    return y
