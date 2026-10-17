"""Dissimilarities from cluster::daisy.

All-numeric columns use Euclidean or Manhattan. Gower rescales each
column to its range and averages the absolute differences. The result
is the upper triangle read by rows: d(1,2), d(1,3), d(1,4), d(2,3), ...
"""

from __future__ import annotations

import numpy as np


def _matrix(values):
    data = np.asarray(values, dtype=float)
    if data.ndim != 2:
        raise ValueError("x is not a dataframe or a numeric matrix.")
    return data


def daisy(x, metric="euclidean", stand=False, weights=None):
    """Lower-triangle dissimilarities."""
    data = _matrix(x)
    n, p = data.shape
    kind = str(metric).lower()
    if kind not in {"euclidean", "manhattan", "gower"}:
        raise ValueError("metric must be euclidean, manhattan, or gower")
    if kind == "gower":
        scaled = _gower_scale(data)
        weight = np.ones(p) if weights is None else np.asarray(weights, dtype=float)
        if weight.size == 1:
            weight = np.repeat(weight, p)
        if weight.size != p:
            raise ValueError("'weights' must be of length p (or 1)")
        return _pairs(scaled, "manhattan", weight)
    scaled = data.copy()
    if stand:
        scaled = scaled - np.nanmean(scaled, axis=0)
        spread = np.nanmean(np.abs(scaled), axis=0)
        spread[spread == 0] = 1
        scaled = scaled / spread
    return _pairs(scaled, kind, None)


def _gower_scale(data):
    low = np.nanmin(data, axis=0)
    span = np.nanmax(data, axis=0) - low
    span[span == 0] = 1
    return (data - low) / span


def _pairs(data, kind, weight):
    n, _ = data.shape
    out = []
    for left in range(n):
        for right in range(left + 1, n):
            diff = data[left] - data[right]
            if weight is None:
                if kind == "manhattan":
                    out.append(float(np.abs(diff).sum()))
                else:
                    out.append(float(np.sqrt(np.square(diff).sum())))
            else:
                out.append(float(np.sum(weight * np.abs(diff)) / np.sum(weight)))
    return out


def meanabsdev(y):
    """Mean absolute deviation from the mean."""
    values = np.asarray(y, dtype=float)
    values = values[~np.isnan(values)]
    if values.size == 0:
        return float("nan")
    return float(np.mean(np.abs(values - np.mean(values))))


def size_diss(d):
    """Number of objects in a lower-triangle dissimilarity."""
    length = len(list(d))
    discr = 1 + 8 * length
    root = int(round(discr ** 0.5))
    if root * root == discr:
        return (1 + root) / 2
    return float("nan")
