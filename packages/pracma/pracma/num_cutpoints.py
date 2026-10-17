"""Largest gaps in a sorted sample."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.num_helpers import is_r_numeric, is_r_vector, r_quantile


def cutpoints(x, nmax=8, quant=0.95):
    if not is_r_numeric(x):
        raise PracmaError("is.numeric(x) is not TRUE")
    if not is_r_numeric(nmax):
        raise PracmaError("is.numeric(nmax) is not TRUE")
    if not is_r_numeric(quant):
        raise PracmaError("is.numeric(quant) is not TRUE")
    if np.asarray(nmax).size != 1 or float(nmax) != math.floor(float(nmax)) or float(nmax) <= 0:
        raise PracmaError("Argument 'nmax' must be a positive integer.")
    level = float(np.asarray(quant).reshape(-1)[0])
    if np.asarray(quant).size != 1 or level < 0 or level > 1:
        raise PracmaError("Argument 'quant' must be a numeric value in [0,1].")
    values = np.asarray(x, dtype=float)
    if values.size == 1:
        return {"cutp": None, "cutd": None}
    values = values.reshape(-1, order="F")
    if np.any(np.diff(values) < 0):
        values = np.sort(values)
    gaps = np.diff(values)
    limit = int(nmax)
    if level == 0.0:
        count = limit
    else:
        threshold = r_quantile(gaps, level)
        count = min(limit, int(np.sum(gaps >= threshold)))
    order = np.argsort(gaps, kind="stable")
    chosen = order[::-1][:count]
    widths = gaps[chosen]
    places = values[chosen] + widths / 2.0
    order = np.argsort(places, kind="stable")
    return {"cutp": places[order], "cutd": widths[order]}
