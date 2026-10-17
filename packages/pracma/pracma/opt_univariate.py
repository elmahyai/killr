"""One-dimensional minimization from pracma."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError
from pracma.opt_helpers import _EPS, _is_numeric, _scalar


def fminbnd(f, a, b, maxiter=1000, maximum=False, tol=1e-07, rel_tol=None, abs_tol=1e-15, *args, **kwargs):
    if rel_tol is None:
        rel_tol = tol
    if not _is_numeric(a) or np.size(a) != 1 or not _is_numeric(b) or np.size(b) != 1:
        raise PracmaError("is.numeric(a) is not TRUE")
    a = float(np.asarray(a).reshape(-1)[0])
    b = float(np.asarray(b).reshape(-1)[0])
    if a >= b:
        raise PracmaError("Interval end points must fulfill  a < b !")
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")
    sign = -1.0 if maximum else 1.0

    def objective(x):
        return sign * _scalar(f(x, *args, **kwargs))

    phi = 0.5 * (3.0 - math.sqrt(5.0))
    xl, xu = a, b
    xmin = xl + phi * (xu - xl)
    fmin = objective(xmin)
    step = step2 = 0.0
    xmin1 = xmin2 = xmin
    fmin1 = fmin2 = fmin
    iteration = 0
    while iteration < maxiter:
        tolx = rel_tol * abs(xmin) + abs_tol
        xm = (xu + xl) / 2
        if abs(xmin - xm) <= 2 * tolx - (xu - xl) / 2:
            break
        iteration += 1
        pp = qq = 0.0
        if abs(step2) > tolx:
            rr = (xmin - xmin1) * (fmin - fmin2)
            qq = (xmin - xmin2) * (fmin - fmin1)
            pp = (xmin - xmin2) * qq - (xmin - xmin1) * rr
            qq = 2 * (qq - rr)
            if qq > 0:
                pp = -pp
            else:
                qq = -qq
        if abs(pp) < abs(qq * step2 / 2) and pp < qq * (xu - xmin) and pp < qq * (xmin - xl):
            step2 = step
            step = pp / qq
            xtemp = xmin + step
            if (xtemp - xl) < 2 * tolx or (xu - xtemp) < 2 * tolx:
                step = tolx if xmin < xm else -tolx
        else:
            step2 = xu - xmin if xmin < xm else xl - xmin
            step = phi * step2
        if abs(step) >= tolx:
            xnew = xmin + step
        else:
            xnew = xmin + (tolx if step > 0 else -tolx)
        fnew = objective(xnew)
        if fnew <= fmin:
            if xnew < xmin:
                xu = xmin
            else:
                xl = xmin
            xmin2, fmin2 = xmin1, fmin1
            xmin1, fmin1 = xmin, fmin
            xmin, fmin = xnew, fnew
        else:
            if xnew < xmin:
                xl = xnew
            else:
                xu = xnew
            if xnew <= xmin1 or xmin1 == xmin:
                xmin2, fmin2 = xmin1, fmin1
                xmin1, fmin1 = xnew, fnew
            elif xnew <= xmin2 or xmin2 == xmin or xmin2 == xmin1:
                xmin2, fmin2 = xnew, fnew
    return {"xmin": xmin, "fmin": fmin, "niter": iteration, "estim.prec": abs(step)}


def fibsearch(f, a, b, *args, endp=False, tol=_EPS**0.5, **kwargs):
    a = float(a)
    b = float(b)
    if a >= b:
        raise PracmaError("Left endpoint a must be smaller than b.")
    tol = max(float(tol), _EPS)
    fib = [0.0, 1.0, 2.0]
    n = 2
    while fib[n] <= 2 * (b - a) / tol:
        fib.append(fib[n] + fib[n - 1])
        n += 1
    x1, x2 = a, b
    xa = a + (b - a) * fib[n - 2] / fib[n]
    xb = a + (b - a) * fib[n - 1] / fib[n]
    fxa = _scalar(f(xa, *args, **kwargs))
    fxb = _scalar(f(xb, *args, **kwargs))
    k = 1
    while k <= n - 3 and xa < xb and (x2 - x1) >= tol:
        if fxa > fxb:
            x1 = xa
            xa = xb
            xb = x1 + (x2 - x1) * fib[n - k - 1] / fib[n - k]
            fxa = fxb
            fxb = _scalar(f(xb, *args, **kwargs))
        else:
            x2 = xb
            xb = xa
            xa = x1 + (x2 - x1) * fib[n - k - 2] / fib[n - k]
            fxb = fxa
            fxa = _scalar(f(xa, *args, **kwargs))
        k += 1
    xmin = (xa + xb) / 2
    fmin = _scalar(f(xmin, *args, **kwargs))
    if endp:
        fa = _scalar(f(a, *args, **kwargs))
        fb = _scalar(f(b, *args, **kwargs))
        if xmin - a < tol and fa < fmin:
            xmin, fmin = a, fa
        elif b - xmin < tol and fb < fmin:
            xmin, fmin = b, fb
    return {"xmin": xmin, "fmin": fmin, "niter": k, "estim.prec": max(xmin - x1, x2 - xmin)}


def shubert(f, a, b, L, crit=1e-04, nmax=1000):
    if not _is_numeric(a) or not _is_numeric(b) or np.size(a) != 1 or np.size(b) != 1:
        raise PracmaError("is.numeric(a) is not TRUE")
    a = float(np.asarray(a).reshape(-1)[0])
    b = float(np.asarray(b).reshape(-1)[0])
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")
    x0 = (a + b) / 2.0
    y0 = _scalar(f(x0))
    xmax, ymax = x0, y0
    fmax = y0 + L * (b - a) / 2.0
    X = np.zeros(nmax)
    Z = np.zeros(nmax)
    X[0] = b
    Z[0] = y0 + fmax
    X[1] = a
    Z[1] = y0 + fmax
    n = 2
    while (fmax - ymax) > crit and n < nmax:
        xn = X[n - 1]
        zn = Z[n - 1]
        yn = _scalar(f(xn))
        if yn > ymax:
            xmax, ymax = xn, yn
        zL = zR = (zn + yn) / 2.0
        xL = xn - (zn - yn) / 2.0 / L
        xR = xn + (zn - yn) / 2.0 / L
        i1 = 1 if a <= xL <= b else 0
        i2 = 1 if a <= xR <= b else 0
        if i1 == 1 and i2 == 0:
            X[n - 1], Z[n - 1] = xL, zL
        elif i1 == 0 and i2 == 1:
            X[n - 1], Z[n - 1] = xR, zR
        elif i1 == 1 and i2 == 1:
            X[n - 1], Z[n - 1] = xL, zL
            X[n], Z[n] = xR, zR
            n += 1
        order = np.argsort(Z[:n], kind="stable")
        Z[:n] = Z[:n][order]
        X[:n] = X[:n][order]
        fmax = Z[n - 1]
    return {"xopt": xmax, "fopt": fmax, "nopt": n}
