"""Nonlinear systems and nonlinear least squares from pracma."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.arrays import Norm
from pracma.opt_helpers import (
    _EPS,
    _frobenius,
    _inv,
    _is_complex,
    _is_numeric,
    _jacobian,
    _mdhess,
    _scalar,
    _vector_value,
    _warn,
)
from pracma.opt_metric import softline


def broyden(Ffun, x0, J0=None, *args, maxiter=100, tol=_EPS**0.5, **kwargs):
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric (row or column) vector.")
    if not callable(Ffun):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def F(x):
        return _vector_value(lambda z: Ffun(z, *args, **kwargs), x)

    point = as_1d(x0)
    y0 = F(point)
    if point.size != y0.size:
        raise PracmaError("Function 'F' must be 'square', i.e. from R^n to R^n .")
    if point.size == 1:
        raise PracmaError("Function 'F' must not be a univariate function.")
    A0 = _jacobian(F, point) if J0 is None else np.asarray(J0, dtype=float)
    B0 = _inv(A0)
    if np.any(np.isinf(B0)):
        B0 = np.eye(point.size)
    x_prev = point
    y_prev = y0
    xnew = (x_prev.reshape(-1, 1) - B0 @ y_prev.reshape(-1, 1)).reshape(-1)
    ynew = F(xnew)
    k = 1
    while k < maxiter:
        s = (xnew - x_prev).reshape(-1, 1)
        d = (ynew - y_prev).reshape(-1, 1)
        if _frobenius(s) < tol or _frobenius(ynew) < tol:
            break
        denom = float(np.asarray(s.T @ B0 @ d).reshape(-1)[0])
        B0 = B0 + ((s - B0 @ d) @ (s.T @ B0)) / denom
        x_prev = xnew
        xnew = (xnew.reshape(-1, 1) - B0 @ ynew.reshape(-1, 1)).reshape(-1)
        y_prev = ynew
        ynew = F(xnew)
        k += 1
    if k >= maxiter:
        _warn("Not converged: Max number of iterations reached.")
    return {"zero": xnew.copy(), "fnorm": math.sqrt(float(np.sum(ynew**2))), "niter": k}


def gaussNewton(x0, Ffun, Jfun=None, maxiter=100, tol=_EPS**0.5, *args, **kwargs):
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    point = as_1d(x0)
    n = point.size
    if n == 1:
        raise PracmaError("Function is univariate -- use a different approach.")
    if not callable(Ffun):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def F(x):
        return _vector_value(lambda z: Ffun(z, *args, **kwargs), x)

    if Jfun is None:
        def J(x):
            return _jacobian(F, x)
    else:
        if not callable(Jfun):
            raise PracmaError("Argument function 'fun' not known in parent environment.")

        def J(x):
            return np.asarray(Jfun(x, *args, **kwargs), dtype=float)

    def objective(x):
        return float(np.sum(F(x) ** 2))

    def gradient(x):
        return (2.0 * J(x).T @ F(x).reshape(-1, 1)).reshape(-1)

    xk = point.copy()
    fk = objective(xk)
    Jk = J(xk)
    gk = gradient(xk)
    Hk = 2.0 * Jk.T @ Jk + tol * np.eye(n)
    dk = (-_inv(Hk) @ gk.reshape(-1, 1)).reshape(-1)
    if not np.all(np.isfinite(dk)):
        dk = _mdhess(Hk, gk)
    ak = softline(xk, dk, objective, gradient)
    adk = ak * dk
    err = Norm(adk)
    k = 1
    while err > tol and k < maxiter:
        xk = xk + adk
        fl = objective(xk)
        Jk = J(xk)
        gk = gradient(xk)
        Hk = 2.0 * Jk.T @ Jk + tol * np.eye(n)
        dk = (-_inv(Hk) @ gk.reshape(-1, 1)).reshape(-1)
        if not np.all(np.isfinite(dk)):
            dk = _mdhess(Hk, gk)
        ak = softline(xk, dk, objective, gradient)
        adk = ak * dk
        err = abs(fl - fk)
        fk = fl
        k += 1
    if k >= maxiter:
        _warn("Maximum number of iterations reached -- no convergence.")
    xs = xk + adk
    return {"xs": xs, "fs": objective(xs), "niter": k, "relerr": err}


def fsolve(f, x0, J=None, maxiter=100, tol=_EPS**0.5, *args, **kwargs):
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    point = as_1d(x0)
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def residual(x):
        return _vector_value(lambda z: f(z, *args, **kwargs), x)

    n = point.size
    m = residual(point).size
    if n == 1:
        raise PracmaError("Function 'fsolve' not applicable for univariate root finding.")
    if J is not None:
        if not callable(J):
            raise PracmaError("Argument function 'fun' not known in parent environment.")

        def jacobian_at(x):
            return np.asarray(J(x, *args, **kwargs), dtype=float)
    else:
        def jacobian_at(x):
            return _jacobian(residual, x)

    if m == n:
        sol = broyden(residual, point, J0=jacobian_at(point), maxiter=maxiter, tol=tol)
        xs = sol["zero"]
        fs = residual(xs)
    else:
        sol = gaussNewton(point, residual, Jfun=jacobian_at, maxiter=maxiter, tol=tol)
        xs = sol["xs"]
        fs = sol["fs"]
        if fs > tol:
            _warn("Minimum appears not to be a zero -- change starting point.")
    return {"x": xs, "fval": fs}


def fzsolve(fz, z0):
    values = np.asarray(z0)
    if values.size == 0:
        return None
    if values.size > 1:
        _warn("Argument 'z0' has length > 1, first component taken.")
        z0 = values.reshape(-1)[0]
    if _is_numeric(z0):
        x0 = np.array([float(np.asarray(z0).reshape(-1)[0]), 0.0])
    elif _is_complex(z0) or isinstance(z0, complex):
        number = complex(np.asarray(z0).reshape(-1)[0])
        x0 = np.array([number.real, number.imag])
    else:
        raise PracmaError("Argument 'z0' must be a real or complex number.")
    if not callable(fz):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def fn(x):
        z = x[0] + x[1] * 1j
        Z = fz(z)
        if isinstance(Z, complex) or np.iscomplexobj(np.asarray(Z)):
            number = complex(np.asarray(Z).reshape(-1)[0])
            return np.array([number.real, number.imag])
        if _is_numeric(Z):
            return np.array([float(np.asarray(Z).reshape(-1)[0]), 0.0])
        return np.array([np.nan, np.nan])

    x = broyden(fn, x0)["zero"]
    return complex(x[0], x[1])


def _lsq_options(options):
    opts = {"tau": 1e-3, "tolx": 1e-8, "tolg": 1e-8, "maxeval": 700}
    if not options:
        return opts
    names = list(options.keys())
    chosen = []
    for name in names:
        hits = [key for key in opts if key.startswith(str(name))]
        if len(hits) != 1:
            quoted = ", ".join("\u201c" + key + "\u201d" for key in opts)
            raise PracmaError(f"'{name}' should be one of {quoted}")
        chosen.append(hits[0])
    for key, value in zip(chosen, options.values()):
        opts[key] = value
    return opts


def lsqnonlin(fun, x0, options=None, *args, **kwargs):
    if not _is_numeric(x0):
        raise PracmaError("is.numeric(x0) is not TRUE")
    if options is None:
        options = {}
    opts = _lsq_options(options)
    tau = opts["tau"]
    tolx = opts["tolx"]
    tolg = opts["tolg"]
    maxeval = opts["maxeval"]
    if not callable(fun):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def residual(x):
        return _vector_value(lambda z: fun(z, *args, **kwargs), x)

    x = as_1d(x0)
    n = x.size
    r = residual(x)
    f = 0.5 * float(np.sum(r**2))
    J = _jacobian(residual, x)
    g = (J.T @ r.reshape(-1, 1)).reshape(-1)
    ng = Norm(g, np.inf)
    A = J.T @ J
    mu = tau * float(np.max(np.diag(A)))
    nu = 2.0
    nh = 0.0
    errno = 0
    k = 1
    xnew = x.copy()
    while k < maxeval:
        k += 1
        step = np.linalg.solve(A + mu * np.eye(n), -g)
        h = step.reshape(-1)
        nh = Norm(h)
        nx = tolx + Norm(x)
        if nh <= tolx * nx:
            errno = 1
            break
        xnew = x + h
        h = xnew - x
        dL = float(np.sum(h * (mu * h - g))) / 2
        rn = residual(xnew)
        fn = 0.5 * float(np.sum(rn**2))
        Jn = _jacobian(residual, xnew)
        if rn.size != r.size:
            df = f - fn
        else:
            df = float(np.sum((r - rn) * (r + rn))) / 2
        if dL > 0 and df > 0:
            x = xnew
            f = fn
            J = Jn
            r = rn
            A = J.T @ J
            g = (J.T @ r.reshape(-1, 1)).reshape(-1)
            ng = Norm(g, np.inf)
            ratio = 2 * df / dL - 1
            mu = mu * max(1.0 / 3.0, 1 - ratio**3)
            nu = 2.0
        else:
            mu = mu * nu
            nu = 2 * nu
        if ng <= tolg:
            errno = 2
            break
    if k >= maxeval:
        errno = 3
    messages = {
        1: "Stopped by small x-step.",
        2: "Stopped by small gradient.",
        3: "No. of function evaluations exceeded.",
    }
    return {
        "x": np.array(xnew, dtype=float, copy=True),
        "ssq": float(np.sum(residual(xnew) ** 2)),
        "ng": ng,
        "nh": nh,
        "mu": mu,
        "neval": k,
        "errno": errno,
        "errmess": messages.get(errno),
    }


def lsqcurvefit(fun, p0, xdata, ydata):
    if not callable(fun):
        raise PracmaError("is.function(fun) is not TRUE")
    if not _is_numeric(p0) or not _is_numeric(xdata) or not _is_numeric(ydata):
        raise PracmaError("is.numeric(p0) is not TRUE")
    xdata = as_1d(xdata)
    ydata = as_1d(ydata)
    if xdata.size != ydata.size:
        raise PracmaError("Aguments 'xdata', 'ydata' must have the same length.")

    def fn(p, _x=None):
        return np.asarray(fun(p, xdata), dtype=float).reshape(-1) - ydata

    return lsqnonlin(fn, p0)
