"""Gap statistic and the standard-error rules for choosing k."""

from __future__ import annotations

import math

import numpy as np

from cluster._rng import unif


def _sample_variance(values):
    data = np.asarray(values, dtype=float)
    count = data.size
    if count < 2:
        return float("nan")
    mean = float(data.mean())
    return float(np.sum((data - mean) ** 2) / (count - 1))


def _pairwise(block, power):
    rows = np.asarray(block, dtype=float)
    count = rows.shape[0]
    if count <= 1:
        return 0.0
    total = 0.0
    for left in range(count):
        for right in range(left + 1, count):
            diff = rows[left] - rows[right]
            distance = float(np.sqrt(np.dot(diff, diff)))
            total += distance ** power
    return total / count


def _log_w(data, k, cluster, power, extra):
    n = data.shape[0]
    if k > 1:
        fit = cluster(data, k, **extra)
        labels = fit["cluster"] if isinstance(fit, dict) else fit
        labels = [int(v) for v in np.asarray(labels).reshape(-1)]
    else:
        labels = [1] * n
    groups = {}
    for index, label in enumerate(labels):
        groups.setdefault(label, []).append(index)
    total = 0.0
    for indexes in groups.values():
        total += _pairwise(data[indexes], power)
    return math.log(0.5 * total)


def clus_gap(x, cluster, k_max, b=100, d_power=1, space_h0="scaledPCA", verbose=False, **extra):
    """Tibshirani gap statistic. ``cluster(data, k)`` returns ``{"cluster": labels}``."""
    data = np.asarray(x, dtype=float)
    if data.ndim != 2:
        raise ValueError("x must be a matrix")
    n, p = data.shape
    k_max = int(k_max)
    b = int(b)
    if k_max < 2 or n < 1 or p < 1 or b <= 0:
        raise ValueError("invalid clusGap arguments")
    if space_h0 not in {"scaledPCA", "original"}:
        raise ValueError("invalid 'spaceH0'")
    power = float(d_power)
    log_w = np.empty(k_max)
    for k in range(1, k_max + 1):
        log_w[k - 1] = _log_w(data, k, cluster, power, extra)
    centered = data - data.mean(axis=0)
    if space_h0 == "scaledPCA":
        _u, _d, vt = np.linalg.svd(centered, full_matrices=False)
        rotation = vt.T
        rotated = centered @ rotation
    else:
        rotation = None
        rotated = centered
    ranges = np.vstack([rotated.min(axis=0), rotated.max(axis=0)])
    log_wks = np.empty((b, k_max))
    width = rotated.shape[1]
    for sample in range(b):
        drawn = np.empty((n, width))
        for column in range(width):
            low = float(ranges[0, column])
            high = float(ranges[1, column])
            if low == high:
                drawn[:, column] = low
            else:
                for row in range(n):
                    drawn[row, column] = low + (high - low) * unif()
        if space_h0 == "scaledPCA":
            reference = drawn @ rotation.T
        else:
            reference = drawn
        reference = reference + data.mean(axis=0)
        for k in range(1, k_max + 1):
            log_wks[sample, k - 1] = _log_w(reference, k, cluster, power, extra)
    expected = log_wks.mean(axis=0)
    se = np.sqrt((1.0 + 1.0 / b) * np.array([_sample_variance(log_wks[:, k]) for k in range(k_max)]))
    gap = expected - log_w
    table = np.column_stack([log_w, expected, gap, se])
    return {
        "tab": table.tolist(),
        "space_h0": space_h0,
        "n": n,
        "b": b,
    }


def max_se(f, se_f, method="firstSEmax", se_factor=1):
    """Index (1-based) of the gap curve under one of the five SE rules."""
    methods = ("firstSEmax", "Tibs2001SEmax", "globalSEmax", "firstmax", "globalmax")
    if method not in methods:
        hits = [name for name in methods if name.startswith(method)]
        if len(hits) != 1:
            raise ValueError("invalid method")
        method = hits[0]
    values = [float(v) for v in np.asarray(f, dtype=float).reshape(-1)]
    se = [float(v) for v in np.asarray(se_f, dtype=float).reshape(-1)]
    k = len(values)
    if k < 1 or k != len(se) or any(v < 0 for v in se) or se_factor < 0:
        raise ValueError("invalid maxSE arguments")
    fse = [se_factor * v for v in se]
    if method == "firstmax":
        for index in range(k - 1):
            if values[index + 1] - values[index] <= 0:
                return index + 1
        return k
    if method == "globalmax":
        best = 0
        for index in range(1, k):
            if values[index] > values[best]:
                best = index
        return best + 1
    if method == "Tibs2001SEmax":
        adjusted = [values[i] - fse[i] for i in range(k)]
        for index in range(k - 1):
            if values[index] >= adjusted[index + 1]:
                return index + 1
        return k
    if method == "firstSEmax":
        nc = k
        for index in range(k - 1):
            if values[index + 1] - values[index] <= 0:
                nc = index + 1
                break
        for index in range(nc - 1):
            if values[index] >= values[nc - 1] - fse[nc - 1]:
                return index + 1
        return nc
    nc = 1
    for index in range(1, k):
        if values[index] > values[nc - 1]:
            nc = index + 1
    for index in range(nc - 1):
        if values[index] >= values[nc - 1] - fse[nc - 1]:
            return index + 1
    return nc
