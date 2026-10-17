"""Summaries, the joint Wald test, and the tau-score rank test."""

from __future__ import annotations

import warnings

import numpy as np
from scipy.stats import ncf, ncx2

from quantreg.bandwidth import bandwidth_rq
from quantreg.fit import rq_fit_br
from quantreg.infer import summary_rq

_EPS = 2.220446049250313e-16 ** (2.0 / 3.0)


def print_anova_rq(x):
    """The numeric anova table: degrees of freedom, F, and the p-value."""
    pieces = [
        np.atleast_1d(np.asarray(x[name], dtype=float)).reshape(-1)
        for name in ("ndf", "ddf", "Tn", "pvalue")
    ]
    return np.concatenate(pieces)


def anova_rq(object, *others, test="Wald", se="nid", iid=True):
    """anova.rq on one fit is refused. Several fits are compared by anova.rqlist."""
    if others:
        return anova_rqlist((object, *others), test=test, se=se, iid=iid)
    raise RuntimeError("Anova is only defined (yet) for lists of rq objects")


def _response_name(fit):
    formula = str(fit.get("formula") or "")
    if "~" not in formula:
        raise ValueError("anova needs a formula")
    return formula.split("~", 1)[0].replace(" ", "")


def anova_rqlist(object, test="Wald", se="nid", iid=True):
    """Compare nested rq fits that share a tau.

    Wald uses the nid, iid, or ker covariance. The rank test uses the tau score.
    Fits at different taus are the joint test in anova.rqs.
    """
    fits = [dict(item) for item in object]
    if len(fits) < 2:
        raise RuntimeError("Anova is only defined (yet) for lists of rq objects")
    responses = [_response_name(fit) for fit in fits]
    if any(name != responses[0] for name in responses):
        raise ValueError("Models don't all have the same response variable")
    fits.sort(key=lambda fit: np.asarray(fit["coefficients"]).reshape(-1).size, reverse=True)
    taus = [float(np.atleast_1d(fit["tau"])[0]) for fit in fits]
    if any(abs(tau - taus[0]) > 1e-12 for tau in taus):
        raise NotImplementedError("anova of separate fits at different taus is still open")
    if test not in {"Wald", "rank"}:
        raise NotImplementedError(f"anova test {test} is still open")
    n = np.asarray(fits[0]["residuals"]).reshape(-1).size
    names = [list(fit["names"]) for fit in fits]
    rows = []
    if test == "Wald":
        summaries = [summary_rq(fit, se=se, covariance=True) for fit in fits]
        full_names = summaries[0]["names"]
        full_coef = summaries[0]["coefficients"][:, 0]
        full_cov = summaries[0]["cov"]
        for summary, smaller in zip(summaries[1:], names[1:]):
            del summary
            if any(name not in full_names for name in smaller):
                raise ValueError("Models aren't nested")
            missing = np.array([name not in smaller for name in full_names])
            ndf = int(np.sum(missing))
            contrast = full_coef[missing]
            variance = full_cov[np.ix_(missing, missing)]
            tn = float(contrast @ np.linalg.solve(variance, contrast) / ndf)
            ddf = n - len(full_names)
            rows.append((ndf, ddf, tn, float(1.0 - ncf.cdf(tn, ndf, ddf, 0.0))))
    else:
        full = fits[0]
        full_design = np.asarray(full["x"], dtype=float)
        response = np.asarray(full["y"], dtype=float).reshape(-1)
        for fit, smaller in zip(fits[1:], names[1:]):
            if any(name not in names[0] for name in smaller):
                raise ValueError("Models aren't nested")
            missing = np.array([name not in smaller for name in names[0]])
            result = rq_test_rank(
                np.asarray(fit["x"], dtype=float),
                full_design[:, missing],
                response,
                score="tau",
                tau=taus[0],
                iid=iid,
            )
            rows.append((result["ndf"], result["ddf"], result["Tn"], result["pvalue"]))
    table = np.array(rows, dtype=float)
    return {
        "ndf": table[:, 0],
        "ddf": table[:, 1],
        "Tn": table[:, 2],
        "pvalue": table[:, 3],
        "class": "anova.rq",
    }


