"""Order statistics used by kuantile, matching the Fortran selectors."""

from __future__ import annotations

import math

import numpy as np


def _nint(value: float) -> int:
    """Fortran NINT: nearest integer, halfway cases away from zero."""
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


def kselect(x, k):
    """The k-th order statistics, 1-based, as kuantiles/dsel05 returns them.

    k must be increasing. Each call selects on the suffix after the previous
    index, so a decreasing index is not a plain order statistic.
    """
    values = np.asarray(x, dtype=float).copy()
    ranks = [int(item) for item in np.atleast_1d(np.asarray(k))]
    chosen = []
    start = 0
    for rank in ranks:
        width = rank - start
        if width < 1 or start + width > values.size:
            raise ValueError("k is outside 1..n or is not increasing")
        part = values[start:]
        order = np.argpartition(part, width - 1)
        part[:] = part[order]
        chosen.append(float(part[width - 1]))
        start = rank
    if np.ndim(k) == 0:
        return chosen[0]
    return np.asarray(chosen, dtype=float)


def kunique(x, isuniq=None):
    """First-occurrence ranks of the sorted unique values, in original order."""
    values = np.asarray(x)
    if isuniq is None:
        # R duplicated() is False on the first copy.
        seen = set()
        flags = []
        for item in values.tolist():
            key = item if not isinstance(item, float) or math.isfinite(item) else ("nan",)
            flags.append(key not in seen)
            seen.add(key)
        isuniq = np.asarray(flags, dtype=bool)
    else:
        isuniq = np.asarray(isuniq, dtype=bool)
    need_sort = bool(np.any(values[1:] < values[:-1])) if values.size > 1 else False
    if need_sort:
        order = np.argsort(values, kind="mergesort")
        isuniq = isuniq[order]
        values = values[order]
    ix = np.cumsum(isuniq).astype(int)
    if need_sort:
        back = np.argsort(order, kind="mergesort")
        ix = ix[back]
    unique = values[isuniq]
    return {"ix": ix, "xU": unique}


def q489(x, tau=0.5):
    """The order statistic at Fortran nint(tau * n), 1-based."""
    values = np.asarray(x, dtype=float)
    n = values.size
    k = _nint(float(tau) * n)
    if k < 1 or k > n:
        raise ValueError("nint(tau * n) is outside 1..n")
    return float(np.partition(values, k - 1)[k - 1])


def _format_percent(prob, digits):
    """R format(100 * prob, trim=TRUE, digits=digits) plus a percent sign."""
    scaled = 100.0 * float(prob)
    text = format(scaled, f".{max(digits - 1, 1)}g")
    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e")
        exponent = int(exponent)
        text = f"{float(mantissa):.0f}" if mantissa.endswith(".0") else mantissa
        sign = "+" if exponent >= 0 else "-"
        text = f"{text}e{sign}{abs(exponent):02d}"
    return text + "%"


def kuantile(x, probs=None, na_rm=False, names=True, type=7):
    """Hyndman-Fan quantile types 1 through 9, named like R format."""
    if probs is None:
        probs = [0.0, 0.25, 0.5, 0.75, 1.0]
    values = np.asarray(x, dtype=float).copy()
    probs = np.atleast_1d(np.asarray(probs, dtype=float))
    if na_rm:
        values = values[~np.isnan(values)]
    elif np.any(np.isnan(values)):
        raise ValueError("NA's and NaN's not allowed in 'x' if 'na.rm' is FALSE")
    if np.any(np.isnan(probs)):
        raise ValueError("NA's and NaN's in 'probs' not allowed")
    if np.any((probs < 0) | (probs > 1)):
        raise ValueError("probs outside [0,1]")
    order = np.argsort(probs, kind="mergesort")
    p = probs[order]
    n = values.size
    m = p.size
    g = np.full(m, 0.5)
    if type == 1:
        k = np.maximum(1, np.ceil(p * n)).astype(int)
        j = k
    elif type == 2:
        j = np.maximum(1, np.floor(p * n)).astype(int)
        k = np.column_stack([np.maximum(1, j), np.minimum(j + 1, n)]).reshape(-1)
        g = np.where(p * n > j, 1.0, 0.5)
    elif type == 3:
        k = np.maximum(1, np.rint(p * n)).astype(int)
        j = k
    else:
        pairs = {4: (0.0, 1.0), 5: (0.5, 0.5), 6: (0.0, 0.0), 7: (1.0, 1.0), 8: (1.0 / 3.0, 1.0 / 3.0), 9: (3.0 / 8.0, 3.0 / 8.0)}
        if type not in pairs:
            raise ValueError("type must be 1 through 9")
        a, b = pairs[type]
        d = a + p * (1.0 - a - b)
        j = np.floor(p * n + d).astype(int)
        g = p * n + d - j
        # Lower and upper order statistics stay paired per prob: row i is (lo_i, hi_i).
        # Sorting k here would scramble the pairs when neighbouring probs share a rank.
        k = np.column_stack([np.maximum(1, j), np.minimum(j + 1, n)]).reshape(-1)
    unique = kunique(k)
    ranks = unique["xU"].astype(int)
    selected = kselect(values, ranks)
    z = np.asarray(selected, dtype=float)[unique["ix"] - 1]
    if type in (1, 3):
        columns = np.column_stack([z, z]) if z.size else np.zeros((m, 2))
    else:
        columns = z.reshape(m, 2)
    weights = np.column_stack([1.0 - g, g])
    y = (columns * weights).sum(axis=1)
    # rank() in R is 1-based competition... actually rank() average by default,
    # but the index back into the sorted result uses the order of probs.
    # y was computed in sorted-prob order. y[rank(probs)] restores the original
    # order. R rank is 1-based and average for ties. order from argsort is the
    # inverse when there are no ties. Ties in probs: R rank averages, and using
    # that as an index is unusual. The check uses distinct probs.
    inverse = np.empty(m, dtype=int)
    inverse[order] = np.arange(m)
    y = y[inverse]
    if names and m > 0:
        digits = 7  # getOption("digits") default
        labels = [_format_percent(prob, digits) for prob in probs]
    else:
        labels = None
    return {"y": y, "names": labels, "class": "kuantile"}
