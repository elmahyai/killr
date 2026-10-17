"""Univariate root finders from pracma."""

from __future__ import annotations

import cmath
import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.opt_helpers import _EPS, _fderiv, _horner, _hornerdefl, _is_numeric, _scalar, _warn


def _bind(fun, args, kwargs):
    if not callable(fun):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def wrapped(x):
        return fun(x, *args, **kwargs)

    return wrapped


def bisect(fun, a, b, maxiter=500, tol=None, *args, **kwargs):
    f = _bind(fun, args, kwargs)
    if tol is not None and not (isinstance(tol, float) and math.isnan(tol)):
        _warn("Deprecated: Argument 'tol' not used anymore.")
    fa = _scalar(f(a))
    fb = _scalar(f(b))
    if fa * fb > 0:
        raise PracmaError("f(a) and f(b) must have different signs.")
    x1 = min(float(a), float(b))
    x2 = max(float(a), float(b))
    xm = (x1 + x2) / 2.0
    n = 1
    while x1 < xm and xm < x2 and n < maxiter:
        n += 1
        if np.sign(x1) != np.sign(x2) and x1 != 0 and x2 != 0:
            xm = 0.0
            if _scalar(f(xm)) == 0.0:
                x1 = x2 = xm
                break
        if np.sign(_scalar(f(x1))) != np.sign(_scalar(f(xm))):
            x2 = xm
        else:
            x1 = xm
        xm = (x1 + x2) / 2.0
    return {"root": xm, "f.root": _scalar(f(xm)), "iter": n, "estim.prec": abs(x1 - x2)}


def secant(fun, a, b, maxiter=500, tol=1e-08, *args, **kwargs):
    f = _bind(fun, args, kwargs)
    x1 = float(a)
    x2 = float(b)
    f1 = _scalar(f(x1))
    if abs(f1) <= tol:
        return x1
    f2 = _scalar(f(x2))
    if abs(f2) <= tol:
        return x1
    n = 0
    x3 = f3 = None
    while n <= maxiter and abs(x2 - x1) > tol:
        n += 1
        slope = (f2 - f1) / (x2 - x1)
        if slope == 0:
            raise PracmaError("multi-argument returns are not permitted")
        x3 = x2 - f2 / slope
        f3 = _scalar(f(x3))
        if abs(f3) <= tol:
            break
        x1, f1 = x2, f2
        x2, f2 = x3, f3
    if n > maxiter:
        _warn("Maximum number of iterations 'maxiter' was reached.")
    return {"root": x3, "f.root": f3, "iter": n, "estim.prec": 2 * abs(x3 - x2)}


def regulaFalsi(fun, a, b, maxiter=500, tol=1e-08, *args, **kwargs):
    f = _bind(fun, args, kwargs)
    x1 = float(a)
    x2 = float(b)
    f1 = _scalar(f(x1))
    f2 = _scalar(f(x2))
    if f1 * f2 > 0:
        raise PracmaError("f(a) and f(b) must have different signs.")
    m = 0.5
    niter = 0
    x3 = f3 = None
    while abs(x2 - x1) >= tol and niter <= maxiter:
        niter += 1
        x3 = (x1 * f2 - x2 * f1) / (f2 - f1)
        f3 = _scalar(f(x3))
        if f3 * f2 < 0:
            x1, f1 = x2, f2
            x2, f2 = x3, f3
        else:
            f1 = m * f1
            x2, f2 = x3, f3
    if niter > maxiter and abs(x2 - x1) >= tol:
        print("regulaFalsi stopped without converging.")
    return {"root": x3, "f.root": f3, "niter": niter, "estim.prec": x1 - x2}


def ridders(fun, a, b, maxiter=500, tol=1e-12, *args, **kwargs):
    f = _bind(fun, args, kwargs)
    x1 = float(a)
    x2 = float(b)
    f1 = _scalar(f(x1))
    f2 = _scalar(f(x2))
    if f1 * f2 >= 0:
        raise PracmaError("f(a) and f(b) must have different signs.")
    niter = 2
    while abs(x1 - x2) > tol and niter < maxiter:
        xm = (x1 + x2) / 2
        fm = _scalar(f(xm))
        if fm == 0:
            return {"root": xm, "f.root": 0, "niter": niter, "estim.prec": 0}
        x3 = xm + (xm - x1) * np.sign(f1 - f2) * fm / math.sqrt(fm**2 - f1 * f2)
        f3 = _scalar(f(x3))
        niter += 2
        if f3 == 0:
            return {"root": x3, "f.root": 0, "niter": niter, "estim.prec": 0}
        if fm * f3 < 0:
            x1, f1 = xm, fm
            x2, f2 = x3, f3
        elif f1 * f3 < 0:
            x2, f2 = x3, f3
        elif f2 * f3 < 0:
            x1, f1 = x3, f3
        else:
            raise PracmaError("Inform the maintainer: you should never get here.")
    if abs(f1) < abs(f2):
        x0, f0 = x1, f1
    else:
        x0, f0 = x2, f2
    return {"root": x0, "f.root": f0, "niter": niter, "estim.prec": abs(x1 - x2)}


