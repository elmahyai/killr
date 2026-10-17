"""Minimum-volume enclosing ellipsoid, from ``src/spannel.c`` and ``R/ellipsoidhull.R``."""

from __future__ import annotations

import math

import numpy as np


def _sweep(cov, nord, ixlo, nel, deter):
    """In-place SWEEP of one pivot. ``deter`` is the running determinant."""
    temp = cov[nel, nel]
    deter *= temp
    if deter <= 0.0:
        return deter
    if nord <= 1:
        cov[1, 1] = 1.0 / temp
        return deter
    for i in range(ixlo, nord + 1):
        if i == nel:
            continue
        for j in range(ixlo, i + 1):
            if j == nel:
                continue
            cov[j, i] = cov[i, j] - cov[i, nel] * cov[nel, j] / temp
            cov[i, j] = cov[j, i]
    cov[nel, nel] = 1.0
    for i in range(ixlo, nord + 1):
        cov[nel, i] = -cov[i, nel] / temp
        cov[i, nel] = cov[nel, i]
    return deter


def _spannel(x, tol=0.01, maxit=5000):
    """Return squared distances, probabilities, iterations, and ierr."""
    data = np.asarray(x, dtype=float)
    n, p = data.shape
    dat = np.column_stack([np.ones(n), data])
    prob = np.full(n, 1.0 / n)
    sqdist = np.zeros(n)
    cov = np.zeros((p + 1, p + 1))
    varsum = np.zeros(p + 1)
    varss = np.zeros(p + 1)
    for j in range(1, p + 1):
        column = dat[:, j]
        varsum[j] = float(column.sum())
        varss[j] = float(np.dot(column, column))
    for j in range(1, p + 1):
        aver = varsum[j] / n
        scal = math.sqrt(varss[j] / n - aver * aver)
        dat[:, j] = (dat[:, j] - aver) / scal
    ierr = 0
    it_done = maxit
    for it in range(maxit):
        cov.fill(0.0)
        for i in range(n):
            work = dat[i].copy()
            tempo = prob[i] * work
            for j in range(p + 1):
                for k in range(j + 1):
                    cov[k, j] += tempo[j] * work[k]
        for j in range(p + 1):
            for k in range(j + 1):
                cov[j, k] = cov[k, j]
        deter = 1.0
        failed = False
        for pivot in range(p + 1):
            deter = _sweep(cov, p, 0, pivot, deter)
            if deter <= 0.0:
                ierr = 2
                failed = True
                break
        if failed:
            it_done = maxit
            break
        dmax = 0.0
        for i in range(n):
            dist = -1.0
            row = dat[i]
            for j in range(p + 1):
                w_j = 0.0
                for k in range(p + 1):
                    w_j -= cov[j, k] * row[k]
                dist += w_j * row[j]
            sqdist[i] = dist
            if dmax < dist:
                dmax = dist
        if dmax <= p + tol:
            it_done = it
            break
        prob *= sqdist / p
    else:
        it_done = maxit
    return sqdist, prob, it_done, ierr


def _cov_wt(x, wt):
    """R ``cov.wt`` with the unbiased divisor. Returns center, cov, normalized weights."""
    data = np.asarray(x, dtype=float)
    weights = np.asarray(wt, dtype=float)
    weights = weights / weights.sum()
    center = weights @ data
    scaled = (data - center) * np.sqrt(weights)[:, None]
    cov = (scaled.T @ scaled) / (1.0 - float(np.sum(weights ** 2)))
    return center, cov, weights


def ellipsoid_hull(x, tol=0.01, maxit=5000, ret_wt=False, ret_sqdist=False, ret_pr=False):
    """Smallest ellipsoid around the rows of ``x``. NAs are omitted."""
    data = np.asarray(x, dtype=float)
    if data.ndim != 2:
        raise ValueError("'x' must be numeric  n x p matrix")
    if np.isnan(data).any():
        data = data[~np.isnan(data).any(axis=1)]
    n, p = data.shape
    if n == 0:
        raise ValueError("no points without missing values")
    sqdist, prob, iterations, ierr = _spannel(data, tol=float(tol), maxit=int(maxit))
    if np.any(prob < 0) or np.all(prob == 0):
        raise ValueError("computed some negative or all 0 probabilities")
    center, cov, weights = _cov_wt(data, prob)
    shape = cov * (1.0 - float(np.sum(weights ** 2)))
    d2 = float(np.average(sqdist, weights=prob))
    conv = iterations < maxit and ierr == 0
    result = {
        "loc": center.tolist(),
        "cov": shape.tolist(),
        "d2": d2,
        "tol": float(tol),
        "eps": float(np.max(sqdist) - p),
        "it": int(iterations),
        "maxit": int(maxit),
        "ierr": int(ierr),
        "conv": bool(conv),
    }
    if ret_wt:
        result["wt"] = weights.tolist()
    if ret_sqdist:
        result["sqdist"] = sqdist.tolist()
    if ret_pr:
        result["prob"] = prob.tolist()
    return result


def volume(object, log=False):
    """Volume of an ellipsoid. ``log=True`` returns the log volume."""
    loc = object["loc"]
    p = len(loc)
    if p < 1:
        raise ValueError("ellipsoid has no dimensions")
    cov = np.asarray(object["cov"], dtype=float)
    _sign, logdet = np.linalg.slogdet(cov)
    ldet2 = float(logdet) / 2.0
    lv = p / 2.0 * math.log(math.pi * float(object["d2"])) + ldet2 - math.lgamma(p / 2.0 + 1.0)
    return float(lv if log else math.exp(lv))


def ellipsoid_points(A, d2, loc, n_half=201):
    """Points on the boundary of a 2-dimensional ellipse."""
    matrix = np.asarray(A, dtype=float)
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise ValueError("'A' must be p x p  cov-matrix defining an ellipsoid")
    p = matrix.shape[0]
    if p != 2:
        raise ValueError("ellipsoidPoints() not yet implemented for p >= 3 dim.")
    loc = [float(v) for v in loc]
    d2 = float(d2)
    n_half = int(n_half)
    det_a = matrix[0, 0] * matrix[1, 1] - matrix[0, 1] ** 2
    yl2 = matrix[1, 1] * d2
    half = math.sqrt(yl2)
    step = (half - (-half)) / (n_half - 1) if n_half > 1 else 0.0
    y = np.array([-half + i * step for i in range(n_half)])
    if n_half:
        y[-1] = half
    discr = det_a * np.maximum(0.0, yl2 - y * y)
    sqrt_discr = np.sqrt(discr) / matrix[1, 1]
    sqrt_discr[0] = 0.0
    sqrt_discr[n_half - 1] = 0.0
    b = loc[0] + matrix[0, 1] / matrix[1, 1] * y
    yy = loc[1] + y
    top = np.column_stack([b - sqrt_discr, yy])
    bottom = np.column_stack([(b + sqrt_discr)[::-1], yy[::-1]])
    return np.vstack([top, bottom])


def predict_ellipsoid(object, n_out=201):
    """Boundary points of a fitted ellipsoid."""
    return ellipsoid_points(object["cov"], d2=object["d2"], loc=object["loc"], n_half=n_out)
