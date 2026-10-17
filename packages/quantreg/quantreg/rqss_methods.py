"""summary.rqss and predict.rqss: standard errors, smooth-term tests and fitted values.

R/rqss.R of quantreg 6.1. The design is the stacked scipy.sparse X of the fit
(data rows, then the penalty rows), as ``rqss`` stores it. The Cholesky factor of
the sparse normal matrix is SciPy's dense upper factor in place of SparseM's
chol.matrix.csr, and the bandwidth is ``bandwidth_rq`` with hs = TRUE.

The covariance is the sandwich V = D^{-1} D0 D^{-1}, where D is the weighted
normal matrix and D0 = tau (1 - tau) X'X. R's chol and backsolve give the same V
as the inverse of D: this was checked against summary.rqss on the proof fits. The
smooth-term F test takes the intercept and one block of coefficients.
"""

from __future__ import annotations

import math
from collections.abc import Mapping

import numpy as np
import scipy.sparse as sp
from scipy.linalg import cholesky, solve_triangular
from scipy.stats import f as f_dist
from scipy.stats import norm
from scipy.stats import t as t_dist

from quantreg.bandwidth import bandwidth_rq
from quantreg.rqss import _parse_formula

SUMMARY_COLUMNS = ["Estimate", "Std. Error", "t value", "Pr(>|t|)"]
QSSTAB_COLUMNS = ["EDF", "Lambda", "Penalty", "F value", "Pr(>F)"]


def _predict_qss1(xyz, newdata):
    """predict.qss1 (and predict.qts1): linear interpolation of the fitted knots.

    Returns the interpolated values y and the design D without its first column,
    the rows that multiply the block of coefficients.
    """
    xyz = np.asarray(xyz, dtype=float)
    knots = xyz[:, 0]
    values = xyz[:, 1]
    if np.any(np.diff(knots) < 0):
        raise ValueError("x coordinates in qss1 object not monotone")
    xnew = np.asarray(newdata, dtype=float).reshape(-1)
    if xnew.size and (xnew.max() > knots.max() or xnew.min() < knots.min()):
        raise ValueError("no extrapolation allowed in predict.qss")
    p = knots.size
    m = xnew.size
    # cut(newdata, unique(x), include.lowest = TRUE): interval index, from 0
    left = np.maximum(np.searchsorted(knots, xnew, side="left") - 1, 0)
    lo = knots[left]
    hi = knots[left + 1]
    rows = np.arange(m)
    D = np.zeros((m, p))
    D[rows, left] = (hi - xnew) / (hi - lo)
    D[rows, left + 1] = (xnew - lo) / (hi - lo)
    return D @ values, D[:, 1:]


def _tri_area(v):
    """tri.area(v) for a 3 x 2 array of vertices: half the cross product, as R writes it."""
    return 0.5 * ((v[1, 0] - v[0, 0]) * (v[2, 1] - v[0, 1]) - (v[2, 0] - v[0, 0]) * (v[1, 1] - v[0, 1]))


def _barycentric(v):
    """barycentric(v) for a 4 x 2 array: the barycentric weights of row 4 in triangle rows 1 to 3."""
    b = np.zeros(3)
    area = _tri_area(v[0:3])
    b[0] = _tri_area(v[[3, 1, 2]]) / area
    b[1] = _tri_area(v[[0, 3, 2]]) / area
    b[2] = _tri_area(v[[0, 1, 3]]) / area
    if np.any(b < 0) or np.any(b > 1):
        raise ValueError("barycentric snafu")
    return b


def _qss2_xyz(object):
    """The n x 3 matrix (x, y, zfit) of a qss2 fit, as predict.qss2 reads object."""
    if isinstance(object, dict):
        xyz = object.get("xyz", object)
    else:
        xyz = getattr(object, "xyz", object)
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] != 3:
        raise ValueError("predict.qss2 needs an n x 3 object (x, y, zfit)")
    return xyz


def _qss2_newdata(newdata, fnames):
    """The new x and y: a named frame (a Mapping) by fnames, or a two-column matrix."""
    if isinstance(newdata, Mapping):
        if all(name in newdata for name in fnames):
            newx = np.asarray(newdata[fnames[0]], dtype=float).reshape(-1)
            newy = np.asarray(newdata[fnames[1]], dtype=float).reshape(-1)
            return newx, newy
        raise ValueError("qss object and newdata frame names conflict")
    arr = np.asarray(newdata, dtype=float)
    if arr.ndim == 2:
        if arr.shape[1] != 2:
            raise ValueError("newdata matrix must have 2 columns")
        return arr[:, 0].copy(), arr[:, 1].copy()
    raise ValueError("object 'newx' not found")


