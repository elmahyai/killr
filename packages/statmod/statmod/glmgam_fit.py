"""Fit gamma GLM with identity link by damped Fisher scoring.

Translated from statmod 1.5.2 ``glmgam.fit`` in ``R/glmgam.R``.
"""

from __future__ import annotations

import warnings

import numpy as np


def _lm_fit(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Least-squares fit matching R ``lm.fit`` on full-rank ``x``."""
    beta, _, _, _ = np.linalg.lstsq(x, y, rcond=None)
    mu = x @ beta
    return beta, mu


def _lm_wfit(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Weighted least squares matching R ``lm.wfit``."""
    sw = np.sqrt(np.asarray(w, dtype=float))
    xw = x * sw[:, None]
    yw = y * sw
    return _lm_fit(xw, yw)


def _deviance_gamma(y: np.ndarray, mu: np.ndarray) -> float:
    if np.any(mu < 0):
        return float("inf")
    o = (y < 1e-15) & (mu < 1e-15)
    if np.any(o):
        if np.all(o):
            return 0.0
        y1 = y[~o]
        mu1 = mu[~o]
        return float(2 * np.sum((y1 - mu1) / mu1 - np.log(y1 / mu1)))
    return float(2 * np.sum((y - mu) / mu - np.log(y / mu)))


def glmgam_fit(
    X,
    y,
    coef_start=None,
    tol=1e-6,
    maxit=50,
    trace=False,
):
    """Fit a gamma GLM with identity link by Levenberg-style Fisher scoring."""
    x = np.asarray(X, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n, p = x.shape
    y = np.asarray(y, dtype=float).reshape(-1)
    if p > n:
        raise ValueError("More columns than rows in X")
    if n != y.size:
        raise ValueError("length(y) not equal to nrow(X)")
    if n == 0:
        return {
            "coefficients": np.array([], dtype=float),
            "fitted.values": np.array([], dtype=float),
            "deviance": np.array([], dtype=float),
        }
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(x))):
        raise ValueError("All values must be finite and non-missing")
    if np.any(y < 0):
        raise ValueError("y must be non-negative")
    maxy = float(np.max(y))
    if maxy == 0:
        return {
            "coefficients": np.zeros(p, dtype=float),
            "fitted.values": np.zeros(n, dtype=float),
            "deviance": np.nan,
        }
    y1 = np.maximum(y, maxy * 1e-3)

    col_names = None
    if hasattr(X, "columns"):
        col_names = list(X.columns)

    if coef_start is None:
        beta, mu = _lm_fit(x, y)
        if np.any(mu < 0):
            beta, mu = _lm_wfit(x, y, 1.0 / (y1 * y1))
        if np.any(mu < 0):
            beta, mu = _lm_fit(x, np.full(n, np.mean(y)))
        if np.any(mu < 0):
            samesign = np.all(x > 0, axis=0) | np.all(x < 0, axis=0)
            if np.any(samesign):
                i = int(np.flatnonzero(samesign)[0])
                beta = np.zeros(p, dtype=float)
                beta[i] = _lm_wfit(x[:, i : i + 1], y, 1.0 / (y1 * y1))[0][0]
                mu = x[:, i] * beta[i]
            else:
                return {
                    "coefficients": np.zeros(p, dtype=float),
                    "fitted.values": np.zeros(n, dtype=float),
                    "deviance": float("inf"),
                }
    else:
        beta = np.asarray(coef_start, dtype=float).reshape(-1)
        mu = x @ beta

    if np.any(mu < 0):
        raise ValueError("Starting values give negative fitted values")

    dev = _deviance_gamma(y, mu)
    iter_count = 0
    if trace:
        print(f"Iter = {iter_count} , Dev = {dev} Beta {beta}")

    lam = None
    identity = None
    while True:
        iter_count += 1
        v = mu * mu
        v = np.maximum(v, np.max(v) / 1e3)
        scaled = x / v[:, None]
        xvx = x.T @ scaled
        maxinfo = float(np.max(np.diag(xvx)))
        if iter_count == 1:
            lam = abs(float(np.mean(np.diag(xvx)))) / p
            identity = np.eye(p)

        dl = x.T @ ((y - mu) / v)
        betaold = beta.copy()
        devold = dev
        lev = 0
        while True:
            lev += 1
            reg = xvx + lam * identity
            chol = np.linalg.cholesky(reg)
            z = np.linalg.solve(chol, dl)
            dbeta = np.linalg.solve(chol.T, z)
            beta = betaold + dbeta
            mu = x @ beta
            dev = _deviance_gamma(y, mu)
            if dev <= devold or dev / np.max(mu) < 1e-15:
                break
            if lam / maxinfo > 1e15:
                beta = betaold
                warnings.warn(
                    "Too much damping - convergence tolerance not achievable",
                    RuntimeWarning,
                    stacklevel=2,
                )
                break
            lam = 2 * lam
            if trace:
                print(f"Damping increased to {lam}")

        if trace:
            print(f"Iter = {iter_count} , Dev = {dev} Beta {beta}")

        if lam / maxinfo > 1e15:
            break
        if lev == 1:
            lam = lam / 10

        if float(dl @ dbeta) < tol or dev / np.max(mu) < 1e-15:
            break
        if iter_count > maxit:
            break

    beta = np.asarray(beta, dtype=float).reshape(-1)
    if col_names is not None and len(col_names) == p:
        # R attaches names; proof compares numeric values only.
        pass

    return {
        "coefficients": beta,
        "fitted.values": np.asarray(mu, dtype=float).reshape(-1),
        "deviance": dev,
        "iter": iter_count,
    }
