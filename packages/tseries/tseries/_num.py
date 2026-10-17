"""Least squares, tails, and the small C helpers from tseries."""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.stats import chi2, f as f_dist


def match_arg(arg, choices):
    hits = [choice for choice in choices if choice.startswith(arg)]
    if len(hits) != 1:
        raise ValueError(f"'{arg}' does not match one of {choices}")
    return hits[0]


def pnorm(z, lower_tail=True):
    z = float(z)
    if math.isnan(z):
        return math.nan
    cdf = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return cdf if lower_tail else 1.0 - cdf


def pchisq_sf(stat, df):
    return float(chi2.sf(stat, df))


def pf_sf(stat, df1, df2):
    return float(f_dist.sf(stat, df1, df2))


def approx(x, y, xout, rule=1):
    """R ``approx`` for one output. ``rule`` 1 is NA outside; 2 clamps."""
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    order = np.argsort(x, kind="mergesort")
    x = x[order]
    y = y[order]
    if len(x) > 1:
        keep = np.empty(len(x), dtype=bool)
        keep[0] = True
        keep[1:] = x[1:] != x[:-1]
        x = x[keep]
        y = y[keep]
    point = float(xout)
    if math.isnan(point):
        return math.nan
    if point < x[0] or point > x[-1]:
        if rule == 1:
            return math.nan
        return float(y[0] if point < x[0] else y[-1])
    return float(np.interp(point, x, y))


def embed(y, dimension):
    """R ``embed``. Column 0 is the most recent observation."""
    series = np.asarray(y, dtype=float).reshape(-1)
    dimension = int(dimension)
    if dimension < 1 or dimension > len(series):
        raise ValueError("invalid embed dimension")
    return np.column_stack(
        [series[dimension - 1 - lag : len(series) - lag] for lag in range(dimension)]
    )


def pp_sum(u, lag, total):
    """``tseries_pp_sum``. ``total`` is the variance term the sum is added to."""
    values = np.asarray(u, dtype=float).reshape(-1)
    n = len(values)
    lag = int(lag)
    acc = 0.0
    for i in range(1, lag + 1):
        piece = 0.0
        for j in range(i, n):
            piece += values[j] * values[j - i]
        piece *= 1.0 - (i / (lag + 1.0))
        acc += piece
    acc /= n
    acc *= 2.0
    return float(total) + acc


def lm(y, x):
    """Ordinary least squares. Coefficients follow R: intercept is column 0."""
    response = np.asarray(y, dtype=float).reshape(-1)
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    n, p = design.shape
    beta, _, rank, _ = np.linalg.lstsq(design, response, rcond=None)
    fitted = design @ beta
    resid = response - fitted
    rss = float(np.dot(resid, resid))
    rank = int(rank)
    df = n - rank
    if df <= 0:
        se = np.full(p, math.nan)
        sigma2 = math.nan
    else:
        sigma2 = rss / df
        gram = design.T @ design
        try:
            cov = sigma2 * np.linalg.inv(gram)
            se = np.sqrt(np.clip(np.diag(cov), 0.0, None))
        except np.linalg.LinAlgError:
            se = np.full(p, math.nan)
    return {
        "coef": beta,
        "se": se,
        "resid": resid,
        "fitted": fitted,
        "rank": rank,
        "sigma2": sigma2,
    }


def r_scale(x):
    """R ``scale`` on a vector or on the columns of a matrix. Divisor is n - 1."""
    values = np.asarray(x, dtype=float)
    vector = values.ndim == 1
    if vector:
        values = values.reshape(-1, 1)
    center = values.mean(axis=0)
    spread = values.std(axis=0, ddof=1)
    scaled = (values - center) / spread
    if vector:
        return scaled.reshape(-1)
    return scaled


def prcomp_scores(x):
    """Scores from R ``prcomp(x, scale.=TRUE)``. Signs of columns may flip."""
    scaled = r_scale(x)
    _u, _s, vt = np.linalg.svd(scaled, full_matrices=False)
    return scaled @ vt.T


def ones(n):
    return np.ones(n)


def critical_p(table, sample_sizes, probs, stat, n_obs):
    """Interpolate a Dickey-Fuller style table the way adf.test and pp.test do."""
    table = np.asarray(table, dtype=float)
    width = table.shape[1] if table.ndim == 2 else 1
    if table.ndim == 1:
        table = table.reshape(-1, 1)
    knots = []
    for col in range(width):
        knots.append(approx(sample_sizes, table[:, col], n_obs, rule=2))
    interpol = approx(knots, probs, stat, rule=2)
    outside = approx(knots, probs, stat, rule=1)
    if not math.isnan(stat) and math.isnan(outside):
        if interpol == min(probs):
            warnings.warn("p-value smaller than printed p-value", stacklevel=2)
        else:
            warnings.warn("p-value greater than printed p-value", stacklevel=2)
    return interpol


def htest(**fields):
    return fields
