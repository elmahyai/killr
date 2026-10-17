"""Generalized least squares estimates for a condensed linear model (nlme ``glsEstimate``)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

import numpy as np

import nlmegls
from nlme.conlin import ConLin
from nlme.linpack_qr import dgemv
from nlme.recalc import recalc

__all__ = ["GlsEstimate", "glsEstimate"]


@dataclass(frozen=True, slots=True)
class GlsEstimate:
    """``glsEstimate`` result: the list with ``logLik``, ``beta``, ``sigma``, and the rest."""

    logLik: float
    beta: np.ndarray
    sigma: float
    varBeta: np.ndarray
    fitted: np.ndarray
    resid: np.ndarray
    auxSigma: float
    names: tuple[str, ...]


def glsEstimate(
    object: Any,
    conLin: ConLin,
    singular_ok: bool = False,
) -> GlsEstimate:
    """Fit the coefficients of the condensed model under the plug-ins in ``object``.

    R's ``glsEstimate`` runs no optimizer, so no nlminb stand-in is needed here. The
    nlminb outer loop of ``gls`` (PORT in R) is the one that uses the stand-in,
    ``nlme.gls._nlminb_standin``, and it calls this function at each step.

    ``object`` is a glsStruct (or an empty one). ``conLin`` is not changed. The
    fitted values use the original ``Xy``, as R does, because ``recalc`` runs
    after ``oXy`` is saved.
    """
    dd = conLin.dims
    p = int(dd["p"])
    reml = int(dd["REML"])
    o_xy = np.asarray(conLin.Xy, dtype=np.float64)
    fix_sig = bool(conLin.fixedSigma)
    sigma0 = float(conLin.sigma)
    con = recalc(object, conLin)
    flat = np.asarray(con.Xy, dtype=np.float64).reshape(-1, order="F")
    beta_all, sigma, log_lik_fit, var_beta_flat, rank, pivot = nlmegls.gls_estimate(
        flat.tolist(),
        int(dd["N"]),
        p,
        reml,
        sigma0,
        0.0,
    )
    rnk = int(rank)
    rnkm1 = rnk - 1
    if not singular_ok and rnkm1 < p:
        raise ValueError(f'computed "gls" fit is singular, rank {rnk}')
    n_total = int(dd["N"])
    n_obs = n_total - reml * p
    piv = [int(v) for v in pivot[:rnkm1]]
    names_all = tuple(conLin.names) if conLin.names is not None else tuple(
        f"V{j}" for j in range(o_xy.shape[1])
    )
    nam_coef = tuple(names_all[j] for j in piv)
    # varBeta arrives column-major as rnkm1 by rnkm1, then R transposes it.
    var_beta = np.asarray(var_beta_flat[: rnkm1 * rnkm1], dtype=np.float64).reshape(
        (rnkm1, rnkm1), order="F"
    ).T
    beta = np.asarray(beta_all[:rnkm1], dtype=np.float64)
    # R: fitted <- c(oXy[, namCoef, drop = FALSE] %*% beta), which is BLAS dgemv.
    fitted = dgemv(o_xy[:, piv], beta)
    resid = o_xy[:, p] - fitted
    ll = float(con.logLik) + float(log_lik_fit)
    if not fix_sig:
        log_lik = (n_obs * (math.log(n_obs) - (1.0 + math.log(2.0 * math.pi)))) / 2.0 + ll
    else:
        log_lik = (-n_obs / 2.0) * math.log(2.0 * math.pi) + ll
    aux_sigma = math.sqrt(float(np.sum(resid * resid))) / math.sqrt(n_obs)
    return GlsEstimate(
        logLik=float(log_lik),
        beta=beta,
        sigma=float(sigma),
        varBeta=var_beta,
        fitted=np.asarray(fitted, dtype=np.float64),
        resid=np.asarray(resid, dtype=np.float64),
        auxSigma=float(aux_sigma),
        names=nam_coef,
    )
