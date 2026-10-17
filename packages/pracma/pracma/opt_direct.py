"""Derivative-free minimizers from pracma."""

from __future__ import annotations

import math

import numpy as np

from pracma._util import PracmaError, as_1d
from pracma.arrays import eye, ones
from pracma.opt_helpers import _is_numeric, _match_one, _scalar, _warn

_MISSING = object()


def nelder_mead(fn, x0, *args, adapt=True, tol=1e-08, maxfeval=5000, step=None, **kwargs):
    if not _is_numeric(x0):
        raise PracmaError("is.numeric(x0) is not TRUE")
    start = as_1d(x0)
    n = start.size
    if step is None:
        step = np.ones(n)
    else:
        step = as_1d(step)
        if not _is_numeric(step):
            raise PracmaError("is.numeric(step) is not TRUE")
    if step.size != n:
        raise PracmaError("Argument 'step' must be of the same length as 'x0'.")
    if not callable(fn):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def objective(x):
        return _scalar(fn(x, *args, **kwargs))

    reqmin = tol
    kcount = maxfeval
    konvge = kcount / 100
    if adapt:
        rcoeff = 1.0
        ecoeff = 1.0 + 2.0 / n
        ccoeff = 0.75 - 1.0 / (2 * n)
        scoeff = 1.0 - 1.0 / n
        eps = 0.001
    else:
        rcoeff, ecoeff, ccoeff, scoeff, eps = 1.0, 2.0, 0.5, 0.5, 0.001
    jcount = konvge
    dn = n
    nn = n + 1
    dnn = nn
    delta = 1.0
    rq = reqmin * dn
    y = np.zeros(n + 1)
    p = np.zeros((n, n + 1))
    xmin = np.full(n, np.nan)
    ynewlo = np.nan
    icount = 0
    numres = 0
    ifault = 0
    while True:
        p[:, nn - 1] = start
        y[nn - 1] = objective(start)
        icount += 1
        for j in range(n):
            saved = start[j]
            start[j] = start[j] + step[j] * delta
            p[:, j] = start
            y[j] = objective(start)
            icount += 1
            start[j] = saved
        ilo = int(np.argmin(y))
        ylo = y[ilo]
        while icount < kcount:
            ihi = int(np.argmax(y))
            keep = np.ones(nn, dtype=bool)
            keep[ihi] = False
            pbar = np.sum(p[:, keep], axis=1) / dn
            pstar = pbar + rcoeff * (pbar - p[:, ihi])
            ystar = objective(pstar)
            icount += 1
            if ystar < ylo:
                p2star = pbar + ecoeff * (pstar - pbar)
                y2star = objective(p2star)
                icount += 1
                if ystar < y2star:
                    p[:, ihi] = pstar
                    y[ihi] = ystar
                else:
                    p[:, ihi] = p2star
                    y[ihi] = y2star
            else:
                better = int(np.sum(ystar < y))
                if better > 1:
                    p[:, ihi] = pstar
                    y[ihi] = ystar
                elif better == 0:
                    p2star = pbar + ccoeff * (p[:, ihi] - pbar)
                    y2star = objective(p2star)
                    icount += 1
                    if y[ihi] < y2star:
                        for j in range(nn):
                            p[:, j] = scoeff * (p[:, j] + p[:, ilo])
                            xmin = p[:, j]
                            y[j] = objective(xmin)
                            icount += 1
                        ilo = int(np.argmin(y))
                        ylo = y[ilo]
                        continue
                    p[:, ihi] = p2star
                    y[ihi] = y2star
                elif better == 1:
                    p2star = pbar + ccoeff * (pstar - pbar)
                    y2star = objective(p2star)
                    icount += 1
                    if y2star <= ystar:
                        p[:, ihi] = p2star
                        y[ihi] = y2star
                    else:
                        p[:, ihi] = pstar
                        y[ihi] = ystar
            if y[ihi] < ylo:
                ylo = y[ihi]
                ilo = ihi
            jcount -= 1
            if jcount > 0:
                continue
            if icount <= kcount:
                jcount = konvge
                center = np.sum(y) / dnn
                if np.sum((y - center) ** 2) <= rq:
                    break
        xmin = p[:, ilo].copy()
        ynewlo = y[ilo]
        if kcount < icount:
            ifault = 2
            break
        ifault = 0
        for i in range(n):
            delta = step[i] * eps
            xmin[i] = xmin[i] + delta
            z = objective(xmin)
            icount += 1
            if z < ynewlo:
                ifault = 2
                break
            xmin[i] = xmin[i] - delta - delta
            z = objective(xmin)
            icount += 1
            if z < ynewlo:
                ifault = 2
                break
            xmin[i] = xmin[i] + delta
        if ifault == 0:
            break
        start = xmin.copy()
        delta = eps
        numres += 1
    return {
        "xmin": xmin,
        "fmin": ynewlo,
        "count": icount,
        "info": {"solver": "Nelder-Mead", "restarts": numres},
    }


