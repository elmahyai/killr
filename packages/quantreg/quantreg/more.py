"""Predictions, multi-tau likelihood, Hill and Pickands tails, and two small fits."""

from __future__ import annotations

import math

import numpy as np

from quantreg.fit import rq_fit
from quantreg.likelihood import aic_rq
from quantreg.model import model_matrix, rq


def predict_rqs(object, newdata=None):
    """Fitted values at every tau, or X %*% coefficients for a new column dictionary."""
    coefficient = np.asarray(object["coefficients"], dtype=float)
    if newdata is None:
        return np.asarray(object["fitted.values"], dtype=float)
    spec = object["terms"]
    design, _response, _names = model_matrix(spec, newdata)
    return design @ coefficient


def lasso_lambda_hat(x, r=1000, tau=0.5, c=1.0, alpha=0.95):
    """Belloni-Chernozhukov lambda. Uniform draws are R's runif, in column order."""
    from boot.rng import unif

    from quantreg.orderstats import kuantile

    design = np.asarray(x, dtype=float)
    n, _p = design.shape
    replicates = int(r)
    tau = float(tau)
    draws = np.array([unif() for _ in range(n * replicates)])
    uniform = draws.reshape((n, replicates), order="F")
    scale = np.mean(design ** 2, axis=0)
    score = (design.T @ (tau - (uniform < tau))) / scale[:, None]
    biggest = np.max(np.abs(score), axis=0)
    cutoff = float(kuantile(biggest, [1.0 - alpha])["y"][0])
    return float(c) * cutoff * scale


def summary_pickands(object, se="boot", b=200, ci=0.9):
    """Parametric bootstrap for the Pickands exponent. Draws are R's rexp."""
    from quantreg.orderstats import kuantile

    del se
    tau = float(object["tau"])
    xi = float(object["xi"])
    m = float(object["m"])
    design = np.asarray(object["F"]["x"], dtype=float)
    response = np.asarray(object["F"]["y"], dtype=float).reshape(-1)
    coefficient = np.asarray(object["F"]["coef"], dtype=float)
    b1 = coefficient[:, 0]
    bm = coefficient[:, 1]
    xbar = design.mean(axis=0)
    direction = design @ (bm - b1) / float(xbar @ (bm - b1))
    replicates = np.empty(int(b))
    for i in range(int(b)):
        draws = np.array([_rexp() for _ in range(response.size)])
        simulated = -((draws ** (-xi)) - 1.0) / xi * direction
        replicates[i] = pickands_fit(design, simulated, tau, m=m)["xi"]
    shifted = replicates - xi
    finite = np.isfinite(replicates)
    probs = [0.5, (1.0 + ci) / 2.0, (1.0 - ci) / 2.0]
    quantiles = [float(kuantile(shifted[finite], [prob])["y"][0]) for prob in probs]
    table = np.array(
        [
            xi,
            xi - quantiles[0],
            xi - quantiles[1],
            xi - quantiles[2],
            float(np.sqrt(np.var(replicates[finite], ddof=1))),
            int(b) - int(np.sum(~finite)),
        ]
    )
    return {"z": table, "tau": tau, "class": "summary.Pickands"}


def print_pickands(x):
    return float(x["xi"])


def print_summary_pickands(x):
    return np.asarray(x["z"], dtype=float)[:5]


def predict_rq(object, newdata=None):
    """Fitted values, or X %*% coefficients for a new column dictionary."""
    if newdata is None:
        return np.asarray(object["fitted.values"], dtype=float).reshape(-1)
    spec = object["terms"]
    design, _response, _names = model_matrix(spec, newdata)
    coefficient = np.asarray(object["coefficients"], dtype=float)
    if coefficient.ndim == 2:
        return design @ coefficient
    return design @ coefficient


