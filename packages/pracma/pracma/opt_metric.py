"""Gradient and variable-metric minimizers from pracma."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.opt_helpers import _EPS, _grad, _identical, _is_numeric, _scalar, _warn


def softline(x0, d0, f, g=None):
    if not _is_numeric(x0) or not _is_numeric(d0):
        raise PracmaError("Arguments 'x0' and 'd0' must be numeric vectors.")
    xk = as_1d(x0)
    dk = as_1d(d0)
    if xk.size != dk.size:
        raise PracmaError("Vectors 'x0' and 'd0' must have the same length.")
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")
    if g is None:
        gradient = lambda x: _grad(f, x)
    else:
        if not callable(g):
            raise PracmaError("Argument function 'fun' not known in parent environment.")
        gradient = g
    tau, chi = 0.1, 0.75
    rho, sigma = 0.1, 0.1
    mhat, epsilon = 400, 1e-10
    m = 0
    f0 = _scalar(f(xk))
    gk = as_1d(gradient(xk))
    m += 2
    deltaf0 = f0
    aL, aU = 0.0, 1e9
    fL = f0
    dfL = float(np.sum(gk * dk))
    a0 = 1.0 if abs(dfL) <= epsilon else -2 * deltaf0 / dfL
    if a0 <= 1e-9 or a0 > 1:
        a0 = 1.0
    while True:
        f0 = _scalar(f(xk + a0 * dk))
        m += 1
        if f0 > (fL + rho * (a0 - aL) * dfL) and abs(fL - f0) > epsilon and m < mhat:
            if a0 < aU:
                aU = a0
            denom = 2 * (fL - f0 + (a0 - aL) * dfL)
            a0hat = aL + ((a0 - aL) ** 2 * dfL) / denom
            a0Lhat = aL + tau * (aU - aL)
            if a0hat < a0Lhat:
                a0hat = a0Lhat
            a0Uhat = aU - tau * (aU - aL)
            if a0hat > a0Uhat:
                a0hat = a0Uhat
            a0 = a0hat
        else:
            df0 = float(np.sum(as_1d(gradient(xk + a0 * dk)) * dk))
            m += 1
            if df0 < sigma * dfL and abs(fL - f0) > epsilon and m < mhat and dfL != df0:
                deltaa0 = (a0 - aL) * df0 / (dfL - df0)
                a0hat = 2 * a0 if deltaa0 <= 0 else a0 + deltaa0
                a0Uhat = a0 + chi * (aU - a0)
                if a0hat > a0Uhat:
                    a0hat = a0Uhat
                aL = a0
                a0 = a0hat
                fL = f0
                dfL = df0
            else:
                break
    return max(a0, 1e-5)


def steep_descent(x0, f, g=None, info=False, maxiter=100, tol=_EPS**0.5):
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")
    objective = f
    gradient = (lambda x: _grad(f, x)) if g is None else g
    x = as_1d(x0)
    if info:
        print(0, "\t", x)
    k = 1
    while k <= maxiter:
        f1 = _scalar(objective(x))
        g1 = as_1d(gradient(x))
        z1 = math.sqrt(float(np.sum(g1**2)))
        if z1 == 0:
            _warn(f"Zero gradient at: {x} {f1} -- not applicable.\n")
            return {"xmin": np.nan, "fmin": np.nan, "niter": k}
        g1 = g1 / z1
        a3 = 1.0
        f3 = _scalar(objective(x - a3 * g1))
        while f3 >= f1:
            a3 = a3 / 2
            f3 = _scalar(objective(x - a3 * g1))
            if a3 < tol / 2:
                if info:
                    print("Method of steepest descent converged to:", x)
                x = np.where(np.abs(x) < _EPS, 0.0, x)
                return {"xmin": x, "fmin": _scalar(objective(x)), "niter": k}
        a2 = a3 / 2
        f2 = _scalar(objective(x - a2 * g1))
        h1 = (f2 - f1) / a2
        h2 = (f3 - f2) / (a3 - a2)
        h3 = (h2 - h1) / a3
        a0 = 0.5 * (a2 - h1 / h3)
        f0 = _scalar(objective(x - a0 * g1))
        a = a0 if f0 < f3 else a3
        x = x - a * g1
        if info:
            print(k, "\t", x)
        k += 1
    if k > maxiter:
        _warn("Maximum number of iterations reached -- not converged.\n")
    return {"xmin": np.nan, "fmin": np.nan, "niter": k}


def fletcher_powell(x0, f, g=None, maxiter=1000, tol=_EPS ** (2.0 / 3.0)):
    if tol < _EPS:
        tol = _EPS
    if not _is_numeric(maxiter) or np.size(maxiter) > 1 or float(np.asarray(maxiter).reshape(-1)[0]) < 1:
        raise PracmaError("Argument 'maxiter' must be a positive integer.")
    maxiter = math.floor(float(np.asarray(maxiter).reshape(-1)[0]))
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    x = as_1d(x0)
    n = x.size
    if n == 1:
        raise PracmaError("Function 'f' is univariate; use some other optimization method.")
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")
    gradient = (lambda z: _grad(f, z)) if g is None else g
    H = np.eye(n)
    f0 = _scalar(f(x))
    g0 = as_1d(gradient(x))
    k = 0
    for k in range(1, maxiter + 1):
        s = (-H @ g0.reshape(-1, 1)).reshape(-1)
        f1 = f0
        z = math.sqrt(float(np.sum(s**2)))
        if z == 0:
            return {"xmin": x, "fmin": f1, "ninter": k}
        s = s / z
        a3 = 1.0
        f3 = _scalar(f(x + a3 * s))
        while f3 >= f1:
            a3 = a3 / 2
            f3 = _scalar(f(x + a3 * s))
            if a3 < tol / 2:
                return {"xmin": x, "fmin": f1, "niter": k}
        a2 = a3 / 2
        f2 = _scalar(f(x + a2 * s))
        h1 = (f2 - f1) / a2
        h2 = (f3 - f2) / (a3 - a2)
        h3 = (h2 - h1) / a3
        a0 = 0.5 * (a2 - h1 / h3)
        f0 = _scalar(f(x + a0 * s))
        a = a0 if f0 < f3 else a3
        d = a * s
        xnew = x + d
        fnew = _scalar(f(xnew))
        gnew = as_1d(gradient(xnew))
        y = gnew - g0
        denom = float(np.sum(d * y))
        A = np.outer(d, d) / denom
        Hy = H @ y.reshape(-1, 1)
        quad = y.reshape(1, -1) @ H @ y.reshape(-1, 1)
        B = (Hy @ Hy.T) / float(np.asarray(quad).reshape(-1)[0])
        H = H + A - B
        if float(np.max(np.abs(d))) < tol:
            break
        f0 = fnew
        g0 = gnew
        x = xnew
    if k == maxiter:
        _warn("Max. number of iterations reached -- may not converge.")
    return {"xmin": x, "fmin": _scalar(f(x)), "niter": k}


def _varmetric(par, fn, gr, tol=1e-08, maxiter=0, maxfeval=0):
    par = as_1d(par)
    n = par.size
    if maxiter == 0:
        maxiter = 1000 + 5 * n
    if maxfeval == 0:
        maxfeval = 3000 + 10 * n
    eps = tol
    acctol = 0.0001
    stepredn = 0.2
    offset = 100.0
    stopbadupdate = True
    keepgoing = True
    ifn = ig = 1
    ilast = ig
    bvec = par.copy()
    f = _scalar(fn(bvec))
    fmin = f
    g = as_1d(gr(bvec))
    oldstep = 1.0
    msg = "Status not resolved"
    conv = -1
    gnorm = math.sqrt(float(np.sum(g * g)))
    if gnorm < (1 + abs(fmin)) * eps * eps:
        keepgoing = False
        msg = "Small gradient norm"
        conv = 2
    while keepgoing:
        if ilast == ig:
            B = np.eye(n)
        fmin = f
        par = bvec.copy()
        c = g.copy()
        t = (-B @ g.reshape(-1, 1)).reshape(-1)
        gradproj = float(np.sum(t * g))
        accpoint = False
        if gradproj <= 0:
            changed = True
            steplength = oldstep
            while (f >= fmin) and changed and (not accpoint):
                bvec = par + steplength * t
                changed = not _identical(bvec + offset, par + offset)
                if changed:
                    f = _scalar(fn(bvec))
                    ifn += 1
                    if ifn > maxfeval:
                        msg = "Too many function evaluations"
                        conv = 1
                        changed = False
                        keepgoing = False
                        break
                    if f < fmin:
                        accpoint = f <= fmin + gradproj * steplength * acctol
                    else:
                        steplength = steplength * stepredn
        if accpoint:
            fmin = f
            g = as_1d(gr(bvec))
            ig += 1
            if ig > maxiter:
                keepgoing = False
                msg = "Too many gradient evaluations"
                conv = 1
                break
            par = bvec.copy()
            gnorm = math.sqrt(float(np.sum(g * g)))
            if gnorm < (1 + abs(fmin)) * eps * eps:
                keepgoing = False
                msg = "Small gradient norm"
                conv = 2
                break
            t = steplength * t
            c = g - c
            D1 = float(np.sum(t * c))
            if D1 > 0:
                y = (B.T @ c.reshape(-1, 1)).reshape(-1)
                D2 = float(1 + np.dot(c, y) / D1)
                B = B - (np.outer(t, y) + np.outer(y, t) - D2 * np.outer(t, t)) / D1
            else:
                if ig == ilast + 1:
                    if stopbadupdate and not accpoint:
                        keepgoing = False
                    msg = f"UPDATE NOT POSSIBLE: ilast, ig{ilast}{ig}"
                    conv = 3
                ilast = ig
        else:
            if ig == ilast or abs(gradproj) < (1 + abs(fmin)) * eps * eps:
                keepgoing = False
                if conv < 0:
                    conv = 0
                msg = "fminunc converged"
            else:
                ilast = ig
    return {
        "par": par,
        "value": fmin,
        "counts": {"function": ifn, "gradient": ig},
        "convergence": conv,
        "message": msg,
    }


def fminunc(x0, fn, gr=None, *args, tol=1e-08, maxiter=0, maxfeval=0, **kwargs):
    point = as_1d(x0) if _is_numeric(x0) else np.asarray([])
    if not _is_numeric(x0) or point.size <= 1:
        raise PracmaError("Argument 'x0' must be a vector of length greater than 1.")
    if not callable(fn):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def objective(x):
        return fn(x, *args, **kwargs)

    if gr is None:
        def gradient(x):
            return _grad(objective, x)
    else:
        if not callable(gr):
            raise PracmaError("Argument function 'fun' not known in parent environment.")

        def gradient(x):
            return gr(x, *args, **kwargs)

    return _varmetric(point, objective, gradient, tol=tol, maxiter=maxiter, maxfeval=maxfeval)
