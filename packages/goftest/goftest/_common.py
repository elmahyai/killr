"""Helpers shared by the goftest translations.

The R code these follow: uniroot with extendInt = "up" and the zeroin root
finder under it (R_zeroin2), getCdf for a null given by name, braun() for a
composite null, and the htest record that ad.test and cvm.test return.
"""

from __future__ import annotations

import inspect
import math
from dataclasses import dataclass, field

import numpy as np
from scipy.special import ndtr

from boot.rng import sample_int

EPS = float(np.finfo(float).eps)
XMAX = float(np.finfo(float).max)
TOL = EPS**0.25


@dataclass
class HTest:
    """The htest list R returns, without the class attribute."""

    statistic: float
    p_value: float
    statistic_name: str
    method: list = field(default_factory=list)


def punif(x, min=0.0, max=1.0):
    """stats::punif."""
    x = np.asarray(x, dtype=float)
    return np.where(x >= max, 1.0, np.where(x <= min, 0.0, (x - min) / (max - min)))


def pnorm(x, mean=0.0, sd=1.0):
    """stats::pnorm, with the normal cdf from SciPy's ndtr."""
    return ndtr((np.asarray(x, dtype=float) - mean) / sd)


_CDFS = {"punif": punif, "pnorm": pnorm}


def get_cdf(null):
    """getCdf: a function is used as is; a name gets a leading p added first."""
    if callable(null):
        return null
    if isinstance(null, str) and len(null) > 0:
        names = ([] if null.startswith("p") else ["p" + null]) + [null]
        for name in names:
            if name in _CDFS:
                return _CDFS[name]
    raise ValueError("Argument 'null' should be a function, or the name of a function")


def _truncate(x):
    return min(max(x, -XMAX), XMAX)


def _sign(x):
    if math.isnan(x):
        return math.nan
    return float((x > 0) - (x < 0))


def zeroin(f, ax, bx, fa, fb, tol=TOL, maxiter=1000):
    """R's C_zeroin2: Brent's root finder, with the same steps as R."""
    a, b = float(ax), float(bx)
    c, fc = a, float(fa)
    fb = float(fb)
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    left = maxiter + 1
    while left:
        left -= 1
        prev_step = b - a
        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa
        tol_act = 2 * EPS * abs(b) + tol / 2
        new_step = (c - b) / 2
        if abs(new_step) <= tol_act or fb == 0.0:
            return b
        if abs(prev_step) >= tol_act and abs(fa) > abs(fb):
            cb = c - b
            if a == c:
                t1 = fb / fa
                p = cb * t1
                q = 1.0 - t1
            else:
                q = fa / fc
                t1 = fb / fc
                t2 = fb / fa
                p = t2 * (cb * q * (q - t1) - (b - a) * (t1 - 1.0))
                q = (q - 1.0) * (t1 - 1.0) * (t2 - 1.0)
            if p > 0:
                q = -q
            else:
                p = -p
            if p < (0.75 * cb * q - abs(tol_act * q) / 2) and p < abs(prev_step * q / 2):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0 else -tol_act
        a = b
        fa = fb
        b += new_step
        fb = float(f(b))
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c = a
            fc = fa
    return b


def uniroot_up(f, lower, upper, tol=TOL, maxiter=1000):
    """R's uniroot(f, c(lower, upper), extendInt = "upX")$root.

    Used with extendInt = "up", so Sig is 1: the lower end moves down while
    f(lower) > 0, and the upper end moves up while f(upper) < 0.
    """
    lower, upper = float(lower), float(upper)
    if not lower < upper:
        raise ValueError("lower < upper  is not fulfilled")
    f_lower = float(f(lower))
    f_upper = float(f(upper))
    if math.isnan(f_lower):
        raise ValueError("f.lower = f(lower) is NA")
    if math.isnan(f_upper):
        raise ValueError("f.upper = f(upper) is NA")

    f_low_t = _truncate(f_lower)
    f_upp_t = _truncate(f_upper)
    do_x = f_low_t > 0 or f_upp_t < 0
    it = 0
    if do_x:
        delta = 0.01 * max(1e-4, abs(lower))
        while f_lower > 0:
            it += 1
            if it > maxiter:
                raise RuntimeError(f"no sign change found in {it - 1} iterations")
            lower = lower - delta
            f_lower = float(f(lower))
            delta = 2 * delta
        delta = 0.01 * max(1e-4, abs(upper))
        while f_upper < 0:
            it += 1
            if it > maxiter:
                raise RuntimeError(f"no sign change found in {it - 1} iterations")
            upper = upper + delta
            f_upper = float(f(upper))
            delta = 2 * delta
        f_low_t = _truncate(f_lower)
        f_upp_t = _truncate(f_upper)
    if not (_sign(f_lower) * _sign(f_upper) <= 0):
        raise ValueError(
            "did not succeed extending the interval endpoints for f(lower) * f(upper) <= 0"
        )
    return zeroin(f, lower, upper, f_low_t, f_upp_t, tol, maxiter)


def _formal_names(f):
    try:
        return set(inspect.signature(f).parameters)
    except (TypeError, ValueError):
        return set()


def parameter_lines(f0, kwargs):
    """The 'with parameter ...' line of the htest method, as R writes it."""
    names = [k for k in kwargs if k in _formal_names(f0)]
    if not names:
        return []
    pard = [f"{k} = {' '.join(str(v) for v in np.atleast_1d(kwargs[k]))}" for k in names]
    word = "parameter" if len(pard) == 1 else "parameters"
    return [f"with {word}    " + ", ".join(pard)]


def braun(u, simpletest, m):
    """Braun (1980) for a composite null: R's braun().

    The groups come from sample() on the labels 1..n mod m, drawn with
    R's generator, so set.seed in R and boot's set_seed give the same split.
    """
    n = len(u)
    if n < 2 * m:
        raise ValueError("Unsufficient data for Braun's method")
    labels = np.arange(1, n + 1) % m
    order = np.asarray(sample_int(n)) - 1
    group = labels[order]
    stats, pvals, statname = [], [], ""
    for level in sorted(set(group.tolist())):
        stat, pval, statname = simpletest(u[group == level])
        stats.append(stat)
        pvals.append(pval)
    statistic = float(max(stats))
    pvalue = 1.0 - (1.0 - min(pvals)) ** m
    return statistic, pvalue, statname + "max"