def log_lik_rqs(object):
    """One Gaussian log likelihood per tau. df is the number of coefficients."""
    residual = np.asarray(object["residuals"], dtype=float)
    coefficient = np.asarray(object["coefficients"], dtype=float)
    n = residual.shape[0]
    p = coefficient.shape[0]
    taus = np.atleast_1d(np.asarray(object["tau"], dtype=float))
    fidelity = np.atleast_1d(np.asarray(object["rho"], dtype=float))
    value = n * (np.log(taus * (1.0 - taus)) - 1.0 - np.log(fidelity / n))
    return {"value": value, "n": n, "df": p}


def aic_rqs(object, k=2):
    """AIC of logLik.rqs. k <= 0 uses log(n)."""
    likelihood = log_lik_rqs(object)
    penalty = float(k)
    if penalty <= 0:
        penalty = math.log(likelihood["n"])
    value = -2.0 * likelihood["value"] + penalty * likelihood["df"]
    return {"value": value, "edf": likelihood["df"]}


def hill_fit(x, y, tau):
    """Hill tail exponent from one quantile fit."""
    design = np.asarray(x, dtype=float)
    response = np.asarray(y, dtype=float).reshape(-1)
    tau = float(tau)
    if tau > 0.5:
        design = -design
        response = -response
        tau = 1.0 - tau
    fit = rq_fit(design, response, tau=tau)
    fitted = fit["fitted.values"]
    ratio = np.where(response <= fitted, np.abs(response / fitted), 1.0)
    logged = np.log(ratio)
    logged = logged[np.isfinite(logged)]
    return {"xi": float(np.sum(logged) / (logged.size * tau)), "tau": tau, "F": fit, "class": "Hill"}


def hill(formula, tau=0.1, data=None):
    """Hill estimator from a formula. The design includes the intercept R would add."""
    return _tail(formula, tau, data, flavor="Hill")


def pickands_fit(x, y, tau, m=2):
    """Pickands tail exponent from three quantile fits."""
    design = np.asarray(x, dtype=float)
    response = np.asarray(y, dtype=float).reshape(-1)
    tau = float(tau)
    m = float(m)
    if tau > 0.5:
        design = -design
        response = -response
        tau = 1.0 - tau
    taus = [tau, m * tau, 2 * m * tau]
    fits = [rq_fit(design, response, tau=value) for value in taus]
    coefficient = np.column_stack([fit["coefficients"] for fit in fits])
    xbar = design.mean(axis=0)
    num = float(xbar @ (coefficient[:, 2] - coefficient[:, 1]))
    denom = float(xbar @ (coefficient[:, 1] - coefficient[:, 0]))
    xi = (-1.0 / math.log(m)) * math.log(num / denom)
    return {"xi": xi, "tau": tau, "m": m, "F": {"coef": coefficient, "x": design, "y": response}, "class": "Pickands"}


def pickands(formula, tau=0.1, data=None, m=2):
    return _tail(formula, tau, data, flavor="Pickands", m=m)


def pareto_test(formula, tau=0.1, data=None, flavor="Hill", m=2, b=200, ci=0.9):
    """Hill or Pickands, then the bootstrap summary. B is the bootstrap size."""
    if flavor == "Hill":
        fitted = hill(formula, tau, data)
        return summary_hill(fitted, b=b, m=m, ci=ci)
    if flavor == "Pickands":
        fitted = pickands(formula, tau, data, m=m)
        raise NotImplementedError("Pickands bootstrap summary is still open")
    raise RuntimeError(f"flavor {flavor} not (yet) implemented")


def _tail(formula, tau, data, flavor, m=2):
    from quantreg.model import parse_formula

    spec = parse_formula(formula)
    # Hill() uses model.matrix(formula), which includes an intercept unless -1 is present.
    design, response, _names = model_matrix(spec, data)
    if flavor == "Hill":
        return hill_fit(design, response, tau)
    return pickands_fit(design, response, tau, m=m)


_EXP_Q = (
    0.6931471805599453,
    0.9333736875190459,
    0.9888777961838675,
    0.9984959252914960,
    0.9998292811061389,
    0.9999833164100727,
    0.9999985691438767,
    0.9999998906925558,
    0.9999999924734159,
    0.9999999995283275,
    0.9999999999728814,
    0.9999999999985598,
    0.9999999999999289,
    0.9999999999999968,
    0.9999999999999999,
    1.0000000000000000,
)