def anms(fn, x0, *args, tol=1e-10, maxfeval=None, **kwargs):
    if not (_is_numeric(x0) and as_1d(x0).size > 1):
        raise PracmaError("is.numeric(x0) && length(x0) > 1 is not TRUE")
    point = as_1d(x0)
    d = point.size
    d1 = d + 1
    if not callable(fn):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def objective(x):
        return _scalar(fn(x, *args, **kwargs))

    if maxfeval is None:
        maxfeval = 50 * d**2
    alpha = 1.0
    beta = 1 + 2 / d
    gamma = 0.75 - 0.5 / d
    delta = 1 - 1 / d
    scalefactor = min(max(float(np.max(np.abs(point))), 1.0), 10.0)
    offset = (1 - math.sqrt(d1)) / d * ones(1, d)
    D0 = np.vstack([eye(d), offset])
    X = np.zeros((d1, d))
    FX = np.zeros(d1)
    for i in range(d1):
        X[i, :] = point + scalefactor * D0[i, :]
        FX[i] = objective(X[i, :])
    order = np.argsort(FX)
    FX = FX[order]
    X = X[order, :]
    ct = d1
    while np.max(np.abs(X[1:, :] - X[:-1, :])) >= scalefactor * tol:
        if ct > maxfeval:
            break
        M = np.mean(X[:d, :], axis=0)
        xref = (1 + alpha) * M - alpha * X[d, :]
        Fref = objective(xref)
        ct += 1
        if Fref < FX[0]:
            xexp = (1 + alpha * beta) * M - alpha * beta * X[d, :]
            Fexp = objective(xexp)
            ct += 1
            if Fexp < Fref:
                X[d, :], FX[d] = xexp, Fexp
            else:
                X[d, :], FX[d] = xref, Fref
        elif Fref < FX[d - 1]:
            X[d, :], FX[d] = xref, Fref
        elif Fref < FX[d]:
            xoc = (1 + alpha * gamma) * M - alpha * gamma * X[d, :]
            Foc = objective(xoc)
            ct += 1
            if Foc <= Fref:
                X[d, :], FX[d] = xoc, Foc
            else:
                for i in range(1, d1):
                    X[i, :] = X[0, :] + delta * (X[i, :] - X[0, :])
                    FX[i] = objective(X[i, :])
                ct += d
        else:
            xic = (1 - gamma) * M + gamma * X[d, :]
            Fic = objective(xic)
            ct += 1
            if Fic < FX[d]:
                X[d, :], FX[d] = xic, Fic
            else:
                for i in range(1, d1):
                    X[i, :] = X[0, :] + delta * (X[i, :] - X[0, :])
                    FX[i] = objective(X[i, :])
                ct += d
        order = np.argsort(FX)
        FX = FX[order]
        X = X[order, :]
    return {"xmin": X[0, :].copy(), "fmin": FX[0], "nfeval": ct}


def _hjexplore(xb, xc, f, h, direction, fbold=_MISSING):
    x = np.array(xb, dtype=float, copy=True)
    if fbold is _MISSING:
        fb = _scalar(f(x))
        numf = 1
    else:
        fb = fbold
        numf = 0
    fx = fb
    xt = np.array(xc, dtype=float, copy=True)
    sf = 0
    dirh = h * direction
    n = xb.size
    for k in range(n):
        p1 = xt + dirh[:, k]
        ft1 = _scalar(f(p1))
        numf += 1
        p2 = xt - dirh[:, k]
        ft2 = _scalar(f(p2))
        numf += 1
        if min(ft1, ft2) < fb:
            sf = 1
            if ft1 < ft2:
                xt, fb = p1, ft1
            else:
                xt, fb = p2, ft2
    if sf == 1:
        x, fx = xt, fb
    return {"x": x, "fx": fx, "sf": sf, "numf": numf}


