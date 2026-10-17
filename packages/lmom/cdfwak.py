"""Wakeby CDF, a port of CDFWAK in lmom 3.3 src/lmoments.f.

para = (xi, a, b, c, d). For each finite x the quantile equation x = G(z)
is solved for z = -log(1 - F) by Halley's method, with the Newton fallback,
the step limit, and the step-back rule of the Fortran. The R wrapper maps
-Inf to 0, Inf to 1, and NA to NA, and calls the Fortran only on finite x.

The Fortran routine returns from the whole subroutine when -z falls below
the underflow limit. The values after that element stay 0, as R allocates
them, and this port does the same.
"""
from __future__ import annotations

import warnings

import numpy as np

from ._cdf_common import scalarize

_EPS = np.float64(1e-8)
_MAXIT = 20
_ZINCMX = np.float64(3.0)
_ZMULT = np.float64(0.2)
_UFL = np.float64(-170.0)
_HALF = np.float64(0.5)
_ONE = np.float64(1.0)
_ZERO = np.float64(0.0)


def _valid(a, b, c, d):
    if b + d <= 0 and (b != 0 or c != 0 or d != 0):
        return False
    if a == 0 and b != 0:
        return False
    if c == 0 and d != 0:
        return False
    if c < 0 or a + c < 0:
        return False
    if a == 0 and c == 0:
        return False
    return True


def _shape_terms(z, b, d):
    eb = _ZERO
    bz = -b * z
    if bz >= _UFL:
        eb = np.exp(bz)
    gb = z
    if abs(b) > _EPS:
        gb = (_ONE - eb) / b
    ed = np.exp(d * z)
    gd = -z
    if abs(d) > _EPS:
        gd = (_ONE - ed) / d
    return eb, gb, ed, gd


def _quantile(z, xi, a, b, c, d):
    _, gb, _, gd = _shape_terms(z, b, d)
    return xi + a * gb - c * gd


def _to_prob(z, ifail):
    """Label 200: CDF = 1 - exp(-z), or return from the subroutine."""
    if -z < _UFL:
        return _ONE, ifail, True
    return _ONE - np.exp(-z), ifail, False


def _wak_one(xx, xi, a, b, c, d, q10, q99):
    """CDF at one finite x. Returns (cdf, ifail, stop_subroutine)."""
    if xx <= xi:
        return _ZERO, 0, False
    if b == 0 and c == 0 and d == 0:
        return _to_prob((xx - xi) / a, 0)
    if c == 0:
        if xx >= xi + a / b:
            return _ONE, 0, False
        return _to_prob(-np.log(_ONE - (xx - xi) * b / a) / b, 0)
    if a == 0:
        return _to_prob(np.log(_ONE + (xx - xi) * d / c) / d, 0)

    if d < 0 and xx >= xi + a / b - c / d:
        return _ONE, 0, False

    z = np.float64(0.7)
    if xx < q10:
        z = _ZERO
    if xx >= q99:
        if d < 0:
            z = np.log((xx - xi - a / b) * d / c + _ONE) / d
        if d == 0:
            z = (xx - xi - a / b) / c
        if d > 0:
            z = np.log((xx - xi) * d / c + _ONE) / d

    ifail = 0
    for _ in range(_MAXIT):
        eb, gb, ed, gd = _shape_terms(z, b, d)
        xest = xi + a * gb - c * gd
        func = xx - xest
        deriv1 = a * eb + c * ed
        deriv2 = -a * b * eb + c * d * ed
        temp = deriv1 + _HALF * func * deriv2 / deriv1
        if temp <= 0:
            temp = deriv1
        zinc = func / temp
        if zinc > _ZINCMX:
            zinc = _ZINCMX
        znew = z + zinc
        if znew <= 0:
            z = z * _ZMULT
            continue
        z = znew
        if abs(zinc) <= _EPS:
            break
    else:
        ifail = 7010

    return _to_prob(z, ifail)


def cdfwak(x, para=(0.0, 1.0, 0.0, 0.0, 0.0)):
    p = np.asarray(para, dtype=float).ravel()
    if p.size != 5:
        raise ValueError("parameter vector has wrong length - should be 5")
    if np.any(np.isnan(p)):
        raise ValueError("missing values in parameter vector")
    xi, a, b, c, d = (np.float64(v) for v in p)
    if not _valid(a, b, c, d):
        raise ValueError("distribution parameters invalid")

    xs = np.asarray(x, dtype=float)
    flat = xs.ravel()
    result = np.full(flat.shape, np.nan)
    result[flat == -np.inf] = 0.0
    result[flat == np.inf] = 1.0

    not_converged = False
    stopped = False
    with np.errstate(all="ignore"):
        q10 = _quantile(np.float64(0.1), xi, a, b, c, d)
        q99 = _quantile(np.float64(5.0), xi, a, b, c, d)
        for i in np.flatnonzero(np.isfinite(flat)):
            if stopped:
                result[i] = 0.0
                continue
            value, ifail, stopped = _wak_one(np.float64(flat[i]), xi, a, b, c, d, q10, q99)
            result[i] = value
            if ifail == 7010:
                not_converged = True

    if not_converged:
        warnings.warn("iteration did not converge - some cdf values not computed",
                      RuntimeWarning, stacklevel=2)
    return scalarize(x, result.reshape(xs.shape))
