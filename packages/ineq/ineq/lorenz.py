"""Empirical Lorenz curve, Mehran bound, asymmetry, and majorization.

Ports ``Lc``, ``Lc.mehran``, ``Lasym``, and ``major`` from ineq 0.2-13.
Theoretical Lorenz curves and the plot methods live elsewhere.
"""

from __future__ import annotations

import numpy as np


def Lc(x, n=None, plot: bool = False):
    """Empirical ordinary and generalized Lorenz curve.

    ``n`` defaults to a vector of ones with the same length as ``x``,
    matched to ``x`` before missing values are dropped. After the
    observations are ordered, each ``x`` is replaced by ``n * x`` and
    ``L.general`` is ``L * mean(x) / mean(n)`` on those replaced values.
    """
    values = np.asarray(x, dtype=np.float64).reshape(-1)
    if n is None:
        weights = np.ones(values.shape[0], dtype=np.float64)
    else:
        weights = np.asarray(n, dtype=np.float64).reshape(-1)
        if weights.shape[0] != values.shape[0]:
            raise ValueError("n must be the same length as x")

    keep = ~np.isnan(values)
    values = values[keep]
    weights = weights[keep]
    order = np.argsort(values, kind="mergesort")
    values = values[order]
    weights = weights[order]
    values = weights * values

    total_n = np.sum(weights)
    total_x = np.sum(values)
    p = np.concatenate(
        (np.array([0.0], dtype=np.float64), np.cumsum(weights) / total_n)
    )
    lorenz = np.concatenate(
        (np.array([0.0], dtype=np.float64), np.cumsum(values) / total_x)
    )
    general = lorenz * (np.mean(values) / np.mean(weights))
    result = {"p": p, "L": lorenz, "L.general": general}
    if plot:
        from ineq.plots import plot_lc

        plot_lc(result)
    return result


def lc_mehran(x, n):
    """Mehran upper Lorenz curve for grouped data.

    Calls :func:`Lc` for the lower curve, then follows the R loops in
    ``Lc.mehran``, including the filter that keeps only finite ``p``.
    """
    minimal = Lc(x, n=n, plot=False)
    p_obs = np.asarray(minimal["p"], dtype=np.float64)
    lorenz_obs = np.asarray(minimal["L"], dtype=np.float64)
    k = int(p_obs.size)

    p = np.empty(k + 1, dtype=np.float64)
    lorenz = np.empty(k + 1, dtype=np.float64)
    p[1:] = p_obs
    lorenz[1:] = lorenz_obs

    q = np.empty(k + 2, dtype=np.float64)
    q[1] = 0.0
    q[2:] = 1.0
    capital = np.empty(k + 2, dtype=np.float64)
    capital[1 : k + 1] = 0.0
    capital[k + 1] = 1.0

    for i in range(k, 1, -1):
        q[i] = 2.0 * p[i] - q[i + 1]
    for i in range(2, k + 1):
        capital[i] = 2.0 * lorenz[i - 1] - capital[i - 1]

    with np.errstate(divide="ignore", invalid="ignore"):
        beta1 = np.empty(k, dtype=np.float64)
        beta1[1:k] = (lorenz[2 : k + 1] - lorenz[1:k]) / (p[2 : k + 1] - p[1:k])
        beta2_full = np.empty(k, dtype=np.float64)
        beta2_full[1:k] = (capital[2 : k + 1] - capital[1:k]) / (
            q[2 : k + 1] - q[1:k]
        )
        beta2 = np.empty(k - 1, dtype=np.float64)
        beta2[1 : k - 1] = beta2_full[2:k]

        beta = np.zeros(k - 1, dtype=np.float64)
        for i in range(1, k - 1):
            if beta1[i] > beta2[i]:
                beta[i] = beta1[i]
            elif beta2[i] > beta1[i + 1]:
                beta[i] = beta1[i + 1]
            else:
                beta[i] = beta2[i]

        intercept = np.empty(k - 1, dtype=np.float64)
        intercept[1 : k - 1] = lorenz[2:k] - beta[1 : k - 1] * p[2:k]
        if k == 3:
            knots = np.empty(0, dtype=np.float64)
        else:
            knots = (intercept[2 : k - 1] - intercept[1 : k - 2]) / (
                beta[1 : k - 2] - beta[2 : k - 1]
            )
        knots = np.concatenate((knots, np.array([1.0], dtype=np.float64)))
        upper = beta[1 : k - 1] * knots + intercept[1 : k - 1]
        lorenz_out = np.concatenate(
            (
                np.array([0.0, 0.0], dtype=np.float64),
                upper,
                np.array([1.0], dtype=np.float64),
            )
        )
        p_out = np.concatenate(
            (
                np.array([0.0, -intercept[1] / beta[1]], dtype=np.float64),
                knots,
                np.array([1.0], dtype=np.float64),
            )
        )
    finite = np.isfinite(p_out)
    return {"p": p_out[finite], "L": lorenz_out[finite]}


