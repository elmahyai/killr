"""Exact binomial tests for comparing two digital libraries.

Translated from statmod 1.5.2 ``sage.test`` in ``R/sagetest.R``.
"""

from __future__ import annotations

import math

import numpy as np

_MISSING = object()


def sage_test(x, y, n1=_MISSING, n2=_MISSING):
    """Two-sided binomial p-values for tag counts in two libraries."""
    x_arr = np.asarray(x, dtype=float).reshape(-1)
    y_arr = np.asarray(y, dtype=float).reshape(-1)
    if np.any(np.isnan(x_arr)) or np.any(np.isnan(y_arr)):
        raise ValueError("missing values not allowed")
    if x_arr.size != y_arr.size:
        raise ValueError("x and y must have same length")

    x_i = np.rint(x_arr).astype(int)
    y_i = np.rint(y_arr).astype(int)
    if np.any(x_i < 0) or np.any(y_i < 0):
        raise ValueError("x and y must be non-negative")

    n1_provided = n1 is not _MISSING
    n2_provided = n2 is not _MISSING
    if n1 is _MISSING:
        n1_i = int(np.sum(x_i))
    else:
        n1_i = int(np.rint(float(n1)))
    if n2 is _MISSING:
        n2_i = int(np.sum(y_i))
    else:
        n2_i = int(np.rint(float(n2)))

    if n1_provided and np.any(x_i > n1_i):
        raise ValueError("x cannot be greater than n1")
    if n2_provided and np.any(y_i > n2_i):
        raise ValueError("y cannot be greater than n2")

    size = x_i + y_i
    p_value = np.ones(x_i.shape, dtype=float)

    if n1_i == n2_i:
        positive = size > 0
        if np.any(positive):
            x_sym = np.minimum(x_i[positive], y_i[positive])
            sizes = size[positive]
            out = np.empty(positive.sum(), dtype=float)
            for index, (xx, sz) in enumerate(zip(x_sym, sizes)):
                out[index] = min(2.0 * _pbinom(int(xx), int(sz), 0.5), 1.0)
            p_value[positive] = out
        return p_value.reshape(np.asarray(x).shape)

    prob = n1_i / (n1_i + n2_i)
    big = size > 10000
    if np.any(big):
        for index in np.flatnonzero(big):
            p_value[index] = _chisq_test_2x2(
                int(x_i[index]),
                int(y_i[index]),
                n1_i - int(x_i[index]),
                n2_i - int(y_i[index]),
            )

    mask = (size > 0) & ~big
    if np.any(mask):
        sizes0 = size[mask]
        for isize in np.unique(sizes0):
            idx = mask & (size == isize)
            probs = _dbinom_row(int(isize), prob)
            cumsump = _cumsump_by_smallest(probs)
            xs = x_i[idx]
            p_value[idx] = cumsump[xs]

    return p_value.reshape(np.asarray(x).shape)


def _dbinom_row(size: int, prob: float) -> np.ndarray:
    out = np.empty(size + 1, dtype=float)
    tail = 1.0 - prob
    for k in range(size + 1):
        out[k] = math.comb(size, k) * (prob**k) * (tail ** (size - k))
    return out


def _order_p(probs: np.ndarray) -> np.ndarray:
    """``order(p)`` on probabilities, matching R tie-breaking on tied counts."""
    indices = np.arange(probs.size)
    return indices[np.lexsort((-indices, probs))]


def _cumsump_by_smallest(probs: np.ndarray) -> np.ndarray:
    o = _order_p(probs)
    cs = np.cumsum(probs[o])
    oo = np.argsort(o + 1, kind="stable")
    return cs[oo]


def _pbinom(q: int, size: int, prob: float) -> float:
    if q < 0:
        return 0.0
    if q >= size:
        return 1.0
    tail = 1.0 - prob
    total = 0.0
    for k in range(q + 1):
        total += math.comb(size, k) * (prob**k) * (tail ** (size - k))
    return total


def _chisq_test_2x2(a: int, b: int, c: int, d: int) -> float:
    """Pearson chi-square with Yates' correction, matching ``stats::chisq.test``."""
    table = np.array([[a, c], [b, d]], dtype=float)
    total = float(np.sum(table))
    row = np.sum(table, axis=1)
    col = np.sum(table, axis=0)
    expected = np.outer(row, col) / total
    diff = np.abs(table - expected) - 0.5
    diff[diff < 0.0] = 0.0
    statistic = float(np.sum(diff * diff / expected))
    return _pchisq(statistic, 1.0, lower_tail=False)


def _pnorm(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _pchisq(q: float, df: float, *, lower_tail: bool = True) -> float:
    if math.isnan(q) or math.isnan(df) or df <= 0:
        return math.nan
    if df == 1.0:
        root = math.sqrt(max(q, 0.0))
        if lower_tail:
            return 2.0 * _pnorm(root) - 1.0
        return 2.0 * (1.0 - _pnorm(root))
    raise ValueError("only df=1 is supported")
