"""rqProcess and KhmaladzeTest from R's khmal.R (quantreg 6.1).

``rq_process`` is ``rqProcess`` on a model matrix ``x`` with the intercept column
included, because the formula step is not translated. Its grid method runs
``rq.fit.fnb`` (``quantreg.interior.rq_fit_fnb``) at each tau, and the covariance
at each tau is the ``nid`` sandwich of ``summary.rq`` (``quantreg.infer.summary_rq``).

``khmaladze_test`` is ``KhmaladzeTest`` on the same model matrix.

R's ``matrix * vector`` recycles the vector down the matrix in column-major
order. ``_r_recycle`` keeps that, which matters when the matrix has more than one
row of slopes.
"""

from __future__ import annotations

import math

import numpy as np

from quantreg.infer import summary_rq
from quantreg.interior import rq_fit_fnb
from quantreg.more import akj, lm_fit_recursive

# R's sqrt(.Machine$double.eps), the spacing tolerance on taus.
_SQRT_EPS = math.sqrt(np.finfo(float).eps)


def _as_matrix(x):
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    return array


def _upper_chol(matrix):
    """R's chol(): the upper factor U with U'U = matrix."""
    return np.linalg.cholesky(matrix).T


def _r_recycle(matrix, vector):
    """R's ``matrix * vector`` when the vector is shorter: recycled in column-major order."""
    flat = matrix.ravel(order="F")
    scaled = flat * np.resize(np.asarray(vector, dtype=float).reshape(-1), flat.size)
    return scaled.reshape(matrix.shape, order="F")


def rq_process(x, y, taus=None, null_h="location", names=None):
    """rqProcess on the model matrix ``x`` and response ``y``.

    Returns a dict with ``taus``, ``qtaus`` (length ntaus), ``Vhat`` and ``vhat``
    ((p - 1) x ntaus), and ``n``. ``names`` is the optional list of coefficient
    names; ``vars`` is the slope names when given. Taus outside [0, 1] raise, as R's
    pivot branch does. Any ``null_h`` other than "location" or "location-scale"
    leaves ``Vhat`` and ``vhat`` as the raw slope rows, as R does.
    """
    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    taus = np.atleast_1d(np.asarray(taus, dtype=float)).reshape(-1)
    xbar = design.mean(axis=0)
    if np.any(taus < 0) or np.any(taus > 1):
        raise ValueError("pivot method is now deprecated for Ktest")
    gaps = np.diff(taus)
    if gaps.size == 0 or abs(np.max(gaps) - np.min(gaps)) > _SQRT_EPS:
        raise ValueError("rqProcess must be evaluated on equally spaced taus")

    ntaus = taus.size
    coefs = np.empty((ntaus, p))
    cov = np.empty((p, p, ntaus))
    for j, tau in enumerate(taus):
        fit = rq_fit_fnb(design, response, tau=float(tau))
        summary = summary_rq(
            {
                "x": design,
                "y": response,
                "method": "fn",
                "coefficients": fit["coefficients"],
                "residuals": fit["residuals"],
                "tau": float(tau),
                "names": names,
            },
            se="nid",
            covariance=True,
        )
        coefs[j] = summary["coefficients"][:, 0]
        cov[:, :, j] = summary["cov"]

    qtaus = coefs @ xbar
    raw = coefs.T[1:, :]
    Vhat = raw.copy()
    vhat = raw.copy()

    if null_h == "location-scale":
        # lm(coefs[, -1] ~ coefs[, 1]): one slope per response column.
        design2 = np.column_stack([np.ones(ntaus), coefs[:, 0]])
        fitted_coef = np.linalg.lstsq(design2, coefs[:, 1:], rcond=None)[0]
        b = fitted_coef[1]
        R = coefs[:, 1:] - design2 @ fitted_coef
        for j in range(ntaus):
            V = cov[:, :, j]
            cross = np.outer(V[1:, 0], b)
            v = V[1:, 1:] + V[0, 0] * np.outer(b, b) - cross - cross.T
            v = np.linalg.inv(v)
            upper = _upper_chol(0.5 * (v + v.T))
            Vhat[:, j] = upper @ R[j, :]
            for k in range(p - 1):
                i = k + 1
                s = V[i, i] + V[0, 0] * b[k] ** 2 - 2.0 * V[i, 0] * b[k]
                vhat[k, j] = R[j, k] / math.sqrt(s)
    elif null_h == "location":
        b = coefs.mean(axis=0)
        R = coefs.T - b[:, None]
        for j in range(ntaus):
            V = cov[:, :, j]
            A = np.linalg.inv(V[1:, 1:])
            B = _upper_chol(0.5 * (A + A.T))
            Vhat[:, j] = B @ R[1:, j]
            vhat[:, j] = R[1:, j] / np.sqrt(np.diag(V)[1:])

    out = {"taus": taus, "qtaus": qtaus, "Vhat": Vhat, "vhat": vhat, "n": n}
    if names is not None:
        out["vars"] = list(names)[1:]
    return out