def predict_qss2(object, newdata, fnames=("x", "y"), **kwargs):
    """predict.qss2: interpolate a triogram surface at new (x, y) points.

    object is the n x 3 matrix (x, y, zfit) of a qss2 fit, the rows of xyz. newdata
    is a Mapping with the names in fnames, or an m x 2 matrix. fnames stands for the
    dimnames of the R object, which a NumPy array does not carry.

    The triangulation is interp's tri_mesh, the hull test is in_convex_hull and the
    triangle of each point is tri_find. The returned D is the m x (p - 1) sparse
    matrix of the barycentric weights, with its first column removed as R does, and
    z is D times the fitted values. Returns a dict with x, y, z and D.

    A point with no triangle (V = 0) cannot happen for points that pass the hull test
    in R's loop; here it raises rather than indexing x[0].
    """
    from interp.in_convex_hull import in_convex_hull
    from interp.tri_find import tri_find
    from interp.tri_mesh import tri_mesh

    del kwargs
    xyz = _qss2_xyz(object)
    x = xyz[:, 0]
    y = xyz[:, 1]
    z = xyz[:, 2]
    newx, newy = _qss2_newdata(newdata, fnames)
    trinew = tri_mesh(x, y)
    if not np.all(in_convex_hull(trinew, newx, newy)):
        raise ValueError("some newdata points outside convex hull")
    p = x.shape[0]
    m = newx.shape[0]
    located = tri_find(trinew, newx, newy)
    V = np.column_stack([located["i1"], located["i2"], located["i3"]]).astype(np.int64)
    if np.any(V == 0):
        raise ValueError("a newdata point is in no triangle")
    B = np.zeros((m, 3))
    for i in range(m):
        vertices = np.column_stack([x[V[i] - 1], y[V[i] - 1]])
        v = np.vstack([vertices, [newx[i], newy[i]]])
        B[i] = _barycentric(v)
    Dfull = sp.csr_matrix(
        (B.reshape(-1), (V - 1).reshape(-1), 3 * np.arange(m + 1)), shape=(m, p)
    )
    return {
        "x": newx,
        "y": newy,
        "z": np.asarray(Dfull @ z).reshape(-1),
        "D": Dfull[:, 1:],
    }