def brentDekker(fun, a, b, maxiter=500, tol=1e-12, *args, **kwargs):
    f = _bind(fun, args, kwargs)
    if not _is_numeric(a) or not _is_numeric(b) or np.asarray(a).size != 1 or np.asarray(b).size != 1:
        raise PracmaError("is.numeric(a) is not TRUE")
    a = float(np.asarray(a).reshape(-1)[0])
    b = float(np.asarray(b).reshape(-1)[0])
    x1, f1 = a, _scalar(f(a))
    if f1 == 0:
        return {"root": a, "f.root": 0, "f.calls": 1, "estim.prec": 0}
    x2, f2 = b, _scalar(f(b))
    if f2 == 0:
        return {"root": b, "f.root": 0, "f.calls": 1, "estim.prec": 0}
    if f1 * f2 > 0.0:
        raise PracmaError("Brent-Dekker: Root is not bracketed in [a, b].")
    x3 = 0.5 * (a + b)
    x0 = x3
    niter = 1
    while niter <= maxiter:
        f3 = _scalar(f(x3))
        if abs(f3) < tol:
            x0 = x3
            break
        if f1 * f3 < 0.0:
            b = x3
        else:
            a = x3
        if (b - a) < tol * max(abs(b), 1.0):
            x0 = 0.5 * (a + b)
            break
        denom = (f2 - f1) * (f3 - f1) * (f2 - f3)
        numer = x3 * (f1 - f2) * (f2 - f3 + f1) + f2 * x1 * (f2 - f3) + f1 * x2 * (f3 - f1)
        dx = b - a if denom == 0 else f3 * numer / denom
        x = x3 + dx
        if (b - x) * (x - a) < 0.0:
            dx = 0.5 * (b - a)
            x = a + dx
        if x1 < x3:
            x2, f2 = x3, f3
        else:
            x1, f1 = x3, f3
        niter += 1
        if abs(x - x3) < tol:
            x0 = x
            break
        x3 = x
    if niter > maxiter:
        _warn("Maximum numer of iterations, 'maxiter', has been reached.")
    prec = min(abs(x1 - x3), abs(x2 - x3))
    return {"root": x0, "f.root": _scalar(f(x0)), "f.calls": niter + 2, "estim.prec": prec}


brent = brentDekker


def muller(f, p0, p1, p2=None, maxiter=100, tol=1e-10):
    if p2 is None:
        p2 = (p0 + p1) / 2
    for name, value in (("p0", p0), ("p1", p1), ("p2", p2)):
        array = np.asarray(value)
        if array.size != 1 or not (_is_numeric(value) or np.iscomplexobj(array) or isinstance(value, complex)):
            raise PracmaError(f"is.numeric({name}) || is.complex({name}) is not TRUE")
    if not callable(f):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def value_at(point):
        raw = f(point)
        number = np.asarray(raw).reshape(-1)[0]
        return complex(number)

    p0, p1, p2 = complex(p0), complex(p1), complex(p2)
    fp0, fp1, fp2 = value_at(p0), value_at(p1), value_at(p2)
    if not (cmath.isfinite(fp0) and cmath.isfinite(fp1) and cmath.isfinite(fp2)):
        raise PracmaError("Function 'f' not finite at one of the initial points.")
    h1 = p1 - p0
    h2 = p2 - p1
    d1 = (fp1 - fp0) / h1
    d2 = (fp2 - fp1) / h2
    d = (d2 - d1) / (h2 + h1)
    i = 3
    h = p = fp = 0j
    while i <= maxiter:
        b = d2 + h2 * d
        disc = b**2 - 4 * value_at(p2) * d + 0j
        capital = cmath.sqrt(disc)
        e = b + capital if abs(b - capital) < abs(b + capital) else b - capital
        h = -2 * value_at(p2) / e
        p = p2 + h
        fp = value_at(p)
        if abs(h) < tol:
            break
        p0, p1, p2 = p1, p2, p
        h1 = p1 - p0
        h2 = p2 - p1
        d1 = (value_at(p1) - value_at(p0)) / h1
        d2 = (value_at(p2) - value_at(p1)) / h2
        d = (d2 - d1) / (h2 + h1)
        i += 1
    if i > maxiter:
        _warn("Root not found to the desired tolerance.")
    if abs(p.imag) <= 0.1 * tol:
        p = p.real
        fp = _scalar(f(p))
    return {"root": p, "fval": fp, "niter": i, "reltol": abs(h)}