def _gdot(x, taus, h):
    """R's gdot: the density, its psi, and Qt * psi + 1 at the quantiles of x.

    approxfun(taus, Qt) and approxfun(Qt, .) are exact at their knots, so the
    density and psi are evaluated at Qt directly.
    """
    # R's quantile(x, taus) is base type 7, which is NumPy's "linear" method. R's own
    # quantreg::kuantile is not the reference: it pairs order statistics wrongly for dense taus.
    qt = np.quantile(np.asarray(x, dtype=float), np.asarray(taus, dtype=float), method="linear")
    z = akj(x, z=qt, h=h)
    return np.column_stack([z["dens"], z["psi"], qt * z["psi"] + 1.0])


def khmaladze_test(x, y, taus=None, null_h="location", trim=(0.05, 0.95), h=1.0):
    """KhmaladzeTest on the model matrix ``x`` and response ``y``.

    Returns a dict with ``nullH``, ``Tn``, ``THn``, ``taus``, ``Vhat`` and ``Vtil``
    (each ntaus x (p - 1), as R's t(Vhat) and t(Vtil)).
    """
    if taus is None:
        taus = np.arange(1, 100) / 100.0
    taus = np.atleast_1d(np.asarray(taus, dtype=float)).reshape(-1)
    fit = rq_process(x, y, taus, null_h=null_h)
    G = _gdot(fit["qtaus"], taus, h=1.0)
    ntaus = taus.size

    Vhat = _r_recycle(fit["Vhat"], G[:, 0])
    vhat = _r_recycle(fit["vhat"], G[:, 0])
    Vtil = Vhat.copy()
    vtil = vhat.copy()

    if null_h == "location":
        X = G[:-1, 1]
    else:
        X = G[:-1, 1:3]
    m = ntaus - 1
    design1 = np.column_stack([np.ones(m), X.reshape(m, -1)])
    for i in range(Vhat.shape[0]):
        Y = Vhat[i, 1:]
        y_ = vhat[i, 1:]
        B = lm_fit_recursive(X, Y)
        b = lm_fit_recursive(X, y_)
        # R: diag(cbind(1, X) %*% B), the recursive fitted value at each step.
        Vtil[i, 1:] = Y - np.sum(design1 * B.T, axis=1)
        vtil[i, 1:] = y_ - np.sum(design1 * b.T, axis=1)

    scale = math.sqrt(float(np.max(taus) - np.min(taus)))
    keep = (taus >= trim[0]) & (taus <= trim[1])
    Tvtil = (vtil - vtil[:, [1]]) / scale
    TVtil = np.sum(np.abs(Vtil - Vtil[:, [1]]) / scale, axis=0)[keep]
    Tn = float(np.max(TVtil))
    THn = np.max(np.abs(Tvtil[:, keep]), axis=1)
    return {
        "nullH": null_h,
        "Tn": Tn,
        "THn": THn,
        "taus": taus,
        "Vhat": Vhat.T,
        "Vtil": Vtil.T,
    }
