"""Censored Q-Q comparison data, translated from fitdistrplus."""

from __future__ import annotations

import warnings
import numpy as np
from scipy import stats


def _turnbull_intervals(left, right):
    """Return Turnbull maximal intersections and their NPMLE masses."""
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    left = np.where(np.isnan(left), -np.inf, left)
    right = np.where(np.isnan(right), np.inf, right)
    if not np.any(np.isfinite(np.r_[left, right])):
        raise ValueError("censdata has no finite endpoint")
    # For the usual fitdistcens representation, each row is already a
    # maximal intersection (the package's NPMLE helper preserves these
    # boundaries, including open-ended rows).
    intervals = sorted(set(zip(left.tolist(), right.tolist())),
                       key=lambda z: (z[0], z[1]))
    if not intervals:
        raise ValueError("unable to construct Turnbull intervals")
    counts = np.array([np.sum((left == a) & (right == b))
                       for a, b in intervals], dtype=float)
    return (np.array([x[0] for x in intervals]),
            np.array([x[1] for x in intervals]), counts / counts.sum())


def _r_quantile(distname, probabilities, estimate, fix_arg=None):
    """Call the SciPy equivalent of an R q* function."""
    params = {} if fix_arg is None else dict(fix_arg)
    params.update(dict(estimate))
    p = np.asarray(probabilities, dtype=float)
    name = distname.lower()
    if name == "norm":
        return stats.norm.ppf(p, loc=params.get("mean", 0.0),
                               scale=params.get("sd", 1.0))
    if name == "lnorm":
        return stats.lognorm.ppf(p, params.get("sdlog", 1.0),
                                 loc=0.0, scale=np.exp(params.get("meanlog", 0.0)))
    if name == "logis":
        return stats.logistic.ppf(p, loc=params.get("location", 0.0),
                                  scale=params.get("scale", 1.0))
    if name == "exp":
        return stats.expon.ppf(p, scale=1.0 / params.get("rate", 1.0))
    if name == "weibull":
        return stats.weibull_min.ppf(p, params["shape"],
                                     scale=params.get("scale", 1.0))
    scipy_dist = getattr(stats, name, None)
    if scipy_dist is None or not hasattr(scipy_dist, "ppf"):
        raise ValueError(f"unsupported distribution: {distname}")
    positional = [v for k, v in params.items() if k not in ("loc", "scale")]
    return scipy_dist.ppf(p, *positional, loc=params.get("loc", 0.0),
                          scale=params.get("scale", 1.0))


def qqcompcens(
    ft, xlim=None, ylim=None, xlogscale=False, ylogscale=False,
    NPMLE_method="Wang", ynoise=True, **kwargs
):
    """Compute censored Q-Q rectangles for one or more fitdistcens results.

    The returned dictionary contains the interval endpoints and theoretical
    endpoints; it is deliberately plot-library neutral.
    """
    fits = [ft] if isinstance(ft, dict) else list(ft)
    if not fits or any(not isinstance(x, dict) for x in fits):
        raise TypeError("ft must be a fitdistcens dictionary or list of dictionaries")
    method = NPMLE_method
    if method == "Turnbull.middlepoints":
        warnings.warn("Turnbull.middlepoints uses Turnbull.intervals here")
        method = "Turnbull.intervals"
    if method not in ("Wang", "Turnbull.intervals"):
        raise ValueError("invalid NPMLE_method")
    data = fits[0]["censdata"]
    left, right = np.asarray(data["left"], float), np.asarray(data["right"], float)
    for fit in fits[1:]:
        if not (np.array_equal(np.asarray(fit["censdata"]["left"]), left, equal_nan=True)
                and np.array_equal(np.asarray(fit["censdata"]["right"]), right, equal_nan=True)):
            raise ValueError("all compared fits must use the same dataset")
    lo, hi, mass = _turnbull_intervals(left, right)
    before = np.r_[0.0, np.cumsum(mass)[:-1]]
    after = np.cumsum(mass)
    # R's boundary replacement is only for drawing; retain the finite
    # substitutes in the returned values so callers can compare plot data.
    finite = np.r_[lo[np.isfinite(lo)], hi[np.isfinite(hi)]]
    lower, upper = finite.min(), finite.max()
    width = upper - lower
    if xlim is None and ylim is None:
        if xlogscale:
            xlim = [lower * (upper / lower) ** -.1, upper * (upper / lower) ** .1]
        else:
            xlim = [lower - .1 * width, upper + .1 * width]
        ylim = list(xlim)
    elif xlim is None:
        xlim = list(ylim)
    elif ylim is None:
        ylim = list(xlim)
    rectangles = []
    for fit in fits:
        qlo = _r_quantile(fit["distname"], before, fit["estimate"], fit.get("fix.arg"))
        qhi = _r_quantile(fit["distname"], after, fit["estimate"], fit.get("fix.arg"))
        rectangles.append({
            "theoretical_left": qlo, "theoretical_right": qhi,
            "empirical_left": lo.copy(), "empirical_right": hi.copy(),
        })
    return {"rectangles": rectangles, "xlim": np.asarray(xlim), "ylim": np.asarray(ylim),
            "probability_low": before, "probability_high": after,
            "left": lo, "right": hi, "p": mass}
