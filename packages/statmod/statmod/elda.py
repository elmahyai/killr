"""Extreme limiting dilution analysis (multi-group).

Translated from statmod 1.5.2 ``elda`` in ``R/elda.R``.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from scipy.stats import chi2

from statmod.digamma import _make_link, _pnorm
from statmod.elda_one_group import _binom_dev_resids, elda_one_group

_DBL_EPS = float(np.finfo(np.float64).eps)
_QR_TOL = 1e-11
_GLM_MAXIT = 25
_GLM_EPS = 1e-8


def _pnorm_scalar(x: float) -> float:
    return float(_pnorm(float(x)))


def _pchisq_upper(q: float, df: float) -> float:
    if math.isnan(q) or math.isnan(df) or df <= 0:
        return math.nan
    return float(chi2.sf(q, df))


def _as_factor(group) -> tuple[np.ndarray, list[str]]:
    """R ``factor(group)`` with sorted levels."""
    arr = np.asarray(group)
    if arr.dtype.kind in {"U", "S", "O"}:
        levels = sorted({str(x) for x in arr.ravel()})
    else:
        levels = sorted({str(x) for x in np.unique(arr)})
    level_to_idx = {lev: i for i, lev in enumerate(levels)}
    flat = arr.ravel()
    codes = np.array([level_to_idx[str(x)] for x in flat], dtype=int)
    return codes, levels


def _group_column_name(level: str) -> str:
    return f"group{level}"


def _design_group_logdose(
    group_codes: np.ndarray, group_levels: list[str], dose: np.ndarray
) -> tuple[np.ndarray, list[str]]:
    n = dose.size
    pieces = [np.ones(n, dtype=float)]
    names = ["(Intercept)"]
    for lev in group_levels[1:]:
        idx = group_levels.index(lev)
        pieces.append((group_codes == idx).astype(float))
        names.append(_group_column_name(lev))
    pieces.append(np.log(np.asarray(dose, dtype=float)))
    names.append("log(dose)")
    return np.column_stack(pieces), names


def _design_logdose(dose: np.ndarray) -> tuple[np.ndarray, list[str]]:
    n = dose.size
    return np.column_stack([np.ones(n), np.log(np.asarray(dose, dtype=float))]), [
        "(Intercept)",
        "log(dose)",
    ]


def _qr_coef_glm(x: np.ndarray, z: np.ndarray, w: np.ndarray) -> tuple[np.ndarray, int]:
    design = x * w[:, None]
    n_coef = design.shape[1]
    if n_coef == 0:
        return np.zeros(0), 0
    q_factor, r_factor = np.linalg.qr(design, mode="reduced")
    diagonal = np.abs(np.diag(r_factor))
    scale = diagonal[0] if diagonal[0] > 0.0 else 1.0
    rank = int(np.sum(diagonal > _QR_TOL * scale))
    qty = q_factor.T @ (z * w)
    beta = np.zeros(n_coef, dtype=np.float64)
    if rank == n_coef:
        beta = np.linalg.solve(r_factor, qty)
    elif rank > 0:
        beta_s, _, rank_s, _ = np.linalg.lstsq(design, z * w, rcond=_QR_TOL)
        beta = beta_s
        rank = int(rank_s)
    return beta, rank


def _glm_binomial_cloglog(
    x: np.ndarray,
    y: np.ndarray,
    *,
    weights: np.ndarray,
) -> dict[str, Any]:
    """Weighted binomial GLM with cloglog link matching ``stats::glm.fit``."""
    _, link = _make_link("cloglog")
    linkfun = link["linkfun"]
    linkinv = link["linkinv"]
    mu_eta = link["mu.eta"]

    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    prior = np.asarray(weights, dtype=float).reshape(-1)
    n, p = x.shape

    mu = (prior * y + 0.5) / (prior + 1.0)
    mu = np.clip(mu, _DBL_EPS, 1.0 - _DBL_EPS)
    eta = linkfun(mu)
    dev_old = float(np.sum(_binom_dev_resids(y, mu, prior), dtype=np.longdouble))
    beta = np.zeros(p)
    rank = 0
    r_factor = None

    for _ in range(_GLM_MAXIT):
        mu = np.clip(mu, _DBL_EPS, 1.0 - _DBL_EPS)
        mu_eta_val = mu_eta(eta)
        variance = mu * (1.0 - mu)
        good = (
            (prior > 0)
            & (mu > 0)
            & (mu_eta_val != 0)
            & np.isfinite(variance)
            & (variance > 0)
        )
        if not np.any(good):
            break
        working = (y[good] - mu[good]) / mu_eta_val[good]
        z = eta[good] + working
        w_sq = prior[good] * mu_eta_val[good] ** 2 / variance[good]
        scale = np.sqrt(np.maximum(w_sq, 0.0))
        beta, rank = _qr_coef_glm(x[good], z, scale)
        _, r_factor = np.linalg.qr(x[good] * scale[:, None], mode="reduced")
        eta = x @ beta
        mu = linkinv(eta)
        dev = float(np.sum(_binom_dev_resids(y, mu, prior), dtype=np.longdouble))
        if abs(dev - dev_old) / (0.1 + abs(dev)) < _GLM_EPS:
            dev_old = dev
            break
        dev_old = dev

    mu = linkinv(x @ beta)
    dev = float(np.sum(_binom_dev_resids(y, mu, prior), dtype=np.longdouble))
    return {
        "coefficients": beta,
        "deviance": dev,
        "rank": rank,
        "qr_r": r_factor,
        "names": None,
    }


def _summary_coef_se(fit: dict[str, Any], x: np.ndarray, names: list[str]) -> dict[str, tuple[float, float]]:
    """Coefficient estimates and standard errors like ``summary.glm``."""
    beta = np.asarray(fit["coefficients"], dtype=float)
    r_factor = fit["qr_r"]
    rank = int(fit["rank"])
    if r_factor is None or rank == 0:
        return {name: (float(beta[i]), math.nan) for i, name in enumerate(names)}

    r = np.asarray(r_factor, dtype=float)
    p = r.shape[1]
    r_rank = r[:rank, :rank]
    try:
        ri = np.linalg.inv(r_rank)
        cov = ri @ ri.T
    except np.linalg.LinAlgError:
        cov = np.full((rank, rank), math.nan)
    se = np.sqrt(np.maximum(np.diag(cov), 0.0))
    out: dict[str, tuple[float, float]] = {}
    for i, name in enumerate(names):
        if i < rank:
            out[name] = (float(beta[i]), float(se[i]))
        else:
            out[name] = (float(beta[i]), math.nan)
    return out


def elda(
    response,
    dose,
    tested=None,
    group=None,
    observed=False,
    confidence=0.95,
    test_unit_slope=False,
):
    """Limiting dilution analysis for one or more groups."""
    response = np.asarray(response, dtype=float)
    dose = np.asarray(dose, dtype=float)
    n = response.size
    if n == 0:
        raise ValueError("No data")
    if dose.size != n:
        raise ValueError("length(dose) doesn't match length(response)")

    if tested is None:
        tested = np.ones(n, dtype=float)
    else:
        tested = np.asarray(tested, dtype=float)
        if tested.size != n:
            if tested.size == 1:
                tested = np.full(n, float(tested.flat[0]))
            else:
                raise ValueError("length(tested) doesn't match length(response)")

    if group is None:
        group = np.ones(n)
    group_codes, group_levels = _as_factor(group)
    num_group = len(group_levels)

    sz = (response == 0) & ((dose == 0) | (tested == 0))
    if np.any(sz):
        keep = ~sz
        out = elda(
            response=response[keep],
            dose=dose[keep],
            tested=tested[keep],
            group=group[keep] if np.asarray(group).size == n else group,
            observed=observed,
            confidence=confidence,
            test_unit_slope=test_unit_slope,
        )
        out["response"] = response
        out["dose"] = dose
        out["tested"] = tested
        return out

    y = response / tested
    if np.any(y < 0):
        raise ValueError("Negative values for response or tested")
    if np.any(y > 1):
        raise ValueError("The response cannot be greater than the number tested")
    if np.any(dose <= 0):
        raise ValueError("dose must be positive")

    out: dict[str, Any] = {
        "response": response,
        "tested": tested,
        "dose": dose,
        "group": group,
        "num.group": num_group,
    }

    ci = np.zeros((num_group, 3), dtype=float)
    ci[:, 0] = np.nan
    colnames = ["Lower", "Estimate", "Upper"]
    rownames = [f"Group {lev}" for lev in group_levels]

    deviance0 = 0.0
    dloglik_logdose = 0.0
    fisher_logdose = 0.0
    dloglik_dose = 0.0
    fisher_dose = 0.0

    for i in range(num_group):
        index = group_codes == i
        fit0 = elda_one_group(
            response=response[index],
            dose=dose[index],
            tested=tested[index],
            observed=observed,
            confidence=confidence,
            trace=False,
        )
        deviance0 += fit0["deviance"]
        dloglik_logdose += fit0["dloglik.logdose"]
        fisher_logdose += fit0["FisherInfo.logdose"]
        dloglik_dose += fit0["dloglik.dose"]
        fisher_dose += fit0["FisherInfo.dose"]
        ci[i, :] = np.maximum(fit0["CI.frequency"], 1.0)

    out["CI"] = ci
    out["CI_colnames"] = colnames
    out["CI_rownames"] = rownames

    if num_group > 1:
        fitequal = elda_one_group(
            response=response,
            dose=dose,
            tested=tested,
            observed=observed,
            confidence=confidence,
            trace=False,
        )
        dev_g = max(fitequal["deviance"] - deviance0, 0.0)
        group_p = _pchisq_upper(dev_g, num_group - 1)
        out["test.difference"] = np.array([dev_g, group_p, float(num_group - 1)], dtype=float)

    if test_unit_slope:
        if math.isnan(fisher_logdose):
            fisher_logdose = 0.0
        if fisher_logdose > 1e-15:
            if num_group > 1:
                x_design, x_names = _design_group_logdose(group_codes, group_levels, dose)
            else:
                x_design, x_names = _design_logdose(dose)
            fit_slope = _glm_binomial_cloglog(x_design, y, weights=tested)
            fit_slope["names"] = x_names
            coef_tab = _summary_coef_se(fit_slope, x_design, x_names)
            est_slope, se_slope = coef_tab["log(dose)"]
            z_wald = (est_slope - 1.0) / se_slope
            p_wald = 2.0 * _pnorm_scalar(-abs(z_wald))
            out["test.slope.wald"] = np.array(
                [est_slope, se_slope, z_wald, p_wald], dtype=float
            )

            dev = max(deviance0 - fit_slope["deviance"], 0.0)
            z_lr = math.sqrt(dev) * math.copysign(1.0, z_wald)
            p_lr = _pchisq_upper(dev, 1.0)
            out["test.slope.lr"] = np.array([math.nan, math.nan, z_lr, p_lr], dtype=float)

            z_score_logdose = dloglik_logdose / math.sqrt(fisher_logdose)
            p_score_logdose = 2.0 * _pnorm_scalar(-abs(z_score_logdose))
            z_score_dose = dloglik_dose / math.sqrt(fisher_dose)
            p_score_dose = 2.0 * _pnorm_scalar(-abs(z_score_dose))
            out["test.slope.score.logdose"] = np.array(
                [math.nan, math.nan, z_score_logdose, p_score_logdose], dtype=float
            )
            out["test.slope.score.dose"] = np.array(
                [math.nan, math.nan, z_score_dose, p_score_dose], dtype=float
            )
        else:
            na4 = np.array([math.nan, math.nan, math.nan, 1.0], dtype=float)
            out["test.slope.wald"] = na4.copy()
            out["test.slope.lr"] = na4.copy()
            out["test.slope.score.logdose"] = na4.copy()
            out["test.slope.score.dose"] = na4.copy()

    return out