def _rexp():
    """One draw from R's exp_rand, using boot's unif_rand."""
    from boot.rng import unif

    a = 0.0
    u = unif()
    while u <= 0.0 or u >= 1.0:
        u = unif()
    while True:
        u += u
        if u > 1.0:
            break
        a += _EXP_Q[0]
    u -= 1.0
    if u <= _EXP_Q[0]:
        return a + u
    i = 0
    ustar = unif()
    umin = ustar
    while u > _EXP_Q[i]:
        ustar = unif()
        if umin > ustar:
            umin = ustar
        i += 1
    return a + umin * _EXP_Q[0]


def summary_hill(object, se="boot", b=200, m=2, ci=0.9):
    """Parametric bootstrap for the Hill exponent. Draws are R's rexp."""
    from quantreg.orderstats import kuantile

    tau = float(object["tau"])
    xi = float(object["xi"])
    design = np.asarray(object["F"]["x"], dtype=float)
    response = np.asarray(object["F"]["y"], dtype=float).reshape(-1)
    b0 = np.asarray(object["F"]["coefficients"], dtype=float).reshape(-1)
    bm = rq_fit(design, response, tau=m * tau)["coefficients"]
    xbar = design.mean(axis=0)
    direction = design @ (bm - b0) / float(xbar @ (bm - b0))
    replicates = np.empty(int(b))
    for i in range(int(b)):
        draws = np.array([_rexp() for _ in range(response.size)])
        simulated = -((draws ** (-xi)) - 1.0) / xi * direction
        replicates[i] = hill_fit(design, simulated, tau)["xi"]
    shifted = replicates - xi
    probs = [0.5, (1.0 + ci) / 2.0, (1.0 - ci) / 2.0]
    quantiles = [float(kuantile(shifted, [prob])["y"][0]) for prob in probs]
    table = np.array(
        [
            xi,
            xi - quantiles[0],
            xi - quantiles[1],
            xi - quantiles[2],
            float(np.sqrt(np.var(replicates, ddof=1))),
            int(b) - int(np.sum(~np.isfinite(replicates))),
        ]
    )
    return {"z": table, "tau": tau, "class": "summary.Hill"}


def print_summary_hill(x):
    """The five printed numbers from print.summary.Hill. The header is text."""
    return np.asarray(x["z"], dtype=float)[:5]


def print_hill(x):
    return str(x["xi"])


def lprq(x, y, h, tau=0.5, m=50):
    """Local linear quantile regression on m points from min(x) to max(x)."""
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    grid = np.linspace(x.min(), x.max(), int(m))
    fitted = np.empty(grid.size)
    slope = np.empty(grid.size)
    for i, center in enumerate(grid):
        z = x - center
        weight = norm_density(z / h)
        fit = rq_fit(np.column_stack([np.ones(y.size), z]) * weight[:, None], y * weight, tau=tau)
        # rq.wfit multiplies x and y by the weights, then rq.fit.br.
        # lprq calls rq(..., weights=wx), which is rq.wfit. The coefficient
        # is for the weighted design, and coef[1] is the intercept of y ~ z.
        fitted[i] = fit["coefficients"][0]
        slope[i] = fit["coefficients"][1]
    return {"xx": grid, "fv": fitted, "dv": slope}


def norm_density(z):
    from scipy.stats import norm

    return norm.pdf(z)