def _hjbexplore(xb, xc, f, lo, up, h, direction, fbold=_MISSING):
    x = np.array(xb, dtype=float, copy=True)
    if fbold is _MISSING:
        fb = _scalar(f(x))
        numf = 1
    else:
        fb = fbold
        numf = 0
    fx = fb
    xt = np.array(xc, dtype=float, copy=True)
    sf = 0
    dirh = h * direction
    n = xb.size
    for k in range(n):
        p1 = xt + dirh[:, k]
        if p1[k] <= up[k]:
            ft1 = _scalar(f(p1))
            numf += 1
        else:
            ft1 = fb
        p2 = xt - dirh[:, k]
        if lo[k] <= p2[k]:
            ft2 = _scalar(f(p2))
            numf += 1
        else:
            ft2 = fb
        if min(ft1, ft2) < fb:
            sf = 1
            if ft1 < ft2:
                xt, fb = p1, ft1
            else:
                xt, fb = p2, ft2
    if sf == 1:
        x, fx = xt, fb
    return {"x": x, "fx": fx, "sf": sf, "numf": numf}


def _hjsearch(xb, f, h, direction, fcount, maxfeval, target):
    x = np.array(xb, dtype=float, copy=True)
    hje = _hjexplore(xb, x, f, h, direction)
    x, fx, sf = hje["x"], hje["fx"], hje["sf"]
    finc = hje["numf"]
    while sf == 1:
        d = x - xb
        xb = x
        xc = x + d
        fb = fx
        hje = _hjexplore(xb, xc, f, h, direction, fb)
        x, fx, sf = hje["x"], hje["fx"], hje["sf"]
        finc += hje["numf"]
        if sf == 0:
            hje = _hjexplore(xb, xb, f, h, direction, fb)
            x, fx, sf = hje["x"], hje["fx"], hje["sf"]
            finc += hje["numf"]
        if fcount + finc > maxfeval or abs(fx) > target:
            break
    return {"x": x, "fx": fx, "sf": sf, "finc": finc}


def _hjbsearch(xb, f, lo, up, h, direction, fcount, maxfeval, target):
    x = np.array(xb, dtype=float, copy=True)
    hje = _hjbexplore(xb, x, f, lo, up, h, direction)
    x, fx, sf = hje["x"], hje["fx"], hje["sf"]
    finc = hje["numf"]
    while sf == 1:
        d = x - xb
        xb = x
        xc = np.minimum(np.maximum(x + d, lo), up)
        fb = fx
        hje = _hjbexplore(xb, xc, f, lo, up, h, direction, fb)
        x, fx, sf = hje["x"], hje["fx"], hje["sf"]
        finc += hje["numf"]
        if sf == 0:
            hje = _hjbexplore(xb, xb, f, lo, up, h, direction, fb)
            x, fx, sf = hje["x"], hje["fx"], hje["sf"]
            finc += hje["numf"]
        if fcount + finc > maxfeval or abs(fx) > target:
            break
    return {"x": x, "fx": fx, "sf": sf, "finc": finc}


def _bounds(lb, ub, n, x0):
    if not _is_numeric(lb) or not _is_numeric(ub):
        raise PracmaError("Lower and upper limits must be numeric.")
    lower = as_1d(lb)
    upper = as_1d(ub)
    if lower.size == 1:
        lower = np.repeat(lower, n)
    if upper.size == 1:
        upper = np.repeat(upper, n)
    if not np.all(lower <= upper):
        raise PracmaError("All lower limits must be smaller than upper limits.")
    if not np.all(lower <= x0) or not np.all(x0 <= upper):
        raise PracmaError("Infeasible starting values -- check limits.")
    return lower, upper


def _hj(x0, f, tol, target, maxfeval, info):
    n = x0.size
    nsteps = math.floor(math.log2(1.0 / tol))
    steps = 2.0 ** (-np.arange(nsteps))
    direction = np.eye(n)
    x = np.array(x0, dtype=float, copy=True)
    fx = _scalar(f(x))
    fcount = 1
    ns = 0
    while ns < nsteps and fcount < maxfeval and abs(fx) < target:
        ns += 1
        hjs = _hjsearch(x, f, steps[ns - 1], direction, fcount, maxfeval, target)
        x, fx = hjs["x"], hjs["fx"]
        fcount += hjs["finc"]
        if info:
            print(ns, "\t", fcount, "\t", fx, "\t", x[0], "...")
    if fcount > maxfeval:
        _warn("Function evaluation limit exceeded -- may not converge.")
        conv = 1
    elif abs(fx) > target:
        _warn("Function exceeds min/max value -- may not converge.")
        conv = 1
    else:
        conv = 0
    return {"xmin": x, "fmin": fx, "fcalls": fcount, "niter": ns, "convergence": conv}