def _zeroin(f, a, b, maxiter=100, tol=1e-07):
    if not _is_numeric(a) or not _is_numeric(b) or np.size(a) != 1 or np.size(b) != 1:
        raise PracmaError("is.numeric(a) is not TRUE")
    a = float(a)
    b = float(b)
    mu = 0.5
    eps = _EPS
    info = 0
    if a > b:
        a, b = b, a
    fa = _scalar(f(a))
    fb = _scalar(f(b))
    if np.sign(fa) * np.sign(fb) > 0:
        raise PracmaError("Function must differ in sign at interval endpoints.")
    itype = 1
    if abs(fa) < abs(fb):
        u, fu = a, fa
    else:
        u, fu = b, fb
    d = e = u
    fd = fe = fu
    mba = mu * (b - a)
    niter = 0
    c = u
    while niter < maxiter:
        if itype == 1:
            if (b - a) <= 2 * (2 * abs(u) * eps + tol):
                info = 1
                break
            if abs(fa) <= 1e3 * abs(fb) and abs(fb) <= 1e3 * abs(fa):
                c = u - (a - b) / (fa - fb) * fu
            else:
                c = 0.5 * (a + b)
            d, fd = u, fu
            itype = 5
        elif itype == 2 or itype == 3:
            values = [fa, fb, fd, fe]
            distinct = len({float(v) for v in values})
            if distinct == 4:
                q11 = (d - e) * fd / (fe - fd)
                q21 = (b - d) * fb / (fd - fb)
                q31 = (a - b) * fa / (fb - fa)
                d21 = (b - d) * fd / (fd - fb)
                d31 = (a - b) * fb / (fb - fa)
                q22 = (d21 - q11) * fb / (fe - fb)
                q32 = (d31 - q21) * fa / (fd - fa)
                d32 = (d31 - q21) * fd / (fd - fa)
                q33 = (d32 - q22) * fa / (fe - fa)
                c = a + q31 + q32 + q33
            if distinct < 4 or np.sign(c - a) * np.sign(c - b) > 0:
                a0 = fa
                a1 = (fb - fa) / (b - a)
                a2 = ((fd - fb) / (d - b) - a1) / (d - a)
                c = a - a0 / a1
                if a2 != 0:
                    c = a - a0 / a1
                    for _ in range(itype):
                        pc = a0 + (a1 + a2 * (c - b)) * (c - a)
                        pdc = a1 + a2 * (2 * c - a - b)
                        if pdc == 0:
                            c = a - a0 / a1
                            break
                        c = c - pc / pdc
            itype += 1
        elif itype == 4:
            c = u - 2 * (b - a) / (fb - fa) * fu
            if abs(c - u) > 0.5 * (b - a):
                c = 0.5 * (b + a)
            itype = 5
        elif itype == 5:
            c = 0.5 * (b + a)
            itype = 2
        delta = 2 * 0.7 * (2 * abs(u) * eps + tol)
        if (b - a) <= 2 * delta:
            c = (a + b) / 2
        else:
            c = max(a + delta, min(b - delta, c))
        fc = _scalar(f(c))
        niter += 1
        if np.sign(fc - fa) * np.sign(fc - fb) >= 0:
            fe = fc
        else:
            e, fe = d, fd
        if np.sign(fa) * np.sign(fc) < 0:
            d, fd = b, fb
            b, fb = c, fc
        elif np.sign(fb) * np.sign(fc) < 0:
            d, fd = a, fa
            a, fa = c, fc
        elif fc == 0:
            a = b = c
            fa = fb = fc
            info = 1
            break
        else:
            raise PracmaError("zeroin: zero point could not be bracketed")
        if abs(fa) < abs(fb):
            u, fu = a, fa
        else:
            u, fu = b, fb
        if b - a <= 2 * (2 * abs(u) * eps + tol):
            info = 1
            break
        if itype == 5 and (b - a) <= mba:
            itype = 2
        if itype == 2:
            mba = mu * (b - a)
    return {"bra": np.array([a, b]), "ket": np.array([fa, fb]), "niter": niter, "info": info}


