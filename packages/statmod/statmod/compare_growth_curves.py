"""Pairwise permutation tests between groups of growth curves.

Translated from statmod 1.5.2 ``compareGrowthCurves`` in ``R/growthcurve.R``.
"""

from __future__ import annotations

import locale
import math
import sys
import warnings

import numpy as np

from statmod.compare_two_growth_curves import compareTwoGrowthCurves
from statmod.mean_t import mean_t

_ADJUST_METHODS = (
    "holm",
    "hochberg",
    "hommel",
    "bonferroni",
    "BH",
    "BY",
    "fdr",
    "none",
)


def compareGrowthCurves(
    group,
    y,
    levels=None,
    nsim=100,
    fun=None,
    times=None,
    verbose=True,
    adjust="holm",
    n0=0.5,
):
    """All pairwise permutation tests between groups of growth curves.

    Rows of ``y`` are individuals and columns are times. ``times`` uses R's
    1-based column numbers. Groups are compared as character labels, in
    locale sort order, and a group needs two members unless ``levels`` names it.
    """
    if fun is None:
        fun = mean_t
    labels = [_one_label(value) for value in _flatten(group)]
    if levels is None:
        counts = {}
        for label in labels:
            if label is None:
                continue
            counts[label] = counts.get(label, 0) + 1
        lev = [name for name in _r_sort(list(counts)) if counts[name] >= 2]
    else:
        lev = [_one_label(value) for value in _flatten(levels)]
    nlev = len(lev)
    if nlev < 2:
        raise ValueError("Less than 2 groups to compare")
    matrix = _as_matrix(y)
    if times is not None:
        matrix = _select_times(matrix, times)
    n_pairs = nlev * (nlev - 1) // 2
    group1 = [""] * n_pairs
    group2 = [""] * n_pairs
    stat = np.zeros(n_pairs, dtype=float)
    pvalue = np.zeros(n_pairs, dtype=float)
    pair = 0
    labels_array = np.asarray(labels, dtype=object)
    for i in range(nlev - 1):
        for j in range(i + 1, nlev):
            if verbose:
                sys.stdout.write(f"{lev[i]} {lev[j]}")
            pair += 1
            selected = np.array(
                [label in (lev[i], lev[j]) for label in labels], dtype=bool
            )
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", category=RuntimeWarning)
                out = compareTwoGrowthCurves(
                    labels_array[selected],
                    matrix[selected, :],
                    nsim=nsim,
                    fun=fun,
                    n0=n0,
                )
            if verbose:
                shown = _as_character_double(round(float(out["stat"]), 2))
                sys.stdout.write(f"  {shown} \n")
            group1[pair - 1] = lev[i]
            group2[pair - 1] = lev[j]
            stat[pair - 1] = out["stat"]
            pvalue[pair - 1] = out["p.value"]
    return {
        "Group1": np.asarray(group1, dtype=object),
        "Group2": np.asarray(group2, dtype=object),
        "Stat": stat,
        "P.Value": pvalue,
        "adj.P.Value": _p_adjust(pvalue, method=adjust),
    }


def _flatten(values):
    if isinstance(values, str):
        return [values]
    array = np.asarray(values, dtype=object)
    if array.ndim == 0:
        return [array.item()]
    return list(array.reshape(-1))


def _one_label(value):
    """R ``as.character`` for a group id. Missing values stay missing."""
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, str):
        return value
    if isinstance(value, (bytes, np.bytes_)):
        return value.decode()
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return None
        return _as_character_double(number)
    if isinstance(value, np.generic):
        return _one_label(value.item())
    return str(value)


def _as_character_double(value):
    """R ``as.character`` for one double, at the default ``scipen``."""
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0.0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def _r_sort(values):
    """R ``sort`` for character labels in the session collation."""
    previous = locale.setlocale(locale.LC_COLLATE)
    try:
        locale.setlocale(locale.LC_COLLATE, "")
        return sorted(values, key=locale.strxfrm)
    finally:
        locale.setlocale(locale.LC_COLLATE, previous)