def lm_fit_recursive(x, y, intercept=True):
    """Recursive least squares. The first p rows initialize the QR solution."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    if intercept:
        design = np.column_stack([np.ones(design.shape[0]), design])
    n, p = design.shape
    square = design[:p, :]
    try:
        factor = np.linalg.inv(square)
    except np.linalg.LinAlgError:
        factor = np.linalg.pinv(square)
    gram = factor @ factor.T
    beta = np.zeros((p, n))
    try:
        beta[:, p - 1] = np.linalg.solve(square, response[:p])
    except np.linalg.LinAlgError:
        beta[:, p - 1] = np.linalg.lstsq(square, response[:p], rcond=None)[0]
    for i in range(p, n):
        row = design[i, :]
        ax = gram @ row
        f = 1.0 + float(row @ ax)
        residual = (response[i] - float(row @ beta[:, i - 1])) / f
        beta[:, i] = beta[:, i - 1] + residual * ax
        gram = gram - np.outer(ax, ax) / f
    return beta


def akj(x, z=None, p=None, h=-1, alpha=0.5, kappa=0.9, iker1=0):
    """Adaptive kernel density, the sakj Fortran routine.

    R sorts x and leaves p in the original order. A check that passes a
    sorted x keeps p aligned with x.
    """
    values = np.sort(np.asarray(x, dtype=float).reshape(-1))
    if p is None:
        p = np.full(values.size, 1.0 / values.size)
    p = np.asarray(p, dtype=float).reshape(-1)
    if p.size != values.size:
        raise ValueError("length(p) must equal length(x)")
    kernel = int(iker1)
    if kernel not in (0, 1):
        raise ValueError("iker1 must be 0 or 1")
    if z is None:
        z = np.linspace(float(values.min()), float(values.max()), 2 * values.size)
    z = np.asarray(z, dtype=float).reshape(-1)
    pi = 3.141593
    con1 = 1.0 / math.sqrt(2.0 * pi) if kernel == 0 else 1.0 / pi
    bandwidth = float(h)
    if bandwidth <= 0:
        mean = float(np.sum(values * p))
        second = float(np.sum(values * values * p))
        xsd = math.sqrt(second - mean * mean)
        total = 0.0
        qrange = 0.0
        for i in range(values.size - 1):
            total += p[i]
            if total >= 0.25:
                qrange = values[i]
                break
        total = 1.0
        for i in range(values.size - 1, -1, -1):
            total -= p[i]
            if total <= 0.75:
                qrange = values[i] - qrange
                break
        # sakj.f writes 1.34 as a single-precision literal (REAL*4), so use its float32 value.
        a = min(xsd, qrange / float(np.float32(1.34)))
        bandwidth = kappa * a / (values.size ** 0.2)
    hinv = 1.0 / bandwidth
    xlam = np.zeros(values.size)
    for j in range(values.size):
        if kernel == 0:
            xponen = 0.5 * ((values[j] - values) * hinv) ** 2
            xker = np.sum(p * np.exp(-xponen) * hinv)
        else:
            xponen = (values[j] - values) * hinv
            xker = np.sum(p * hinv / (1.0 + xponen ** 2))
        xlam[j] = con1 * xker
    g = math.exp(float(np.sum(p * np.log(xlam))))
    # sakj.f never declares g or ginv, so Fortran implicit typing makes them REAL*4.
    # Round them to float32 here, or xlam differs from R by up to about 1e-8.
    g32 = float(np.float32(g))
    ginv32 = float(np.float32(1.0 / g32))
    xlam = hinv / ((xlam * ginv32) ** (-alpha))
    dens = np.zeros(z.size)
    psi = np.zeros(z.size)
    score = np.zeros(z.size)
    for j, point in enumerate(z):
        xponen = (point - values) * xlam
        if kernel == 0:
            fact = np.exp(-0.5 * xponen * xponen) * xlam
            xker = float(np.sum(p * fact))
            dxker = float(np.sum(-p * fact * xponen * xlam))
            ddxker = float(np.sum(-p * fact * (1.0 - xponen ** 2) * xlam ** 2))
        else:
            fact = xlam / (1.0 + xponen ** 2)
            xker = float(np.sum(p * fact))
            dxker = float(np.sum(-p * 2.0 * xponen * fact ** 2))
            ddxker = float(np.sum(-p * 2.0 * (fact ** 2) * (xlam - 4.0 * (xponen ** 2) * fact)))
        dens[j] = con1 * xker
        psi[j] = -(dxker / xker)
        score[j] = (dxker / xker) ** 2 - ddxker / xker
    return {"dens": dens, "psi": psi, "score": score, "h": bandwidth}