def fzero(fun, x, maxiter=500, tol=1e-12, *args, **kwargs):
    values = np.asarray(x, dtype=float).reshape(-1) if _is_numeric(x) else np.asarray(x)
    if not _is_numeric(x) or values.size > 2:
        raise PracmaError("Argument 'x' must be a scalar or a vector of length 2.")
    f = _bind(fun, args, kwargs)
    if values.size == 2:
        a, b = float(values[0]), float(values[1])
        if a > b:
            _warn("Left endpoint bigger than right one: exchanged points.")
            a, b = b, a
        zin = _zeroin(f, a, b, maxiter=maxiter, tol=tol)
    else:
        a = float(values[0])
        fa = _scalar(f(a))
        if fa == 0:
            return {"x": a, "fval": fa}
        aa = 1.0 if a == 0 else a
        zin = None
        for b in (0.9 * aa, 1.1 * aa, aa - 1, aa + 1, 0.5 * aa, 1.5 * aa, -aa, 2 * aa, -10 * aa, 10 * aa):
            fb = _scalar(f(b))
            if fb == 0:
                return {"x": b, "fval": fb}
            if np.sign(fa) * np.sign(fb) < 0:
                zin = _zeroin(f, a, b, maxiter=maxiter, tol=tol)
                break
    if zin is None:
        _warn("No interval w/ function 'f' changing sign was found.")
        return {"x": np.nan, "fval": np.nan}
    x1, x2 = float(zin["bra"][0]), float(zin["bra"][1])
    f1, f2 = float(zin["ket"][0]), float(zin["ket"][1])
    x0 = (x1 + x2) / 2
    f0 = _scalar(f(x0))
    if f0 < f1 and f0 < f2:
        return {"x": x0, "fval": f0}
    if f1 <= f2:
        return {"x": x1, "fval": f1}
    return {"x": x2, "fval": f2}


def newtonRaphson(fun, x0, dfun=None, maxiter=500, tol=1e-08, *args, **kwargs):
    if not callable(fun):
        raise PracmaError("is.function(fun) is not TRUE")
    if dfun is None:

        def dfun(x, *a, **k):
            h = tol ** (2.0 / 3.0)
            return (fun(x + h, *a, **k) - fun(x - h, *a, **k)) / (2 * h)

    x = x0
    fx = _scalar(fun(x, *args, **kwargs))
    dfx = _scalar(dfun(x, *args, **kwargs))
    niter = 0
    diff = tol + 1
    while diff >= tol and niter <= maxiter:
        niter += 1
        if dfx == 0:
            _warn("Slope is zero: no further improvement possible.")
            break
        diff = -fx / dfx
        x = x + diff
        diff = abs(diff)
        fx = _scalar(fun(x, *args, **kwargs))
        dfx = _scalar(dfun(x, *args, **kwargs))
    if niter > maxiter:
        _warn("Maximum number of iterations 'maxiter' was reached.")
    return {"root": x, "f.root": fx, "niter": niter, "estim.prec": diff}


newton = newtonRaphson


def halley(fun, x0, maxiter=500, tol=1e-08, *args, **kwargs):
    f = _bind(fun, args, kwargs)
    x0 = float(np.asarray(x0).reshape(-1)[0])
    f0 = _scalar(f(x0))
    if abs(f0) < tol ** (1.5):
        return {"root": x0, "f.root": f0, "maxiter": 0, "estim.prec": 0}
    f1 = _fderiv(f, x0, 1)
    f2 = _fderiv(f, x0, 2)
    x1 = x0 - 2 * f0 * f1 / (2 * f1**2 - f0 * f2)
    niter = 1
    while abs(x1 - x0) > tol and niter < maxiter:
        x0 = x1
        f0 = _scalar(f(x0))
        f1 = _fderiv(f, x0, 1)
        f2 = _fderiv(f, x0, 2)
        x1 = x0 - 2 * f0 * f1 / (2 * f1**2 - f0 * f2)
        niter += 1
    return {"root": x1, "f.root": _scalar(f(x1)), "iter": niter, "estim.prec": abs(x1 - x0)}


def newtonHorner(p, x0, maxiter=50, tol=_EPS**0.5):
    coeff = as_1d(p)
    x = float(np.asarray(x0).reshape(-1)[0])
    niter = 0
    diff = 1 + tol
    while niter <= maxiter and diff >= tol:
        h = _horner(coeff, x)
        if abs(float(np.asarray(h["dy"]).reshape(-1)[0])) <= tol:
            _warn("Newton's method encountered a slope almost zero.")
            return {
                "root": None,
                "f.root": None,
                "deflate": None,
                "iters": niter,
                "estim.prec": np.inf,
            }
        xnew = x - float(np.asarray(h["y"]).reshape(-1)[0]) / float(np.asarray(h["dy"]).reshape(-1)[0])
        diff = abs(x - xnew)
        niter += 1
        x = xnew
    if niter > maxiter:
        _warn("Maximum number of iterations exceeded.")
    defl = _hornerdefl(coeff, x)
    return {
        "root": x,
        "f.root": defl["y"],
        "deflate": defl["q"],
        "iters": niter,
        "estim.prec": diff,
    }