def _as_matrix(y):
    matrix = np.asarray(y, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("y must be matrix-like")
    return matrix


def _select_times(matrix, times):
    """R matrix column subscript. Positive numbers are 1-based columns."""
    index = np.asarray(times, dtype=int).reshape(-1)
    if index.size == 0:
        return matrix[:, []]
    if np.any(index == 0):
        raise IndexError("0 is not a valid column")
    if np.all(index > 0):
        chosen = index - 1
        if np.any(chosen < 0) or np.any(chosen >= matrix.shape[1]):
            raise IndexError("subscript out of bounds")
        return matrix[:, chosen]
    if np.all(index < 0):
        drop = {-int(value) for value in index}
        keep = [i for i in range(matrix.shape[1]) if (i + 1) not in drop]
        return matrix[:, keep]
    raise ValueError("only 0's may be mixed with negative subscripts")


def _match_adjust(method):
    if not isinstance(method, str):
        raise ValueError("adjust method must be a string")
    hits = [name for name in _ADJUST_METHODS if name.startswith(method)]
    if len(hits) != 1:
        listed = ", ".join(repr(name) for name in _ADJUST_METHODS)
        if not hits:
            raise ValueError(f"'{method}' should be one of {listed}")
        raise ValueError(f"'{method}' matches more than one of the choices")
    chosen = hits[0]
    if chosen == "fdr":
        return "BH"
    return chosen


def _p_adjust(p, method="holm", n=None):
    """R ``p.adjust`` for the methods ``compareGrowthCurves`` can request."""
    method = _match_adjust(method)
    values = np.asarray(p, dtype=float).reshape(-1)
    # R's default ``n = length(p)`` is lazy. ``p`` is already the non-missing
    # values when that default is forced, so missing p-values do not increase n.
    missing = np.isnan(values)
    if not np.any(missing):
        kept = values
    else:
        kept = values[~missing]
    lp = int(kept.size)
    if n is None:
        n = lp
    n = int(n)
    if n < lp:
        raise ValueError("n must be at least the number of p-values")
    if n <= 1:
        return values.copy()
    if n == 2 and method == "hommel":
        method = "hochberg"
    adjusted = _adjust_non_missing(kept, method, n, lp)
    if not np.any(missing):
        return adjusted
    out = values.copy()
    out[~missing] = adjusted
    return out


def _adjust_non_missing(p, method, n, lp):
    p = np.asarray(p, dtype=float)
    if method == "bonferroni":
        return np.minimum(1.0, n * p)
    if method == "none":
        return p.copy()
    if method == "holm":
        i = np.arange(1, lp + 1, dtype=float)
        order = np.argsort(p, kind="mergesort")
        inverse = np.argsort(order, kind="mergesort")
        scaled = np.minimum(1.0, np.maximum.accumulate((n + 1.0 - i) * p[order]))
        return scaled[inverse]
    if method == "hochberg":
        i = np.arange(lp, 0, -1, dtype=float)
        order = np.argsort(-p, kind="mergesort")
        inverse = np.argsort(order, kind="mergesort")
        scaled = np.minimum(1.0, np.minimum.accumulate((n + 1.0 - i) * p[order]))
        return scaled[inverse]
    if method == "BH":
        i = np.arange(lp, 0, -1, dtype=float)
        order = np.argsort(-p, kind="mergesort")
        inverse = np.argsort(order, kind="mergesort")
        scaled = np.minimum(1.0, np.minimum.accumulate((n / i) * p[order]))
        return scaled[inverse]
    if method == "BY":
        i = np.arange(lp, 0, -1, dtype=float)
        order = np.argsort(-p, kind="mergesort")
        inverse = np.argsort(order, kind="mergesort")
        harmonic = np.sum(1.0 / np.arange(1, n + 1, dtype=float))
        scaled = np.minimum(1.0, np.minimum.accumulate((harmonic * n / i) * p[order]))
        return scaled[inverse]
    if method == "hommel":
        return _hommel(p, n, lp)
    raise ValueError(f"unknown adjust method {method}")


def _hommel(p, n, lp):
    p = np.asarray(p, dtype=float)
    if n > lp:
        p = np.concatenate([p, np.ones(n - lp, dtype=float)])
    i = np.arange(1, n + 1, dtype=float)
    order = np.argsort(p, kind="mergesort")
    p = p[order]
    inverse = np.argsort(order, kind="mergesort")
    start = np.min(n * p / i)
    q = np.full(n, start, dtype=float)
    pa = q.copy()
    for j in range(n - 1, 1, -1):
        left = np.arange(0, n - j + 1)
        right = np.arange(n - j + 1, n)
        denom = np.arange(2, j + 1, dtype=float)
        q1 = np.min(j * p[right] / denom)
        q[left] = np.minimum(j * p[left], q1)
        q[right] = q[n - j]
        pa = np.maximum(pa, q)
    out = np.maximum(pa, p)
    if lp < n:
        return out[inverse[:lp]]
    return out[inverse]
