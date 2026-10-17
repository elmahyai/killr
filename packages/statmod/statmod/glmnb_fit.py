"""Fit negative binomial GLM with log link by damped Fisher scoring.

Translated from statmod 1.5.2 ``glmnb.fit`` in ``R/glmnb.R``.
"""

from __future__ import annotations

import warnings

import numpy as np


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
    q, r = np.linalg.qr(xw, mode="reduced")
    coef = np.linalg.solve(r, q.T @ yw)
    fitted = x @ coef
    return {"coefficients": coef, "residuals": y - fitted, "fitted.values": fitted}


def _dot_lm_fit(x: np.ndarray, y: np.ndarray) -> dict:
    """Unweighted least squares matching R ``.lm.fit``."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    q, r = np.linalg.qr(x, mode="reduced")
    coef = np.linalg.solve(r, q.T @ y)
    fitted = x @ coef
    return {"coefficients": coef, "residuals": y - fitted}


def _qr_coef(x: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Coefficients from R ``qr.coef(qr(x), y)``."""
    q, r = np.linalg.qr(x, mode="reduced")
    return np.linalg.solve(r, q.T @ y)


def _chol_pivot_backsolve(matrix: np.ndarray, dl: np.ndarray) -> tuple[np.ndarray, int, np.ndarray]:
    """Step vector from R ``backsolve(chol(..., pivot=TRUE), ...)``."""
    from scipy.linalg.lapack import dpstrf

    ac = np.array(matrix, dtype=np.float64, copy=True)
    r_factor, piv, rank, info = dpstrf(ac, lower=0)
    if info < 0:
        raise np.linalg.LinAlgError("dpstrf failed")
    r_factor = np.triu(r_factor)
    p = piv.astype(int) - 1
    j = p[:rank]
    rr = r_factor[:rank, :rank]
    dl_j = np.asarray(dl, dtype=float).reshape(-1)[j]
    y = np.linalg.solve(rr.T, dl_j)
    z = np.linalg.solve(rr, y)
    dbeta = np.zeros(dl.size, dtype=float)
    dbeta[j] = z
    return dbeta, int(rank), piv


def _unit_dev_poissonlimit(y: np.ndarray, mu: np.ndarray, phi: np.ndarray) -> np.ndarray:
    b = y - mu
    b2 = 0.5 * b * b * phi * (1.0 + phi * (2.0 / 3.0 * b - y))
    return 2.0 * (y * np.log(y / mu) - b - b2)