@np.errstate(divide="ignore", invalid="ignore")
def summary_rqss(object, cov=False, ztol=1e-5):
    """summary.rqss: the parametric table, the smooth-term table and, if cov, the covariance.

    The result is a dict with R's field names: coef (rows x 4) with coef_names,
    qsstab (rows x 5) with qsstab_names when there is a smooth term, fidelity,
    tau, formula, edf, n. With cov, Vcov, Vqss (one per smooth term) and V.
    """
    coef = np.asarray(object.coef, dtype=float).reshape(-1)
    resid = np.asarray(object.resid, dtype=float).reshape(-1)
    tau = float(object.tau)
    X = sp.csr_matrix(object.X, dtype=float)
    p = X.shape[1]
    ncA = np.asarray(object.ncA, dtype=int).reshape(-1)
    nrA = np.asarray(object.nrA, dtype=int).reshape(-1)
    m = ncA.size
    n = resid.size - int(nrA[-1])
    edf = int(object.edf)

    uhat = resid[:n]
    h = bandwidth_rq(tau, n, hs=True)
    while (tau - h < 0) or (tau + h > 1):
        h = h / 2
    spread = min(math.sqrt(float(np.var(uhat, ddof=1))), (np.quantile(uhat, 0.75) - np.quantile(uhat, 0.25)) / 1.34)
    h = (float(norm.ppf(tau + h)) - float(norm.ppf(tau - h))) * max(ztol, spread)
    f = np.concatenate([norm.pdf(uhat / h) / h, np.ones(resid.size - n)])

    weighted = (X.T @ sp.diags(f) @ X).toarray()
    weighted = 0.5 * (weighted + weighted.T)
    upper = cholesky(weighted, lower=False)
    inv_upper = solve_triangular(upper, np.eye(p), lower=False)
    inv_weighted = inv_upper @ inv_upper.T
    D0 = tau * (1.0 - tau) * (X.T @ X).toarray()
    V = inv_weighted @ D0 @ inv_weighted
    serr = np.sqrt(np.diag(V))

    p0 = int(ncA[0])
    estimate = coef[:p0]
    tval = estimate / serr[:p0]
    pval = 2.0 * (1.0 - t_dist.cdf(np.abs(tval), n - edf))
    ptab = np.column_stack([estimate, serr[:p0], tval, pval])
    names = list(object.coef_names[:p0])

    result = {
        "coef": ptab,
        "coef_names": names,
        "columns": list(SUMMARY_COLUMNS),
        "fidelity": float(object.fidelity),
        "tau": tau,
        "formula": object.formula,
        "edf": edf,
        "n": n,
    }
    if m > 1:
        ntab = np.zeros((m - 1, 5))
        Vqss = []
        for j in range(1, m):
            a, b = int(ncA[j - 1]), int(ncA[j])
            pen = resid[n + int(nrA[j - 1]) : n + int(nrA[j])]
            ntab[j - 1, 2] = float(np.sum(np.abs(pen)))
            ntab[j - 1, 0] = float(np.sum(np.abs(pen) > ztol))
            idx = np.concatenate([[0], np.arange(a, b)])
            v = V[np.ix_(idx, idx)]
            v = 0.5 * (v + v.T)
            Vqss.append(v)
            block = coef[a:b]
            ntab[j - 1, 3] = float(block @ np.linalg.solve(v[1:, 1:], block)) / ntab[j - 1, 0]
            ntab[j - 1, 4] = 1.0 - float(f_dist.cdf(ntab[j - 1, 3], ntab[j - 1, 0], n - edf))
        ntab[:, 1] = np.asarray(object.lambdas, dtype=float)
        ntab[:, 2] = ntab[:, 2] / ntab[:, 1]
        result["qsstab"] = ntab
        result["qsstab_names"] = [str(object.coef_names[int(ncA[j])])[:-1] for j in range(m - 1)]
    if cov:
        result["Vcov"] = V[:p0, :p0]
        if m > 1:
            result["Vqss"] = Vqss
        result["V"] = V
    return result


def predict_rqss(object, newdata, interval="none", level=0.95):
    """predict.rqss: fitted values at newdata, with a pointwise interval if asked.

    newdata is a mapping from names to arrays. Rows with a missing model variable
    are dropped, as model.frame does. interval="none" returns the fitted values as
    a 1-D array. interval="confidence" returns columns yhat, ylower, yupper.
    """
    if object.formula is None:
        raise ValueError("predict.rqss needs the formula the fit was made with")
    _response, intercept, parametric, _smooths = _parse_formula(object.formula)
    names = list(parametric) + list(object.qssnames)
    if any(name not in newdata for name in names):
        raise ValueError("newdata doesn't include some model variables")
    columns = {name: np.asarray(newdata[name], dtype=float).reshape(-1) for name in names}
    n_all = columns[names[0]].shape[0] if names else len(next(iter(newdata.values())))
    keep = np.ones(n_all, dtype=bool)
    for name in names:
        keep &= np.isfinite(columns[name])
    n = int(keep.sum())
    parts = []
    if intercept:
        parts.append(np.ones((n, 1)))
    for name in parametric:
        parts.append(columns[name][keep].reshape(-1, 1))
    X = np.hstack(parts) if parts else np.zeros((n, 0))
    p = X.shape[1]
    coef = np.asarray(object.coef, dtype=float).reshape(-1)
    y = X @ coef[:p]
    for name, component in zip(object.qssnames, object.qss):
        smooth_y, smooth_D = _predict_qss1(component.xyz, columns[name][keep])
        y = y + smooth_y
        if interval == "confidence":
            X = np.hstack([X, smooth_D])
    if interval == "confidence":
        V = summary_rqss(object, cov=True)["V"]
        v = np.sqrt(np.sum((X @ V) * X, axis=1))
        calpha = float(norm.ppf(1.0 - (1.0 - level) / 2.0))
        return np.column_stack([y, y - v * calpha, y + v * calpha])
    return y
