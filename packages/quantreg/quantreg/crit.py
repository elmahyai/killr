"""Hotelling tube critical value, the root R's uniroot returns."""

from __future__ import annotations

import math

from scipy.stats import norm, t


def critval(kappa, alpha=0.05, rdf=0):
    """Critical value for a uniform band. rdf <= 0 uses the normal tail."""
    kappa = float(kappa)
    alpha = float(alpha)
    rdf = float(rdf)

    def tube(x):
        if rdf <= 0:
            tail = kappa * math.exp(-(x * x) / 2.0) / math.pi + 2.0 * (1.0 - float(norm.cdf(x)))
        else:
            tail = kappa * (1.0 + x * x / rdf) ** (-rdf / 2.0) / math.pi + 2.0 * (1.0 - float(t.cdf(x, rdf)))
        return tail - alpha

    # R uniroot on c(1, 5). The default tolerance is .Machine$double.eps^0.25.
    return _uniroot(tube, 1.0, 5.0, (2.0 ** -52) ** 0.25)


_EPSILON = 2.220446049250313e-16


def _uniroot(func, lower, upper, tol, maxit=1000):
    """R_zeroin2, the root uniroot returns."""
    a = float(lower)
    b = float(upper)
    fa = func(a)
    fb = func(b)
    if fa * fb > 0:
        raise ValueError("f() values at end points not of opposite sign")
    c = a
    fc = fa
    remaining = maxit + 1
    if fa == 0.0:
        return a
    if fb == 0.0:
        return b
    while remaining:
        remaining -= 1
        prev_step = b - a
        if abs(fc) < abs(fb):
            a = b
            b = c
            c = a
            fa = fb
            fb = fc
            fc = fa
        tol_act = 2 * _EPSILON * abs(b) + tol / 2
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
            if p > 0.0:
                q = -q
            else:
                p = -p
            if p < (0.75 * cb * q - abs(tol_act * q) / 2) and p < abs(prev_step * q / 2):
                new_step = p / q
        if abs(new_step) < tol_act:
            new_step = tol_act if new_step > 0.0 else -tol_act
        a = b
        fa = fb
        b += new_step
        fb = func(b)
        if (fb > 0 and fc > 0) or (fb < 0 and fc < 0):
            c = a
            fc = fa
    return b
