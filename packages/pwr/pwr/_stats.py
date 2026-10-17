"""Distributions and the root finder pwr borrows from stats.

pnorm is math.erfc. qnorm, the t, F, and chi-square functions are SciPy,
which is already the distribution library. The root finder is R's zeroin.
"""

from __future__ import annotations

import math

from scipy.stats import chi2, f, ncf, nct, ncx2, norm, t

_EPS = 2.220446049250313e-16
_TOL = _EPS ** 0.25


class PwrError(Exception):
    """An error raised with R's stop message."""


def match_arg(value, choices: tuple[str, ...], name: str) -> str:
    """R match.arg. An exact choice wins, otherwise one unique prefix."""
    if isinstance(value, (list, tuple)):
        if list(value) == list(choices):
            return choices[0]
        if len(value) != 1:
            raise PwrError(f"'{name}' must be of length 1")
        value = value[0]
    if not isinstance(value, str):
        raise PwrError(f"'{name}' must be NULL or a character vector")
    if value in choices:
        return value
    matches = [choice for choice in choices if choice.startswith(value)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        listed = ", ".join(repr(choice) for choice in choices)
        raise PwrError(f"'{name}' should be one of {listed}")
    raise PwrError(f"'{name}' matched more than one choice: {', '.join(matches)}")


def pnorm(x: float, lower_tail: bool = True) -> float:
    """Standard normal cdf. The upper tail uses erfc directly."""
    z = x / math.sqrt(2.0)
    if lower_tail:
        return 0.5 * math.erfc(-z)
    return 0.5 * math.erfc(z)


def qnorm(p: float, lower_tail: bool = True) -> float:
    """Standard normal quantile."""
    if lower_tail:
        return float(norm.ppf(p))
    return float(norm.isf(p))


def pt(q: float, df: float, ncp: float = 0.0, lower_tail: bool = True) -> float:
    """t cdf, with a noncentrality parameter when it is not zero."""
    if ncp == 0.0:
        value = float(t.cdf(q, df) if lower_tail else t.sf(q, df))
    else:
        value = float(nct.cdf(q, df, ncp) if lower_tail else nct.sf(q, df, ncp))
    return value


def qt(p: float, df: float, lower_tail: bool = True) -> float:
    """t quantile. pwr does not pass a noncentrality parameter here."""
    if lower_tail:
        return float(t.ppf(p, df))
    return float(t.isf(p, df))


def pf(q: float, df1: float, df2: float, ncp: float = 0.0, lower_tail: bool = True) -> float:
    """F cdf, with a noncentrality parameter."""
    if lower_tail:
        return float(ncf.cdf(q, df1, df2, ncp))
    return float(ncf.sf(q, df1, df2, ncp))


def qf(p: float, df1: float, df2: float, lower_tail: bool = True) -> float:
    """Central F quantile."""
    if lower_tail:
        return float(f.ppf(p, df1, df2))
    return float(f.isf(p, df1, df2))


def pchisq(q: float, df: float, ncp: float = 0.0, lower_tail: bool = True) -> float:
    """Chi-square cdf, with a noncentrality parameter."""
    if lower_tail:
        return float(ncx2.cdf(q, df, ncp))
    return float(ncx2.sf(q, df, ncp))


def qchisq(p: float, df: float, lower_tail: bool = True) -> float:
    """Central chi-square quantile."""
    if lower_tail:
        return float(chi2.ppf(p, df))
    return float(chi2.isf(p, df))


def uniroot(func, lower: float, upper: float, tol: float = _TOL, maxiter: int = 1000) -> float:
    """R uniroot. The search is Brent's zeroin with R's tolerance."""
    fa = func(lower)
    fb = func(upper)
    if math.isnan(fa):
        raise PwrError("f.lower = f(lower) is NA")
    if math.isnan(fb):
        raise PwrError("f.upper = f(upper) is NA")
    if not (math.copysign(1.0, fa) * math.copysign(1.0, fb) <= 0.0 or fa == 0.0 or fb == 0.0):
        raise PwrError("f() values at end points not of opposite sign")
    return _zeroin(lower, upper, fa, fb, func, tol, maxiter)


def _zeroin(ax, bx, fa, fb, func, tol, maxiter) -> float:
    a = ax
    b = bx
    c = a
    fc = fa
    left = maxiter + 1
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    while left:
        left -= 1
        prev_step = b - a
        if abs(fc) < abs(fb):
            # Sequential, as in zeroin.c: c becomes the previous b.
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa
        tol_act = 2.0 * _EPS * abs(b) + tol / 2.0
        new_step = (c - b) / 2.0
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
            if p > 0.0:
                q = -q
            else:
                p = -p
            if p < (0.75 * cb * q - abs(tol_act * q) / 2.0) and p < abs(prev_step * q / 2.0):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0.0 else -tol_act
        a = b
        fa = fb
        b += new_step
        fb = func(b)
        if (fb > 0.0 and fc > 0.0) or (fb < 0.0 and fc < 0.0):
            c = a
            fc = fa
    return b