def _hjb(x0, f, lower, upper, tol, target, maxfeval, info):
    n = x0.size
    lower, upper = _bounds(lower, upper, n, x0)
    nsteps = math.floor(math.log2(1.0 / tol))
    steps = 2.0 ** (-np.arange(nsteps))
    direction = np.eye(n)
    x = np.array(x0, dtype=float, copy=True)
    fx = _scalar(f(x))
    fcount = 1
    ns = 0
    while ns < nsteps and fcount < maxfeval and abs(fx) < target:
        ns += 1
        hjs = _hjbsearch(x, f, lower, upper, steps[ns - 1], direction, fcount, maxfeval, target)
        x, fx = hjs["x"], hjs["fx"]
        fcount += hjs["finc"]
        if info:
            print(ns, "\t", fcount, "\t", fx, "\t", x[0], "...")
    if fcount > maxfeval:
        _warn("Function evaluation limit exceeded -- may not converge.")
        conv = 1
    elif abs(fx) > target:
        _warn("Function exceeds min/max value -- may not converge.")
        conv = 1
    else:
        conv = 0
    return {"xmin": x, "fmin": fx, "fcalls": fcount, "niter": ns, "convergence": conv}


def hooke_jeeves(x0, fn, *args, lb=None, ub=None, tol=1e-08, maxfeval=10000, target=np.inf, info=False, **kwargs):
    if not _is_numeric(x0):
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    point = as_1d(x0)
    n = point.size
    if n == 1:
        raise PracmaError("Do not use Hooke-Jeeves for univariate functions.")
    if not callable(fn):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def objective(x):
        return fn(x, *args, **kwargs)

    if lb is None and ub is None:
        result = _hj(point, objective, tol, target, maxfeval, info)
    else:
        if lb is None:
            lb = np.full(n, -np.inf)
        if ub is None:
            ub = np.full(n, np.inf)
        lower, upper = _bounds(lb, ub, n, point)
        result = _hjb(point, objective, lower, upper, tol, target, maxfeval, info)
    return {
        "xmin": result["xmin"],
        "fmin": result["fmin"],
        "count": result["fcalls"],
        "convergence": 0,
        "info": {"solver": "Hooke-Jeeves", "iterations": result["niter"]},
    }


def fminsearch(fn, x0, *args, lower=None, upper=None, method="Nelder-Mead", minimize=True, maxiter=1000, tol=1e-08, **kwargs):
    point = as_1d(x0) if _is_numeric(x0) else np.asarray(x0)
    n = point.size if _is_numeric(x0) else 0
    if not _is_numeric(x0) or n == 0:
        raise PracmaError("Argument 'x0' must be a numeric vector.")
    if n == 1:
        raise PracmaError("Don't use 'fminsearch' for one-dimensional minimization.")
    method = _match_one(method, ["Nelder-Mead", "Hooke-Jeeves"])
    scale = 1 if minimize else -1
    if not callable(fn):
        raise PracmaError("Argument function 'fun' not known in parent environment.")

    def objective(x):
        return scale * fn(x, *args, **kwargs)

    if (lower is not None or upper is not None) and method == "Nelder-Mead":
        raise PracmaError(
            "'Nelder-Mead' cannot handle bounds constraints;\n"
            "Instead, use 'Hooke-Jeeves' with bounds/box constraints."
        )
    if method == "Nelder-Mead":
        opt = nelder_mead(objective, point, tol=tol, maxfeval=5 * maxiter)
    else:
        if lower is None and upper is not None:
            lower = np.full(n, -np.inf)
        if lower is not None and upper is None:
            upper = np.full(n, np.inf)
        opt = hooke_jeeves(point, objective, lb=lower, ub=upper, tol=tol, maxfeval=10 * maxiter)
    fopt = opt["fmin"] if minimize else -opt["fmin"]
    return {
        "xmin": opt["xmin"],
        "fmin": fopt,
        "count": opt["count"],
        "convergence": 0,
        "info": opt["info"],
    }
