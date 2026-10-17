"""Single-group extreme limiting dilution analysis.

Translated from statmod 1.5.2 ``eldaOneGroup`` in ``R/elda.R``.
"""

from __future__ import annotations

import math
import warnings

import numpy as np

from statmod.digamma import _make_link, _qnorm_scalar

_DBL_EPS = float(np.finfo(np.float64).eps)


def _limdil_allpos(tested, dose, confidence, observed):
    """One-sided interval when all assays are positive (``.limdil.allpos``)."""
    alpha = 1.0 - confidence
    dose = np.asarray(dose, dtype=float)
    tested = np.asarray(tested, dtype=float)
    dosem = float(np.min(dose))
    tested_sum = float(np.sum(tested[dose == dosem]))
    beta = math.log(-math.log(1.0 - alpha ** (1.0 / tested_sum))) - math.log(dosem)
    lambda_val = math.exp(beta)
    if observed:
        lambda_val = -math.expm1(lambda_val)
    while True:
        if observed:
            one_minus = (1.0 - lambda_val) ** dose
            f_val = float(np.sum(tested * np.log(1.0 - one_minus))) - math.log(alpha)
            deriv = float(
                np.sum(
                    tested
                    * (-dose)
                    * (1.0 - lambda_val) ** (dose - 1.0)
                    / (1.0 - one_minus)
                )
            )
        else:
            exp_term = np.exp(-dose * lambda_val)
            f_val = float(np.sum(tested * np.log(1.0 - exp_term))) - math.log(alpha)
            deriv = float(
                np.sum(tested * dose * exp_term / (1.0 - exp_term))
            )
        step = f_val / deriv
        lambda_val = lambda_val - step
        if -step < 1e-6:
            break
    return lambda_val


def _binom_dev_resids(y, mu, wt):
    """Binomial deviance residuals matching ``stats`` ``binomial()$dev.resids``."""
    y = np.asarray(y, dtype=float)
    mu = np.asarray(mu, dtype=float)
    wt = np.asarray(wt, dtype=float)
    mu = np.minimum(np.maximum(mu, _DBL_EPS), 1.0 - _DBL_EPS)
    y = np.minimum(np.maximum(y, 0.0), 1.0)
    term1 = np.where(y == 0.0, 0.0, y * np.log(y / mu))
    term2 = np.where(y == 1.0, 0.0, (1.0 - y) * np.log((1.0 - y) / (1.0 - mu)))
    return 2.0 * wt * (term1 + term2)


def elda_one_group(
    response,
    dose,
    tested,
    observed=False,
    confidence=0.95,
    tol=1e-8,
    maxit=100,
    trace=False,
):
    """Estimate active cell frequency from LDA data for one group."""
    y = np.asarray(response, dtype=float)
    n = np.asarray(tested, dtype=float)
    d = np.asarray(dose, dtype=float)
    phat = y / n

    if np.all(y < 1e-14):
        total_n = float(np.sum(d * n))
        size = 1.0 - confidence
        if observed:
            upper_u = 1.0 - size ** (1.0 / total_n)
        else:
            upper_u = -math.log(size) / total_n
        return {
            "CI.frequency": np.array([math.inf, math.inf, 1.0 / upper_u], dtype=float),
            "deviance": 0.0,
            "dloglik.logdose": 0.0,
            "FisherInfo.logdose": 0.0,
            "dloglik.dose": 0.0,
            "FisherInfo.dose": 0.0,
        }

    if np.all(phat > 1.0 - 1e-14):
        upper_u = _limdil_allpos(n, d, confidence, observed)
        return {
            "CI.frequency": np.array([1.0 / upper_u, 1.0, 1.0], dtype=float),
            "deviance": 0.0,
            "dloglik.logdose": 0.0,
            "FisherInfo.logdose": 0.0,
            "dloglik.dose": 0.0,
            "FisherInfo.dose": 0.0,
        }

    _, cloglog = _make_link("cloglog")
    mu_eta = cloglog["mu.eta"]

    pmean = float(np.mean(y) / np.mean(n))
    lambda_val = -math.log1p(-pmean) / float(np.max(d))
    if trace:
        print(0, lambda_val, 1.0 / lambda_val)

    iter_count = 0
    while True:
        iter_count += 1
        if iter_count > maxit:
            warnings.warn("max iterations exceeded", RuntimeWarning, stacklevel=2)
            break
        p = -np.expm1(-lambda_val * d)
        onemp = np.exp(-lambda_val * d)
        dloglik_lambda = float(np.mean(n * d * (phat - p) / p))
        d2loglik_lambda = float(-np.mean(n * phat * d * d * onemp / p / p))
        step = dloglik_lambda / d2loglik_lambda
        lambda_val = lambda_val - step
        if trace:
            print(iter_count, lambda_val, 1.0 / lambda_val, step)
        if abs(step) < tol:
            break

    alpha = math.log(lambda_val)
    p = -np.expm1(-lambda_val * d)
    onemp = np.exp(-lambda_val * d)
    fisher_info_alpha = float(np.sum(n * d * d * onemp / p) * lambda_val**2)
    se_alpha = 1.0 / math.sqrt(fisher_info_alpha)
    p_tail = (1.0 - confidence) / 2.0
    z_crit = _qnorm_scalar(1.0 - p_tail)
    ci_alpha = np.array(
        [alpha - z_crit * se_alpha, alpha, alpha + z_crit * se_alpha],
        dtype=float,
    )

    if observed:
        ci_frequency = -1.0 / np.expm1(-np.exp(ci_alpha))
    else:
        ci_frequency = np.exp(-ci_alpha)

    deviance = float(np.sum(_binom_dev_resids(phat, p, n)))

    v = p * onemp / n
    x_log = np.log(d)
    eta = alpha + x_log
    mu_eta_val = mu_eta(eta)
    info_alpha = mu_eta_val**2 / v
    xmean = float(np.sum(x_log * info_alpha) / np.sum(info_alpha))
    mu_beta = (x_log - xmean) * mu_eta_val
    dloglik_beta = float(np.sum(mu_beta * (phat - p) / v))
    fisher_info_beta = float(np.sum(mu_beta**2 / v))
    z_scoretest = dloglik_beta / math.sqrt(fisher_info_beta)

    x_dose = d
    xmean_dose = float(np.sum(x_dose * info_alpha) / np.sum(info_alpha))
    mu_beta_dose = (x_dose - xmean_dose) * mu_eta_val
    dloglik_beta_dose = float(np.sum(mu_beta_dose * (phat - p) / v))
    fisher_info_beta_dose = float(np.sum(mu_beta_dose**2 / v))
    z_scoretest_dose = dloglik_beta_dose / math.sqrt(fisher_info_beta_dose)

    return {
        "p": p,
        "lambda": lambda_val,
        "alpha": alpha,
        "CI.alpha": ci_alpha,
        "CI.frequency": ci_frequency,
        "deviance": deviance,
        "iter": iter_count,
        "z.scoretest": z_scoretest,
        "z.scoretest.dose": z_scoretest_dose,
        "dloglik.logdose": dloglik_beta,
        "FisherInfo.logdose": fisher_info_beta,
        "dloglik.dose": dloglik_beta_dose,
        "FisherInfo.dose": fisher_info_beta_dose,
    }
