"""Null distribution of the Cramer-von Mises statistic: goftest 1.2-3 pCvM (R/cramer.R).

R's besselK(x, nu) is SciPy's kv(nu, x). goftest 1.2-3 has no C for this
distribution, so the series are remade from the R code. Ak() is not called
by the R code and is not translated.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
from scipy.special import kv


def _d2(x):
    z = (x**2) / 4
    b = kv(0.25, z) + kv(0.75, z)
    return b * np.sqrt((x**3) / (8 * np.pi))


def _d3(x):
    z = (x**2) / 4
    b = 2 * kv(0.25, z) + 3 * kv(0.75, z) - kv(1.25, z)
    return b * np.sqrt((x**5) / (32 * np.pi))


def _ed2(x):
    return np.exp(-(x**2) / 4) * _d2(x)


def _ed3(x):
    return np.exp(-(x**2) / 4) * _d3(x)


def _choose_neg_half(k):
    """choose(-1/2, k) as R's choose() gives it: a product below 30, the gamma form above."""
    if k == 0:
        return 1.0
    if k < 30:
        r = -0.5
        for j in range(2, k + 1):
            r *= (-0.5 - j + 1) / j
        return r
    sign = -1.0 if k % 2 else 1.0
    return sign * math.exp(math.lgamma(k + 0.5) - math.lgamma(k + 1) - 0.5 * math.log(math.pi))


def _ak_on_fk(k, x):
    """AkOnFk(k, x): A(k, x) / k!."""
    two_sqrt_x = 2 * np.sqrt(x)
    fk1x = (4 * k + 1) / two_sqrt_x
    fk3x = (4 * k + 3) / two_sqrt_x
    fk5x = (4 * k + 5) / two_sqrt_x
    x34 = x**0.75
    x54 = x**1.25
    if k < 100:
        gf = math.gamma(k + 0.5) / math.gamma(k + 1)
    elif k <= 1e15:
        gf = math.exp(math.lgamma(k + 0.5) - math.lgamma(k + 1))
    else:
        gf = math.exp(-10.0 * k)
    return gf * (
        _ed3(fk1x) / (72 * x54)
        + (2 * k + 1)
        * (
            _ed2(fk3x) / (9 * x34)
            + (2 * k + 3) * _ed3(fk5x) / (12 * x54)
            + 7 * (_ed2(fk1x) + _ed2(fk5x)) / (144 * x34)
        )
    )


def _vinf(x):
    """cdf of the asymptotic distribution, Vinf() in R."""
    m = x.size
    tot = np.zeros(m)
    active = np.ones(m, dtype=bool)
    ok = False
    for k in range(201):
        idx = np.flatnonzero(active)
        xa = x[idx]
        q = (4 * k + 1) ** 2 / (16 * xa)
        z = (
            ((-1.0) ** k)
            * _choose_neg_half(k)
            * math.sqrt(4 * k + 1)
            * np.exp(-q)
            * kv(0.25, q)
            / np.sqrt(xa)
        )
        tot[idx] += z
        active[idx] = np.abs(z) >= 1e-9
        if k > 10:
            ok = not active.any()
            if ok:
                break
    if not ok:
        warnings.warn("Series did not converge after 200 iterations (asymptotic cdf)", stacklevel=3)
    return tot / np.pi


def _psi1(x):
    """Leading term of the small-sample cdf, psi1() in R."""
    m = x.size
    tot = np.zeros(m)
    active = np.ones(m, dtype=bool)
    ok = False
    for k in range(201):
        idx = np.flatnonzero(active)
        z = -_ak_on_fk(k, x[idx]) / np.pi
        tot[idx] += z
        active[idx] = np.abs(z) >= 1e-9
        if k > 20:
            ok = not active.any()
            if ok:
                break
    if not ok:
        warnings.warn("Series did not converge after 200 iterations (small sample cdf)", stacklevel=3)
    return tot + _vinf(x) / 12


def _vn(x, n):
    """First-order small-sample cdf, Vn() in R (Csorgo and Faraway, 1.8)."""
    return _vinf(x) + _psi1(x) / n


def pCvM(q, n=np.inf, lower_tail=True):
    """cdf of the Cramer-von Mises statistic at q. n = Inf gives the limiting law."""
    q = np.asarray(q, dtype=float).ravel()
    nn = min(100.0, n)
    lower = 1.0 / (12.0 * nn)
    upper = nn / 3.0
    p = np.zeros(q.size)
    unknown = np.ones(q.size, dtype=bool)
    zeroes = q <= lower
    p[zeroes] = 0.0
    unknown[zeroes] = False
    ones = q >= upper
    p[ones] = 1.0
    unknown[ones] = False
    if unknown.any():
        xs = q[unknown]
        p[unknown] = _vinf(xs) if math.isinf(n) else _vn(xs, n)
    p[p < 2e-10] = 0.0
    p[(1.0 - p) < 2e-10] = 1.0
    return p if lower_tail else 1.0 - p
