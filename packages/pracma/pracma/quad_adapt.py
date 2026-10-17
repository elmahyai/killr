"""Adaptive Simpson, Lobatto, vectorized Simpson, and Gauss-Richardson."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError

_EPS = float(np.finfo(float).eps)


def quad(f, xa, xb, tol=None, trace=False, **kwargs):
    xa = _finite_scalar(xa, "xa")
    xb = _finite_scalar(xb, "xb")
    if tol is None:
        tol = _EPS ** 0.5
    fun = _callable(f)

    def wrapped(x):
        return fun(x, **kwargs)

    if xa == xb:
        return np.float64(xb - xa)
    reverse = False
    if xa > xb:
        xa, xb = xb, xa
        reverse = True
    if not math.isfinite(_one(wrapped(xa))):
        xa = xa + 2.0 * _EPS
    if not math.isfinite(_one(wrapped(xb))):
        xb = xb - 2.0 * _EPS
    total = _adaptsim(wrapped, xa, xb, float(tol), trace)
    if reverse:
        total = -total
    return np.float64(total)


def quadl(f, xa, xb, tol=None, trace=False, **kwargs):
    xa = _finite_scalar(xa, "xa")
    xb = _finite_scalar(xb, "xb")
    if tol is None:
        tol = _EPS ** 0.5
    fun = _callable(f)

    def wrapped(x):
        return fun(x, **kwargs)

    if xa == xb:
        return np.float64(xb - xa)
    reverse = False
    if xa > xb:
        xa, xb = xb, xa
        reverse = True
    if not math.isfinite(_one(wrapped(xa))):
        xa = xa + 2.0 * _EPS
    if not math.isfinite(_one(wrapped(xb))):
        xb = xb - 2.0 * _EPS
    total = _adaptlob(wrapped, xa, xb, float(tol), trace)
    if reverse:
        total = -total
    return np.float64(total)


def quadv(f, a, b, tol=None, **kwargs):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    if tol is None:
        tol = _EPS ** 0.5
    tol = float(tol)
    if a > b:
        raise PracmaError("Interval boundaries must satisfy 'a <= b'.")
    if a == b:
        return {"Q": np.array([0.0]), "fcnt": 0, "estim.prec": np.float64(0.0)}
    fun = _callable(f)

    def wrapped(x):
        return np.asarray(fun(x, **kwargs), dtype=float).reshape(-1)

    h = 0.13579 * (b - a)
    x = np.array(
        [a, a + h, a + 2.0 * h, (a + b) / 2.0, b - 2.0 * h, b - h, b],
        dtype=float,
    )
    rows = [wrapped(x[j]) for j in range(7)]
    y = np.vstack(rows)
    fcnt = 7
    if not np.all(np.isfinite(y[0, :])):
        y[0, :] = wrapped(a + _EPS * (b - a))
        fcnt += 1
    if not np.all(np.isfinite(y[6, :])):
        y[6, :] = wrapped(b - _EPS * (b - a))
        fcnt += 1
    hmin = _EPS * (b - a) / 1024.0
    q1, fcnt = _quadvstep(wrapped, x[0], x[2], y[0, :], y[1, :], y[2, :], tol, fcnt, hmin)
    q2, fcnt = _quadvstep(wrapped, x[2], x[4], y[2, :], y[3, :], y[4, :], tol, fcnt, hmin)
    q3, fcnt = _quadvstep(wrapped, x[4], x[6], y[4, :], y[5, :], y[6, :], tol, fcnt, hmin)
    return {
        "Q": np.asarray(q1 + q2 + q3, dtype=float).reshape(-1),
        "fcnt": int(fcnt),
        "estim.prec": np.float64(tol * (fcnt - 7) / 2.0),
    }


def quadgr(f, a, b, tol=None, **kwargs):
    a = _scalar(a, "a")
    b = _scalar(b, "b")
    if tol is None:
        tol = _EPS ** 0.5
    tol = float(tol)
    fun = _callable(f)

    def wrapped(x):
        return fun(x, **kwargs)

    left = np.asarray(wrapped(a), dtype=float).reshape(-1)
    right = np.asarray(wrapped(b), dtype=float).reshape(-1)
    if left.size != 1 or right.size != 1:
        raise PracmaError("Function 'f' may be multi-valued; please check.")
    pair = np.asarray(wrapped(np.array([a, b], dtype=float)), dtype=float).reshape(-1)
    if pair.size != 2:
        raise PracmaError("Function 'f' needs to be vectorized (see 'Vectorize').")
    if a == b:
        return {"value": np.float64(0.0), "rel.err": np.float64(0.0)}
    reverse = False
    if a > b:
        a, b = b, a
        reverse = True
    if math.isinf(a) or math.isinf(b):
        result = _quadgr_infinite(wrapped, a, b, tol)
        if reverse:
            result["value"] = np.float64(-result["value"])
        return result

    positive = np.array(
        [
            0.12523340851146894,
            0.36783149899818018,
            0.58731795428661748,
            0.76990267419430469,
            0.9041172563704748,
            0.98156063424671924,
        ]
    )
    weights = np.array(
        [
            0.24914704581340288,
            0.23349253653835478,
            0.20316742672306584,
            0.16007832854334636,
            0.10693932599531818,
            0.047175336386511842,
        ]
    )
    nodes = np.concatenate([positive, -positive])
    weights = np.concatenate([weights, weights])
    maxit = 17
    q0 = np.zeros(maxit + 1)
    q1 = np.zeros(maxit + 1)
    q2 = np.zeros(maxit + 1)
    hh = (b - a) / 2.0
    x = (a + b) / 2.0 + hh * nodes
    q0[1] = float(np.dot(hh * weights, np.asarray(fun(x), dtype=float).reshape(-1)))
    err = np.float64(np.nan)
    value = np.float64(np.nan)
    for k in range(3, maxit + 1):
        hh = hh / 2.0
        x = np.column_stack([np.asarray(x, dtype=float) + a, np.asarray(x, dtype=float) + b]) / 2.0
        samples = np.array([np.sum(np.asarray(wrapped(x[i, :]), dtype=float)) for i in range(12)])
        q0[k] = float(np.dot(hh * weights, samples))
        if k >= 5:
            q1[k] = _rich(q0, k)
            q2[k] = _rich(q1, k)
        elif k >= 3:
            q1[k] = _rich(q0, k)
        if k >= 6:
            current = np.array([q0[k], q1[k], q2[k]])
            previous = np.array([q0[k - 1], q1[k - 1], q2[k - 1]])
        elif k >= 4:
            current = np.array([q0[k], q1[k]])
            previous = np.array([q0[k - 1], q1[k - 1]])
        else:
            current = np.array([q0[k]])
            previous = np.array([q0[k - 1]])
        gaps = np.abs(current - previous)
        err = float(np.min(gaps))
        value = float(current[int(np.argmin(gaps))])
        if err < tol or not math.isfinite(value):
            break
    if reverse:
        value = -value
    return {"value": np.float64(value), "rel.err": np.float64(err)}


def _quadgr_infinite(wrapped, a, b, tol):
    if math.isfinite(a) and math.isinf(b):

        def mapped(t, origin=a):
            return wrapped(origin + t / (1.0 - t)) / (1.0 - t) ** 2

        return quadgr(mapped, 0.0, 1.0, tol=tol)
    if math.isinf(a) and math.isfinite(b):

        def mapped(t, origin=b):
            return wrapped(origin + t / (1.0 + t)) / (1.0 + t) ** 2

        return quadgr(mapped, -1.0, 0.0, tol=tol)
    def right(t):
        return wrapped(t / (1.0 - t)) / (1.0 - t) ** 2

    def left(t):
        return wrapped(t / (1.0 + t)) / (1.0 + t) ** 2

    first = quadgr(right, 0.0, 1.0, tol=tol / 2.0)
    second = quadgr(left, -1.0, 0.0, tol=tol / 2.0)
    return {
        "value": np.float64(first["value"] + second["value"]),
        "rel.err": np.float64(first["rel.err"] + second["rel.err"]),
    }


def _rich(q, k):
    if q[k] != q[k - 1]:
        cc = (q[k - 1] - q[k - 2]) / (q[k] - q[k - 1]) - 1.0
    else:
        cc = 1.0
    cc = max(cc, 0.07)
    return q[k] + (q[k] - q[k - 1]) / cc


def _adaptsim(f, xa, xb, tol, trace):
    y = np.array([_one(f(xa)), _one(f((xa + xb) / 2.0)), _one(f(xb))])
    probes = xa + np.array([0.9501, 0.2311, 0.6068, 0.4860, 0.8913]) * (xb - xa)
    yy = np.array([_one(f(value)) for value in probes])
    ab = (xb - xa) / 8.0 * (np.sum(y) + np.sum(yy))
    if ab == 0.0:
        ab = xb - xa
    ab = ab * tol / _EPS
    return _adaptsimstp(f, xa, xb, y[0], y[1], y[2], ab, trace)


def _adaptsimstp(f, xa, xb, fa, fm, fb, ab, trace):
    m = (xa + xb) / 2.0
    h = (xb - xa) / 4.0
    fml = _one(f(xa + h))
    fmr = _one(f(xb - h))
    i1 = h / 1.5 * (fa + 4.0 * fm + fb)
    i2 = h / 3.0 * (fa + 4.0 * (fml + fmr) + 2.0 * fm + fb)
    i1 = (16.0 * i2 - i1) / 15.0
    if (ab + (i1 - i2) == ab) or (m <= xa) or (xb <= m):
        if trace:
            print(xa, xb - xa, i1)
        return i1
    return _adaptsimstp(f, xa, m, fa, fml, fm, ab, trace) + _adaptsimstp(
        f, m, xb, fm, fmr, fb, ab, trace
    )


def _adaptlob(f, a, b, tol, trace):
    m = (a + b) / 2.0
    h = (b - a) / 2.0
    alpha = math.sqrt(2.0 / 3.0)
    beta = 1.0 / math.sqrt(5.0)
    x1 = 0.942882415695480
    x2 = 0.641853342345781
    x3 = 0.236383199662150
    x = np.array(
        [
            a,
            m - x1 * h,
            m - alpha * h,
            m - x2 * h,
            m - beta * h,
            m - x3 * h,
            m,
            m + x3 * h,
            m + beta * h,
            m + x2 * h,
            m + alpha * h,
            m + x1 * h,
            b,
        ]
    )
    y = np.array([_one(f(value)) for value in x])
    i2 = (h / 6.0) * (y[0] + y[12] + 5.0 * (y[4] + y[8]))
    i1 = (h / 1470.0) * (
        77.0 * (y[0] + y[12]) + 432.0 * (y[2] + y[10]) + 625.0 * (y[4] + y[8]) + 672.0 * y[6]
    )
    ab = h * (
        0.0158271919734802 * (y[0] + y[12])
        + 0.0942738402188500 * (y[1] + y[11])
        + 0.155071987336585 * (y[2] + y[10])
        + 0.188821573960182 * (y[3] + y[9])
        + 0.199773405226859 * (y[4] + y[8])
        + 0.224926465333340 * (y[5] + y[7])
        + 0.242611071901408 * y[6]
    )
    sign = math.copysign(1.0, ab) if ab != 0.0 else 1.0
    if ab == 0.0:
        sign = 1.0
    erri1 = abs(i1 - ab)
    erri2 = abs(i2 - ab)
    ratio = 1.0
    if erri2 != 0.0:
        ratio = erri1 / erri2
    if ratio > 0.0 and ratio < 1.0:
        tol = tol / ratio
    ab = sign * abs(ab) * tol / _EPS
    if ab == 0.0:
        ab = b - a
    return _adaptlobstp(f, a, b, y[0], y[12], ab, trace)


def _adaptlobstp(f, a, b, fa, fb, ab, trace):
    h = (b - a) / 2.0
    m = (a + b) / 2.0
    alpha = math.sqrt(2.0 / 3.0)
    beta = 1.0 / math.sqrt(5.0)
    mll = m - alpha * h
    ml = m - beta * h
    mr = m + beta * h
    mrr = m + alpha * h
    y = np.array([_one(f(mll)), _one(f(ml)), _one(f(m)), _one(f(mr)), _one(f(mrr))])
    i2 = (h / 6.0) * (fa + fb + 5.0 * (y[1] + y[3]))
    i1 = (h / 1470.0) * (
        77.0 * (fa + fb) + 432.0 * (y[0] + y[4]) + 625.0 * (y[1] + y[3]) + 672.0 * y[2]
    )
    if (ab + (i1 - i2) == ab) or (mll <= a) or (b <= mrr):
        if trace:
            print(a, b - a, i1)
        return i1
    return (
        _adaptlobstp(f, a, mll, fa, y[0], ab, trace)
        + _adaptlobstp(f, mll, ml, y[0], y[1], ab, trace)
        + _adaptlobstp(f, ml, m, y[1], y[2], ab, trace)
        + _adaptlobstp(f, m, mr, y[2], y[3], ab, trace)
        + _adaptlobstp(f, mr, mrr, y[3], y[4], ab, trace)
        + _adaptlobstp(f, mrr, b, y[4], fb, ab, trace)
    )


def _quadvstep(f, a, b, fa, fc, fb, tol, fcnt, hmin):
    maxfcnt = 10000
    h = b - a
    c = (a + b) / 2.0
    d = (a + c) / 2.0
    e = (c + b) / 2.0
    fd = f(d)
    fe = f(e)
    fcnt = fcnt + 2
    q1 = (h / 6.0) * (fa + 4.0 * fc + fb)
    q2 = (h / 12.0) * (fa + 4.0 * fd + 2.0 * fc + 4.0 * fe + fb)
    q = q2 + (q2 - q1) / 15.0
    if not np.all(np.isfinite(q)):
        raise PracmaError("Improper function values: infinite or NaN encountered.")
    if fcnt > maxfcnt:
        raise PracmaError("Maximum function count exceeded; singularity likely.")
    if abs(h) < hmin or c == a or c == b:
        raise PracmaError("Minimum step size reached; singularity possible.")
    if np.max(q2 - q) < tol:
        return q, fcnt
    qac, fcnt = _quadvstep(f, a, c, fa, fd, fc, tol, fcnt, hmin)
    qcb, fcnt = _quadvstep(f, c, b, fc, fe, fb, tol, fcnt, hmin)
    return qac + qcb, fcnt


def _finite_scalar(value, name):
    number = _scalar(value, name)
    if not math.isfinite(number):
        raise PracmaError(f"is.finite({name}) is not TRUE")
    return number


def _scalar(value, name):
    if isinstance(value, (bool, np.bool_)):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    array = np.asarray(value)
    if array.size != 1 or np.iscomplexobj(array) or not np.issubdtype(array.dtype, np.number):
        raise PracmaError(f"is.numeric({name}) is not TRUE")
    return float(array.reshape(-1)[0])


def _one(value):
    return float(np.asarray(value, dtype=float).reshape(-1)[0])


def _callable(fun):
    if not callable(fun):
        raise PracmaError("argument is not a function")
    return fun
