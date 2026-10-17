"""REML scoring for gamma regression with structured dispersion.

Translated from statmod 1.5.2 ``remlscoregamma`` in ``R/remlscorgamma.R``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from statmod.canonic_digamma import canonic_digamma
from statmod.digamma import _make_link

import scipy.special as _sp

_DBL_EPS = float(np.finfo(np.float64).eps)
_GLM_MAXIT = 50
_GLM_EPS = 1e-14


def _digamma(x: np.ndarray) -> np.ndarray:
    return _sp.digamma(np.asarray(x, dtype=float))


def _trigamma(x: np.ndarray) -> np.ndarray:
    return _sp.polygamma(1, np.asarray(x, dtype=float))


def _lm_fit(x: np.ndarray, y: np.ndarray) -> dict:
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    q_factor, r_factor = np.linalg.qr(x, mode="reduced")
    rank = int(np.sum(np.abs(np.diag(r_factor)) > np.max(x.shape) * _DBL_EPS))
    coef = np.linalg.solve(r_factor, q_factor.T @ y)
    fitted = x @ coef
    return {
        "coefficients": coef,
        "residuals": y - fitted,
        "fitted.values": fitted,
        "rank": rank,
    }


def _gamma_deviance_component(y: np.ndarray, mu: np.ndarray) -> np.ndarray:
    return 2.0 * ((y - mu) / mu - np.log(y / mu))


def _reml_deviance(
    const: float, phi: np.ndarray, d: np.ndarray, r_diag: np.ndarray, rank: int
) -> float:
    inv_phi = 1.0 / phi
    terms = [
        float(
            2.0
            * (
                math.lgamma(float(inv_phi[i]))
                + (1.0 + math.log(float(phi[i]))) / float(phi[i])
            )
            + float(d[i]) / float(phi[i])
        )
        for i in range(phi.size)
    ]
    qr_det = float(np.prod(np.abs(r_diag[:rank])))
    return math.fsum([const, *terms, const, 2.0 * math.log(qr_det)])


def _glm_fit_gamma(
    x: np.ndarray,
    y: np.ndarray,
    *,
    linkfun,
    linkinv,
    mu_eta,
    weights: np.ndarray | None = None,
    mustart: np.ndarray | None = None,
) -> dict:
    """IRLS fit matching R ``stats::glm.fit`` for Gamma with a custom link."""
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n, p = x.shape
    prior = np.ones(n) if weights is None else np.asarray(weights, dtype=float).reshape(-1)

    if mustart is not None:
        mu = np.asarray(mustart, dtype=float).reshape(-1)
    else:
        mu = y + (y == 0) / 6.0
    mu = np.clip(mu, _DBL_EPS, None)
    eta = linkfun(mu)
    dev_old = float(np.sum(_gamma_deviance_component(y, mu), dtype=np.longdouble))

    coef = np.zeros(p)
    rank = p
    q_factor = None
    r_factor = None

    for _ in range(_GLM_MAXIT):
        mu = np.clip(mu, _DBL_EPS, None)
        mu_eta_val = mu_eta(eta)
        variance = mu * mu
        w_sq = prior * (mu_eta_val * mu_eta_val) / variance
        w_sq = np.maximum(w_sq, 0.0)
        scale = np.sqrt(w_sq)
        working = (y - mu) / mu_eta_val
        z = eta + working
        xw = x * scale[:, None]
        zw = z * scale
        q_factor, r_factor = np.linalg.qr(xw, mode="reduced")
        rank = int(np.sum(np.abs(np.diag(r_factor)) > np.max(x.shape) * _DBL_EPS))
        coef = np.linalg.solve(r_factor, q_factor.T @ zw)
        eta = x @ coef
        mu = linkinv(eta)
        dev = float(np.sum(_gamma_deviance_component(y, mu), dtype=np.longdouble))
        if abs(dev - dev_old) / (0.1 + abs(dev)) < _GLM_EPS:
            break
        dev_old = dev

    mu = linkinv(x @ coef)
    return {
        "coefficients": coef,
        "fitted.values": mu,
        "rank": rank,
        "qr": {"Q": q_factor, "R": r_factor, "qr": r_factor},
    }


def remlscoregamma(
    y,
    x,
    z,
    mlink="log",
    dlink="log",
    trace=False,
    tol=1e-5,
    maxit=40,
):
    """Approximate REML for gamma regression with structured dispersion."""
    y = np.asarray(y, dtype=float).reshape(-1)
    x = np.asarray(x, dtype=float)
    z = np.asarray(z, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    if z.ndim == 1:
        z = z.reshape(-1, 1)
    n = y.size
    p = x.shape[1]
    const = 2.0 * float(np.sum(np.log(y)))

    _, mli = _make_link(mlink)
    _, dli = _make_link(dlink)
    mlinkfun = mli["linkfun"]
    mlinkinv = mli["linkinv"]
    mmu_eta = mli["mu.eta"]
    dlinkfun = dli["linkfun"]
    dlinkinv = dli["linkinv"]
    dmu_eta = dli["mu.eta"]

    fitm = _glm_fit_gamma(
        x,
        y,
        linkfun=mlinkfun,
        linkinv=mlinkinv,
        mu_eta=mmu_eta,
    )
    mu = fitm["fitted.values"]
    d = _gamma_deviance_component(y, mu)
    rank = fitm["rank"]

    phi_scalar = -1.0 / float(canonic_digamma(np.array([float(np.mean(d))]))) * n / (n - rank)
    phi = np.full(n, phi_scalar)
    fitd = _lm_fit(z, dlinkfun(phi))
    gam = np.where(np.isnan(fitd["coefficients"]), 0.0, fitd["coefficients"])
    if float(np.mean(np.abs(fitd["residuals"]))) / phi[0] > 1e-12:
        phi = np.asarray(dlinkinv(z @ gam), dtype=float).reshape(-1)
        fitm = _glm_fit_gamma(
            x,
            y,
            linkfun=mlinkfun,
            linkinv=mlinkinv,
            mu_eta=mmu_eta,
            weights=1.0 / phi,
            mustart=mu,
        )
        mu = fitm["fitted.values"]
        d = _gamma_deviance_component(y, mu)
        rank = fitm["rank"]
    else:
        fitm = _glm_fit_gamma(
            x,
            y,
            linkfun=mlinkfun,
            linkinv=mlinkinv,
            mu_eta=mmu_eta,
            weights=1.0 / phi,
            mustart=mu,
        )
        mu = fitm["fitted.values"]
        d = _gamma_deviance_component(y, mu)
        rank = fitm["rank"]

    r_diag = np.abs(np.diag(fitm["qr"]["qr"]))
    dev = _reml_deviance(const, phi, d, r_diag, rank)

    iter_count = 0
    if trace:
        print(f"Iter = {iter_count} , Dev = {dev} Gamma {gam}")

    q2_cols = p * (p + 1) // 2
    h = np.zeros(n)
    info = None

    while True:
        iter_count += 1
        eta = dlinkfun(phi)
        phidot = dmu_eta(eta)[:, None] * z
        z2 = phidot / phi[:, None] / math.sqrt(2.0)

        qfull = fitm["qr"]["Q"]
        q2 = np.zeros((n, q2_cols))
        j0 = 0
        for k in range(p):
            ncol = p - k
            q2[:, j0 : j0 + ncol] = qfull[:, :ncol] * qfull[:, k:p]
            j0 += ncol
        if p > 1:
            q2[:, p:] = math.sqrt(2.0) * q2[:, p:]

        h = q2[:, :p] @ np.ones(p)
        q2z = q2.T @ z2
        inv_phi = 1.0 / phi
        extradisp = (
            2.0
            * (_trigamma(inv_phi) - _trigamma(inv_phi / h) / h)
            / (phi * phi)
            - (1.0 - h)
        )
        info = z2.T @ ((extradisp + 1.0 - 2.0 * h)[:, None] * z2) + q2z.T @ q2z

        inv_h_phi = 1.0 / (h * phi)
        deltah = 2.0 * (_digamma(inv_h_phi) + np.log(h) - _digamma(inv_phi))
        dl = phidot.T @ ((d - deltah) / (2.0 * phi * phi))

        r_info = np.linalg.cholesky(info)
        dgam = np.linalg.solve(r_info.T, np.linalg.solve(r_info, dl))
        gam = gam + dgam

        phi = np.asarray(dlinkinv(z @ gam), dtype=float).reshape(-1)
        fitm = _glm_fit_gamma(
            x,
            y,
            linkfun=mlinkfun,
            linkinv=mlinkinv,
            mu_eta=mmu_eta,
            weights=1.0 / phi,
            mustart=mu,
        )
        mu = fitm["fitted.values"]
        d = _gamma_deviance_component(y, mu)
        rank = fitm["rank"]
        r_diag = np.abs(np.diag(fitm["qr"]["qr"]))
        dev = _reml_deviance(const, phi, d, r_diag, rank)

        if trace:
            print(f"Iter = {iter_count} , Dev = {dev} Gamma {gam}")

        if float(dl @ dgam) < tol:
            break
        if iter_count > maxit:
            warnings.warn("Max iterations exceeded", stacklevel=2)
            break

    cov_gam = np.linalg.solve(info, np.eye(info.shape[0]))
    se_gam = np.sqrt(np.diag(cov_gam))
    r_beta = fitm["qr"]["R"]
    se_beta = np.sqrt(np.diag(np.linalg.inv(r_beta.T @ r_beta)))

    return {
        "beta": fitm["coefficients"],
        "se.beta": se_beta,
        "gamma": gam,
        "se.gam": se_gam,
        "mu": mu,
        "phi": phi,
        "deviance": dev,
        "h": h,
    }
