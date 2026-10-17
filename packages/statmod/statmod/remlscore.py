"""REML scoring for heteroscedastic normal regression.

Translated from statmod 1.5.2 ``remlscore`` in ``R/remlscor.R``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np


def _vecmat(v, m):
    """``diag(v) %*% M`` matching statmod ``vecmat``."""
    v = np.asarray(v, dtype=float).reshape(-1)
    m = np.asarray(m, dtype=float)
    return v[:, None] * m


def _lm_fit(x: np.ndarray, y: np.ndarray) -> dict:
    """Unweighted least squares matching R ``lm.fit`` on full-rank ``x``."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    p = x.shape[1]
    q_factor, r_factor = np.linalg.qr(x, mode="reduced")
    rank = int(np.sum(np.abs(np.diag(r_factor)) > np.max(x.shape) * np.finfo(float).eps))
    if rank < p:
        raise ValueError("X is of not of full column rank")
    coef = np.linalg.solve(r_factor, q_factor.T @ y)
    fitted = x @ coef
    return {
        "coefficients": coef,
        "residuals": y - fitted,
        "fitted.values": fitted,
        "rank": rank,
        "qr": {"Q": q_factor, "R": r_factor},
    }


def _lm_wfit(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict:
    """Weighted least squares matching R ``lm.wfit``."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    sw = np.sqrt(w)
    xw = x * sw[:, None]
    yw = y * sw
    q_factor, r_factor = np.linalg.qr(xw, mode="reduced")
    rank = int(np.sum(np.abs(np.diag(r_factor)) > np.max(x.shape) * np.finfo(float).eps))
    coef = np.linalg.solve(r_factor, q_factor.T @ yw)
    fitted = x @ coef
    return {
        "coefficients": coef,
        "residuals": y - fitted,
        "fitted.values": fitted,
        "rank": rank,
        "qr": {"Q": q_factor, "R": r_factor},
    }


def _log_det_from_qr(r_factor: np.ndarray) -> float:
    return 2.0 * float(np.sum(np.log(np.abs(np.diag(r_factor)))))


def remlscore(y, x, z, trace=False, tol=1e-5, maxit=40):
    """Fit mean-variance normal model by REML scoring."""
    y = np.asarray(y, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float)
    z = np.asarray(z, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if z.ndim == 1:
        z = z.reshape(-1, 1)
    n = y.size
    p = x.shape[1]
    qcols = z.shape[1]
    const = n * math.log(2 * math.pi)

    fitm = _lm_fit(x, y)
    qmat = fitm["qr"]["Q"]
    h = np.sum(qmat * qmat, axis=1)
    d = fitm["residuals"] ** 2

    wd = 1.0 - h
    zd = np.log(d / (1.0 - h)) + 1.27
    fitd = _lm_wfit(z, zd, wd)
    gam = np.where(np.isnan(fitd["coefficients"]), 0.0, fitd["coefficients"])
    phi = np.exp(fitd["fitted.values"])
    fitm = _lm_wfit(x, y, 1.0 / phi)
    d = fitm["residuals"] ** 2
    dev = float(
        np.sum(d / phi)
        + np.sum(np.log(phi))
        + const
        + _log_det_from_qr(fitm["qr"]["R"])
    )

    iter_count = 0
    if trace:
        print(f"Iter = {iter_count} , Dev = {dev} Gamma {gam}")

    q2_cols = p * (p + 1) // 2
    q2 = np.zeros((n, q2_cols))
    lam = None
    ident = None
    while True:
        iter_count += 1
        qfull = fitm["qr"]["Q"]
        j0 = 0
        for k in range(p):
            ncol = p - k
            q2[:, j0 : j0 + ncol] = qfull[:, :ncol] * qfull[:, k:p]
            j0 += ncol
        if p > 1:
            q2[:, p:] = math.sqrt(2.0) * q2[:, p:]
        h = q2[:, :p] @ np.ones(p)
        q2z = q2.T @ z
        zvz = (z.T @ _vecmat(1.0 - 2.0 * h, z) + q2z.T @ q2z) / 2.0
        maxinfo = float(np.max(np.diag(zvz)))
        if iter_count == 1:
            lam = abs(float(np.mean(np.diag(zvz)))) / qcols
            ident = np.eye(qcols)

        zd = (d - (1.0 - h) * phi) / phi
        dl = (z.T @ zd).reshape(-1) / 2.0

        gamold = gam.copy()
        devold = dev
        lev = 0
        while True:
            lev += 1
            rfac = np.linalg.cholesky(zvz + lam * ident)
            dgam = np.linalg.solve(rfac.T, np.linalg.solve(rfac, dl))
            gam = gamold + dgam
            phi = np.exp(z @ gam)
            fitm = _lm_wfit(x, y, 1.0 / phi)
            d = fitm["residuals"] ** 2
            dev = float(
                np.sum(d / phi)
                + np.sum(np.log(phi))
                + const
                + _log_det_from_qr(fitm["qr"]["R"])
            )
            if dev < devold - 1e-15:
                break
            if lam / maxinfo > 1e15:
                gam = gamold
                warnings.warn("Too much damping - convergence tolerance not achievable", stacklevel=2)
                break
            lam = 2.0 * lam
            if trace:
                print(f"Damping increased to {lam}")

        if trace:
            print(f"Iter = {iter_count} , Dev = {dev} Gamma {gam}")

        if lam / maxinfo > 1e15:
            break
        if lev == 1:
            lam = lam / 10.0
        if float(dl @ dgam) < tol:
            break
        if iter_count > maxit:
            warnings.warn("reml: Max iterations exceeded", stacklevel=2)
            break

    cov_gam = np.linalg.inv(zvz)
    se_gam = np.sqrt(np.diag(cov_gam))
    r_beta = fitm["qr"]["R"]
    cov_beta = np.linalg.inv(r_beta.T @ r_beta)
    se_beta = np.sqrt(np.diag(cov_beta))

    return {
        "beta": fitm["coefficients"],
        "se.beta": se_beta,
        "gamma": gam,
        "se.gam": se_gam,
        "mu": fitm["fitted.values"],
        "phi": phi,
        "deviance": dev,
        "h": h,
        "cov.beta": cov_beta,
        "cov.gam": cov_gam,
        "iter": iter_count,
    }