def _unit_dev_gamma(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    return 2.0 * ((y - mu) / mu - np.log(y / mu))


def _unit_dev_negbin(y: np.ndarray, mu: np.ndarray, phi: np.ndarray) -> np.ndarray:
    return 2.0 * (
        y * np.log(y / mu) - (y + 1.0 / phi) * np.log((1.0 + y * phi) / (1.0 + mu * phi))
    )


def _total_deviance(
    y: np.ndarray, mu: np.ndarray, phi: np.ndarray, weights: np.ndarray
) -> float:
    if np.any(np.isinf(mu)):
        return float("inf")
    poisson_like = phi < 1e-4
    gamma_like = phi * mu > 1e6
    negbin = ~(poisson_like | gamma_like)
    y1 = y + 1e-8
    mu1 = mu + 1e-8
    unit_dev = np.empty_like(y1, dtype=float)
    if np.any(poisson_like):
        unit_dev[poisson_like] = _unit_dev_poissonlimit(
            y1[poisson_like], mu1[poisson_like], phi[poisson_like]
        )
    if np.any(gamma_like):
        m = mu1[gamma_like]
        alpha = m / (1.0 + phi[gamma_like] * m)
        unit_dev[gamma_like] = _unit_dev_gamma(y1[gamma_like], m) * alpha
    if np.any(negbin):
        unit_dev[negbin] = _unit_dev_negbin(
            y1[negbin], mu1[negbin], phi[negbin]
        )
    return float(np.sum(weights * unit_dev))


def glmnb_fit(
    X,
    y,
    dispersion,
    weights=None,
    offset=0,
    coef_start=None,
    start_method="mean",
    tol=1e-6,
    maxit=50,
    trace=False,
):
    """Fit a negative binomial GLM with log link by Levenberg-style Fisher scoring."""
    y = np.asarray(y, dtype=float).reshape(-1)
    if y.size == 0:
        raise ValueError("y has length zero")
    if np.any(y < 0):
        raise ValueError("y must be non-negative")
    if not np.all(np.isfinite(y)):
        raise ValueError("All y values must be finite and non-missing")

    x = np.asarray(X, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    n, p = x.shape
    if n != y.size:
        raise ValueError("length(y) not equal to nrow(X)")
    if not np.all(np.isfinite(x)):
        raise ValueError("All X values must be finite and non-missing")
    if p > n:
        raise ValueError("More columns than rows in X")

    col_names = [f"x{i + 1}" for i in range(p)]
    if hasattr(X, "columns"):
        col_names = [str(c) for c in X.columns]

    phi = np.broadcast_to(np.asarray(dispersion, dtype=float), (n,)).copy().reshape(-1)
    if np.any(phi < 0):
        raise ValueError("dispersion values must be non-negative")

    offset = np.broadcast_to(np.asarray(offset, dtype=float), (n,)).copy().reshape(-1)
    if not np.all(np.isfinite(offset)):
        raise ValueError("All offset values must be finite and non-missing")

    if weights is None:
        weights = np.ones(n, dtype=float)
    else:
        weights = np.broadcast_to(np.asarray(weights, dtype=float), (n,)).copy().reshape(-1)
    if np.any(weights <= 0):
        raise ValueError("All weights must be positive")

    ymax = float(np.max(y))
    if ymax == 0.0:
        if col_names[0] == "(Intercept)":
            beta = np.zeros(p, dtype=float)
            beta[0] = float("-inf")
            mu = np.zeros(n, dtype=float)
            return {
                "coefficients": beta,
                "fitted.values": mu,
                "deviance": 0.0,
                "iter": 0,
                "convergence": "converged",
            }
        one = np.ones(n, dtype=float)
        fit = _dot_lm_fit(x, one)
        if float(np.max(np.abs(fit["residuals"]))) < 1.0:
            beta = -1e10 * fit["coefficients"]
            mu = np.zeros(n, dtype=float)
            return {
                "coefficients": beta,
                "fitted.values": mu,
                "deviance": 0.0,
                "iter": 0,
                "convergence": "converged",
            }
        if coef_start is None:
            fit = _lm_wfit(x, offset, weights)
            coef_start = -fit["coefficients"]

    delta = 1.0 / 6.0
    y1 = np.maximum(y, delta)
    if coef_start is None:
        if start_method not in ("log(y)", "mean"):
            raise ValueError('start.method must be "log(y)" or "mean"')
        if start_method == "log(y)":
            fit = _lm_wfit(x, np.log(y1) - offset, weights)
            beta = fit["coefficients"]
            mu = np.exp(fit["fitted.values"] + offset)
        else:
            n_exp = np.exp(offset)
            rate = y / n_exp
            w = weights * n_exp / (1.0 + phi * n_exp)
            beta_mean = np.log(np.sum(w * rate) / np.sum(w))
            beta = _qr_coef(x, np.full(n, beta_mean, dtype=float))
            mu = np.exp(x @ beta + offset)
    else:
        beta = np.asarray(coef_start, dtype=float).reshape(-1)
        mu = np.exp(x @ beta + offset)

    dev = _total_deviance(y, mu, phi, weights)
    iter_count = 0
    if trace:
        print(f"Iter = {iter_count} , Dev = {dev} Beta {beta}")

    lam = None
    identity = None
    lambdabig = False
    while True:
        iter_count += 1
        if iter_count > maxit:
            break

        v_div_mu = 1.0 + phi * mu
        wx = (weights * mu / v_div_mu)[:, None] * x
        xvx = x.T @ wx
        maxinfo = float(np.max(np.diag(xvx)))
        if iter_count == 1:
            lam = max(maxinfo * 1e-6, 1e-13)
            lambdaceiling = maxinfo * 1e13
            lambdabig = False
            identity = np.eye(p)

        dl = x.T @ (weights * (y - mu) / v_div_mu)
        lev = 0
        while True:
            lev += 1
            reg = xvx + lam * identity
            step, rank, _ = _chol_pivot_backsolve(reg, dl)
            while rank < p:
                lam = lam * 10.0
                reg = xvx + lam * identity
                step, rank, _ = _chol_pivot_backsolve(reg, dl)

            dbeta = step
            betanew = beta + dbeta
            munew = np.exp(x @ betanew + offset)
            devnew = _total_deviance(y, munew, phi, weights)
            if devnew <= dev or devnew / ymax < 1e-13:
                beta = betanew
                mu = munew
                dev = devnew
                break

            lam = 2.0 * lam
            if trace:
                print(f"Damping increased to {lam}")
            lambdabig = lam > lambdaceiling
            if lambdabig:
                warnings.warn(
                    "Too much damping - convergence tolerance not achievable",
                    RuntimeWarning,
                    stacklevel=2,
                )
                break

        if trace:
            print(f"Iter = {iter_count} , Dev = {dev} Beta {beta}")

        if lambdabig:
            break

        scoresquare = float(dl @ dbeta)
        if trace:
            print(f"Convergence criterion {scoresquare} {dl} {dbeta}")
        if scoresquare < tol or dev / ymax < 1e-12:
            break

        if lev == 1:
            lam = lam / 10.0

    beta = np.asarray(beta, dtype=float).reshape(-1)
    convergence = "converged"
    if lambdabig:
        convergence = "lambdabig"
    if iter_count > maxit:
        convergence = "maxit"

    return {
        "coefficients": beta,
        "fitted.values": np.asarray(mu, dtype=float).reshape(-1),
        "deviance": dev,
        "iter": iter_count,
        "convergence": convergence,
    }