def summary_rqs(object, se="nid", covariance=False, hs=True):
    """One summary.rq for each tau. se is passed through."""
    taus = np.atleast_1d(np.asarray(object["tau"], dtype=float))
    coefficient = np.asarray(object["coefficients"], dtype=float)
    residual = np.asarray(object["residuals"], dtype=float)
    rho = np.atleast_1d(np.asarray(object["rho"], dtype=float))
    pieces = []
    for i, tau in enumerate(taus):
        one = dict(object)
        one["coefficients"] = coefficient[:, i]
        one["residuals"] = residual[:, i]
        one["tau"] = float(tau)
        one["rho"] = float(rho[i])
        one["class"] = "rq"
        pieces.append(summary_rq(one, se=se, covariance=covariance, hs=hs))
    return pieces


def anova_rqs(object, se="nid", joint=True):
    """Joint Wald test that the slopes are the same at every tau.

    The models are the columns of one rqs fit, so the taus differ and the
    design is the same. Nested comparisons of different formulas are still open.
    """
    taus = np.atleast_1d(np.asarray(object["tau"], dtype=float))
    pieces = []
    coefficient = np.asarray(object["coefficients"], dtype=float)
    residual = np.asarray(object["residuals"], dtype=float)
    rho = np.atleast_1d(np.asarray(object["rho"], dtype=float))
    for i, tau in enumerate(taus):
        one = dict(object)
        one["coefficients"] = coefficient[:, i]
        one["residuals"] = residual[:, i]
        one["tau"] = float(tau)
        one["rho"] = float(rho[i])
        pieces.append(summary_rq(one, se=se, covariance=True))
    if np.unique(np.round(taus, 12)).size == 1:
        raise NotImplementedError("anova for equal taus needs nested formulas")
    names = list(object["names"])
    if names[0] != "(Intercept)":
        raise ValueError("Intercept required in common tau testing")
    omega = np.minimum(taus[:, None], taus[None, :]) - np.outer(taus, taus)
    j_matrix = pieces[0]["J"]
    p = j_matrix.shape[0]
    m = taus.size
    n = residual.shape[0]
    h_stack = np.stack([piece["Hinv"] for piece in pieces], axis=2)
    flat = h_stack.transpose(0, 2, 1).reshape((p * m, p), order="F")
    factor = flat @ np.linalg.cholesky(j_matrix)
    ones = np.ones((p, p))
    weight = np.kron(omega, ones)
    w_matrix = (factor @ factor.T) * weight
    values = np.concatenate([piece["coefficients"][:, 0] for piece in pieces])
    if joint:
        slope = np.column_stack([np.zeros(p - 1), np.eye(p - 1)])
        difference = np.diff(np.eye(m), axis=0)
        design = np.kron(difference, slope)
        ndf = (p - 1) * (m - 1)
        ddf = n * m - (p - 1) * (m - 1)
        transformed = design @ values
        middle = design @ w_matrix @ design.T
        tn = float(transformed @ np.linalg.solve(middle, transformed) / ndf)
        pvalue = float(1.0 - ncf.cdf(tn, ndf, ddf, 0.0))
        return {"ndf": ndf, "ddf": ddf, "Tn": tn, "pvalue": pvalue}
    tn = np.zeros(p - 1)
    pvalue = np.zeros(p - 1)
    ndf = m - 1
    ddf = n * m - (m - 1)
    for i in range(1, p):
        row = np.zeros((1, p))
        row[0, i] = 1.0
        design = np.kron(np.diff(np.eye(m), axis=0), row)
        transformed = (design @ values).reshape(-1)
        middle = design @ w_matrix @ design.T
        tn[i - 1] = float(transformed @ np.linalg.solve(middle, transformed) / ndf)
        pvalue[i - 1] = float(1.0 - ncf.cdf(tn[i - 1], ndf, ddf, 0.0))
    return {"ndf": ndf, "ddf": ddf, "Tn": tn, "pvalue": pvalue, "names": names[1:]}


