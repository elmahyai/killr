"""Negative log-likelihood for cumulative link models (ordinal clm.nll)."""

import numpy as np
from scipy.special import expit
from scipy.stats import cauchy, norm

from ordinal._fitted import get_fitted
from ordinal.links import dgumbel, dlgamma, ggumbel, gcauchy, glgamma, glogis, gnorm


def _link_gfun(rho, eta):
    link = rho.link
    eta = np.asarray(eta, dtype=float).reshape(-1)
    if link == "logit":
        return glogis(eta)
    if link == "probit":
        return gnorm(eta)
    if link == "loglog":
        return ggumbel(eta, max=True)
    if link == "cloglog":
        return ggumbel(eta, max=False)
    if link == "cauchit":
        return gcauchy(eta)
    if link == "log-gamma":
        return glgamma(eta, rho.lambda_)
    raise ValueError("link not recognized")


def _link_dfun(rho, eta):
    link = rho.link
    eta = np.asarray(eta, dtype=float).reshape(-1)
    if link == "logit":
        p = expit(eta)
        return p * (1.0 - p)
    if link == "probit":
        return norm.pdf(eta)
    if link == "loglog":
        return dgumbel(eta, max=True)
    if link == "cloglog":
        return dgumbel(eta, max=False)
    if link == "cauchit":
        return cauchy.pdf(eta)
    if link == "log-gamma":
        return dlgamma(eta, rho.lambda_)
    raise ValueError("link not recognized")


def _clm_prepare(rho, par=None):
    if par is not None:
        rho.par = np.asarray(par, dtype=float).reshape(-1)
    n_psi = int(rho.n_psi)
    k = int(rho.k)
    par = rho.par
    if k > 0:
        sigma = rho.soff * np.exp(rho.s @ par[n_psi : n_psi + k])
    else:
        sigma = rho.sigma
    eta1 = (rho.b1 @ par[:n_psi] + rho.o1) / sigma
    eta2 = (rho.b2 @ par[:n_psi] + rho.o2) / sigma
    fitted = get_fitted(eta1, eta2, rho.link, rho.lambda_)
    rho.sigma = np.asarray(sigma, dtype=float).reshape(-1)
    rho.eta1 = np.asarray(eta1, dtype=float).reshape(-1)
    rho.eta2 = np.asarray(eta2, dtype=float).reshape(-1)
    rho.fitted = np.asarray(fitted, dtype=float).reshape(-1)
    return rho.fitted


def clm_nll(rho, par=None):
    fitted = _clm_prepare(rho, par)
    if np.all(np.isfinite(fitted)) and np.all(fitted > 0):
        return -float(np.sum(rho.wts * np.log(fitted)))
    return float("inf")


def clm_grad(rho):
    """Gradient of the negative log-likelihood (ordinal clm.grad)."""
    p1 = _link_dfun(rho, rho.eta1)
    p2 = _link_dfun(rho, rho.eta2)
    wtpr = rho.wts / rho.fitted
    scale = rho.sigma
    c2 = rho.b1 * (p1 / scale)[:, None] - rho.b2 * (p2 / scale)[:, None]
    k = int(rho.k)
    rho._p1 = p1
    rho._p2 = p2
    rho._wtpr = wtpr
    rho._C2 = c2
    if k <= 0:
        rho._C3 = None
        return -(c2.T @ wtpr)
    c3 = -(rho.eta1 * p1 - rho.eta2 * p2)[:, None] * rho.s
    rho._C3 = c3
    design = np.hstack([c2, c3])
    return -(design.T @ wtpr)


def clm_hess(rho):
    """Hessian of the negative log-likelihood (ordinal clm.hess)."""
    if not hasattr(rho, "_C2"):
        clm_grad(rho)
    p1 = rho._p1
    p2 = rho._p2
    wtpr = rho._wtpr
    c2 = rho._C2
    c3 = rho._C3
    scale = rho.sigma
    g1 = _link_gfun(rho, rho.eta1)
    g2 = _link_gfun(rho, rho.eta2)
    wtprpr = wtpr / rho.fitted
    dg_psi = (rho.b1 * (g1 * wtpr / scale**2)[:, None]).T @ rho.b1
    dg_psi -= (rho.b2 * (g2 * wtpr / scale**2)[:, None]).T @ rho.b2
    d_block = dg_psi - c2.T @ (c2 * wtprpr[:, None])
    k = int(rho.k)
    if k <= 0:
        return -d_block
    wtprsig = wtpr / scale
    epg1 = p1 + g1 * rho.eta1
    epg2 = p2 + g2 * rho.eta2
    et = (
        rho.b1.T @ (-(wtprsig * epg1)[:, None] * rho.s)
        - rho.b2.T @ (-(wtprsig * epg2)[:, None] * rho.s)
        - c2.T @ (wtprpr[:, None] * c3)
    )
    mid = wtpr * (
        (rho.eta1 * p1 - rho.eta2 * p2) ** 2 / rho.fitted - (rho.eta1 * epg1 - rho.eta2 * epg2)
    )
    f_block = -(rho.s.T @ (mid[:, None] * rho.s))
    upper = np.hstack([d_block, et])
    lower = np.hstack([et.T, f_block])
    return -np.vstack([upper, lower])


def clm_grad_direct(rho, par):
    clm_nll(rho, par)
    return clm_grad(rho)
