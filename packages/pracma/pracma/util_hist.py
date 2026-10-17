"""Histogram counts from histc.R."""

from __future__ import annotations

import numpy as np

from pracma._util import PracmaError
from pracma.util_support import is_numeric, require, whole_number


def histc(x, edges):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    require(is_numeric(edges), "is.numeric(edges) is not TRUE")
    bounds = np.asarray(edges, dtype=float).reshape(-1)
    if np.any(np.diff(bounds) < 0):
        raise PracmaError("Argument 'edges' must be a monotonically non-decreasing vector.")
    values = np.asarray(x, dtype=float)
    count = bounds.size
    if count == 1:
        bins = np.zeros(values.size, dtype=float)
        if values.ndim == 2:
            bins = bins.reshape(count, values.shape[1])
        return {"cnt": 0.0, "bin": bins}
    if values.ndim > 2:
        raise PracmaError("Argument 'x' must be a numeric vector or matrix.")
    bins = np.zeros(values.shape, dtype=float)
    if values.ndim <= 1:
        values = values.reshape(-1)
        bins = np.zeros(values.size, dtype=float)
        counts = np.zeros(count, dtype=float)
        for index in range(count - 1):
            inside = (bounds[index] <= values) & (values < bounds[index + 1])
            counts[index] = float(np.sum(inside))
            bins[inside] = index + 1
        on_edge = values == bounds[count - 1]
        counts[count - 1] = float(np.sum(on_edge))
        bins[on_edge] = count
        return {"cnt": counts, "bin": bins}
    counts = np.zeros((count, values.shape[1]), dtype=float)
    for index in range(count - 1):
        inside = (bounds[index] <= values) & (values < bounds[index + 1])
        counts[index, :] = np.sum(inside, axis=0)
        bins[inside] = index + 1
    on_edge = values == bounds[count - 1]
    counts[count - 1, :] = np.sum(on_edge, axis=0)
    bins[on_edge] = count
    return {"cnt": counts, "bin": bins}


def _hist_counts(values, breaks):
    """Right-closed histogram bins. The lowest bin also contains the left edge."""
    slots = np.searchsorted(breaks, values, side="left") - 1
    slots = np.where(values == breaks[0], 0, slots)
    counts = np.zeros(breaks.size - 1, dtype=float)
    valid = (slots >= 0) & (slots < counts.size)
    np.add.at(counts, slots[valid], 1.0)
    return counts


def histss(x, n=100, plotting=False):
    require(is_numeric(x), "is.numeric(x) is not TRUE")
    require(is_numeric(n), "is.numeric(n) is not TRUE")
    values = np.asarray(x, dtype=float).reshape(-1)
    count = np.asarray(n, dtype=float).reshape(-1)
    if count.size != 1 or count[0] < 2 or not whole_number(count[0]):
        raise PracmaError("Argument 'n' must be an integer greater than 1.")
    bins = int(count[0])
    span = float(np.max(values) - np.min(values))
    low = float(np.min(values))
    high = float(np.max(values))
    cost = np.zeros(bins - 1)
    for index in range(1, bins):
        width = span / (index + 1)
        breaks = np.linspace(low, high, index + 1)
        breaks[-1] = high
        counts = _hist_counts(values, breaks)
        mean = float(np.mean(counts))
        variance = float(np.sum((counts - mean) ** 2) / (index + 1))
        cost[index - 1] = (2 * mean - variance) / width**2
    chosen = int(np.argmin(cost)) + 1
    breaks = np.linspace(low, high, chosen + 1)
    breaks[-1] = high
    counts = _hist_counts(values, breaks)
    widths = np.diff(breaks)
    total = float(np.sum(counts))
    density = counts / (total * widths) if total else np.zeros_like(counts)
    mids = (breaks[:-1] + breaks[1:]) / 2.0
    result = {
        "breaks": breaks,
        "counts": counts,
        "density": density,
        "mids": mids,
    }
    if plotting:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        plt.figure()
        plt.hist(values, bins=breaks)
    return result