def _qr_resid(x0, x1):
    q_factor, _r = np.linalg.qr(np.asarray(x0, dtype=float), mode="reduced")
    x1 = np.asarray(x1, dtype=float)
    return x1 - q_factor @ (q_factor.T @ x1)


def _weighted_resid(x0, x1, weight):
    """Residuals from R's lm.wfit. The weight enters as its square root."""
    x0 = np.asarray(x0, dtype=float)
    x1 = np.asarray(x1, dtype=float)
    scale = np.sqrt(np.asarray(weight, dtype=float)).reshape(-1, 1)
    q_factor, r_factor = np.linalg.qr(x0 * scale, mode="reduced")
    beta = np.linalg.solve(r_factor, q_factor.T @ (x1 * scale))
    return x1 - x0 @ beta


def rq_test_rank(x0, x1, y, score="tau", tau=0.5, iid=True, weights=None, omega=1.0, delta0=None, pvalue="F"):
    """Rank test of x1 given x0. Only the tau score is available.

    The tau score is the regression-quantile dual minus one minus tau.
    Wilcoxon and normal scores need the whole quantile process.
    """
    if score != "tau":
        raise NotImplementedError("rank scores other than tau need the full quantile process")
    x0 = np.asarray(x0, dtype=float)
    x1 = np.asarray(x1, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x0.ndim == 1:
        x0 = x0.reshape(-1, 1)
    if x1.ndim == 1:
        x1 = x1.reshape(-1, 1)
    if weights is not None and np.size(weights) > 0:
        weights = np.asarray(weights, dtype=float).reshape(-1)
        y = weights * y
        x0 = x0 * weights[:, None]
        x1 = x1 * weights[:, None]
    n = y.size
    tau = float(tau)
    fit = rq_fit_br(x0, y, tau=tau)
    ranks = np.asarray(fit["dual"], dtype=float).reshape(-1) - (1.0 - tau)
    a2 = tau * (1.0 - tau)
    if not iid:
        bandwidth = bandwidth_rq(tau, n, hs=True)
        high = rq_fit_br(x0, y, tau=tau + bandwidth)["coefficients"]
        low = rq_fit_br(x0, y, tau=tau - bandwidth)["coefficients"]
        change = (x0 @ (high - low)).reshape(-1)
        if np.any(change <= 0):
            share = 100.0 * np.sum(change <= 0) / n
            warnings.warn(f"{share} percent fis <=0", stacklevel=2)
        density = np.maximum(_EPS, (2.0 * bandwidth) / (change - _EPS))
        projected = _weighted_resid(x0, x1, density)
    else:
        projected = _qr_resid(x0, x1)
    statistic = projected.T @ ranks
    statistic = statistic.T @ np.linalg.solve(projected.T @ projected, statistic) / a2
    if delta0 is None:
        delta0 = np.zeros(x1.shape[1])
    delta0 = np.asarray(delta0, dtype=float).reshape(-1)
    ncp = (float(omega) ** 2) * float(delta0 @ ((projected.T @ projected) / n) @ delta0) / a2
    ndf = x1.shape[1]
    tn = float(np.asarray(statistic).reshape(-1)[0]) / ndf
    ddf = n - x0.shape[1] - x1.shape[1]
    if pvalue == "F":
        probability = float(1.0 - ncf.cdf(tn, ndf, ddf, ncp))
    else:
        probability = float(1.0 - ncx2.cdf(tn * ndf, ndf, ncp))
    return {"Tn": tn, "ndf": ndf, "ddf": ddf, "pvalue": probability}