def Lasym(x, n=None, interval: bool = False, na_rm: bool = True):
    """Lorenz asymmetry coefficient of Damgaard and Weiner.

    ``n`` defaults to ones of the original length, before missing ``x``
    values are removed. The mean is the weighted mean, the sum of
    weight times value divided by the sum of the weights. With
    ``na_rm`` false and any missing ``x``, the result is a length-1 or
    length-2 NaN array, depending on ``interval``.
    """
    values = np.asarray(x, dtype=np.float64).reshape(-1)
    if n is None:
        weights = np.ones(values.shape[0], dtype=np.float64)
    else:
        weights = np.asarray(n, dtype=np.float64).reshape(-1)

    if (not na_rm) and np.any(np.isnan(values)):
        return np.full(1 + int(bool(interval)), np.nan, dtype=np.float64)

    values = values[~np.isnan(values)]
    order = np.argsort(values, kind="mergesort")
    values = values[order]
    picked = np.empty(order.shape[0], dtype=np.float64)
    inside = order < weights.shape[0]
    picked[inside] = weights[order[inside]]
    picked[~inside] = np.nan
    weights = picked

    if np.any(np.isnan(values)) or np.any(np.isnan(weights)):
        mu = np.nan
    else:
        mu = float(np.sum(weights * values) / np.sum(weights))

    below = values < mu
    mass_below = float(np.sum(weights[below]))
    mass = float(np.sum(weights))
    total_below = float(np.sum(weights[below] * values[below]))
    total = float(np.sum(weights * values))
    equal = values == mu

    if np.any(equal):
        mass_equal = float(np.sum(weights[equal]))
        at_or_below = below | equal
        total_at_or_below = float(np.sum(weights[at_or_below] * values[at_or_below]))
        coefficient = np.array(
            [
                mass_below / mass + total_below / total,
                (mass_below + mass_equal) / mass + total_at_or_below / total,
            ],
            dtype=np.float64,
        )
        if not interval:
            coefficient = np.array([np.mean(coefficient)], dtype=np.float64)
        return coefficient

    left = _extreme(values[below], largest=True)
    right = _extreme(values[~below], largest=False)
    delta = (mu - left) / (right - left)
    return np.array(
        [(mass_below + delta) / mass + (total_below + delta * right) / total],
        dtype=np.float64,
    )


def major(x, y) -> bool:
    """Return whether ``x`` majorizes ``y``.

    Both vectors are sorted ascending. The result is true when they have
    the same length, the same sum, and every partial sum of ``x`` is at
    most the partial sum of ``y``. It is false when those totals match
    but the partial-sum test fails. Different lengths or totals raise
    ``ValueError``.
    """
    left = np.sort(np.asarray(x, dtype=np.float64).reshape(-1))
    right = np.sort(np.asarray(y, dtype=np.float64).reshape(-1))
    if left.shape[0] == right.shape[0] and np.sum(left) == np.sum(right):
        return bool(np.all((np.cumsum(left) - np.cumsum(right)) <= 0.0))
    raise ValueError("incomparable arguments")


def _extreme(values: np.ndarray, largest: bool) -> float:
    """R's max or min, including the empty-vector sentinels."""
    if values.size == 0:
        return float(-np.inf if largest else np.inf)
    if largest:
        return float(np.max(values))
    return float(np.min(values))
