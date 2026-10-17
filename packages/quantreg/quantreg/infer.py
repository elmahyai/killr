"""Standard errors and printed summaries for a fitted rq object."""

from __future__ import annotations

import math

import numpy as np
from scipy.stats import norm, t

from quantreg.bandwidth import bandwidth_rq
from quantreg.fit import rq_fit


def _inv_gram(design):
    """(A'A)^{-1} from the R backsolve(qr(A)$qr) product."""
    _q, r = np.linalg.qr(np.asarray(design, dtype=float), mode="reduced")
    solved = np.linalg.solve(r, np.eye(r.shape[0]))
    return solved @ solved.T


def summary_rq(object, se="nid", covariance=False, hs=True, R=200):
    """Standard errors for a fitted rq object. se is iid, nid, ker, or boot.

    The default in R for n < 1001 is the rank-inversion interval from the
    simplex. That interval is still the Fortran path, so this translation
    requires se to be one of the sandwich or bootstrap methods. boot is the
    xy-pair bootstrap with R replicates, as summary.rq calls boot.rq.

    The result carries x, y, and the model frame (model) of the fit, as R reads
    them from the model frame in plot.summary.rqs. x and y are not weighted.
    """
    if object.get("method") == "lasso":
        raise RuntimeError("no inference for lasso'd rq fitting: try rqss (if brave, or credulous)")
    if se in (None, "rank"):
        raise NotImplementedError("rank inversion intervals are still the simplex confidence interval")
    if se in ("BLB", "extreme", "conquer"):
        raise NotImplementedError(f"summary se={se!r} is still open")
    design = np.asarray(object["x"], dtype=float)
    response = np.asarray(object["y"], dtype=float).reshape(-1)
    unweighted_x = design
    unweighted_y = response
    names = list(object.get("names") or [f"x{i + 1}" for i in range(design.shape[1])])
    residual = np.asarray(object["residuals"], dtype=float).reshape(-1)
    coefficient = np.asarray(object["coefficients"], dtype=float)
    if coefficient.ndim == 2:
        coefficient = coefficient[:, 0]
        residual = residual[:, 0] if residual.ndim == 2 else residual
    tau = float(np.atleast_1d(object["tau"])[0])
    weight = object.get("weights")
    if weight is not None:
        weight = np.asarray(weight, dtype=float).reshape(-1)
        residual = residual * weight
        design = design * weight[:, None]
        response = response * weight
    n, p = design.shape
    rdf = n - p
    eps = math.sqrt(np.finfo(float).eps)
    if se == "iid":
        gram = _inv_gram(design)
        pz = int(np.sum(np.abs(residual) < eps))
        bandwidth = max(p + 1, math.ceil(n * bandwidth_rq(tau, n, hs=hs)))
        order = np.argsort(np.abs(residual), kind="mergesort")
        chosen = residual[order][pz : pz + bandwidth + 1]
        ordered = np.sort(chosen)
        xt = np.arange(pz + 1, pz + bandwidth + 2) / (n - p)
        slope = rq_fit(np.column_stack([np.ones(ordered.size), xt]), ordered, tau=0.5)["coefficients"][1]
        scale = 1.0 / slope
        cov = (slope ** 2) * gram * tau * (1.0 - tau)
        serr = np.sqrt(np.diag(cov))
        fxxinv = None
    elif se == "nid":
        bandwidth = bandwidth_rq(tau, n, hs=hs)
        while (tau - bandwidth < 0) or (tau + bandwidth > 1):
            bandwidth /= 2
        method = object.get("method") or "br"
        high = rq_fit(design, response, tau=tau + bandwidth, method=method)["coefficients"]
        low = rq_fit(design, response, tau=tau - bandwidth, method=method)["coefficients"]
        dyhat = design @ (high - low)
        if np.any(dyhat <= 0):
            import warnings

            warnings.warn(f"{int(np.sum(dyhat <= 0))} non-positive fis", stacklevel=2)
        density = np.maximum(0.0, (2 * bandwidth) / (dyhat - eps))
        weighted = np.sqrt(density)[:, None] * design
        fxxinv = _inv_gram(weighted)
        xx = design.T @ design
        cov = tau * (1.0 - tau) * fxxinv @ xx @ fxxinv
        scale = float(np.mean(density))
        serr = np.sqrt(np.diag(cov))
    elif se == "ker":
        bandwidth = bandwidth_rq(tau, n, hs=hs)
        while (tau - bandwidth < 0) or (tau + bandwidth > 1):
            bandwidth /= 2
        uhat = response - design @ coefficient
        iqr = np.quantile(uhat, 0.75) - np.quantile(uhat, 0.25)
        bandwidth = (float(norm.ppf(tau + bandwidth)) - float(norm.ppf(tau - bandwidth))) * min(
            math.sqrt(float(np.var(uhat, ddof=1))), iqr / 1.34
        )
        density = norm.pdf(uhat / bandwidth) / bandwidth
        weighted = np.sqrt(density)[:, None] * design
        fxxinv = _inv_gram(weighted)
        cov = tau * (1.0 - tau) * fxxinv @ (design.T @ design) @ fxxinv
        scale = float(np.mean(density))
        serr = np.sqrt(np.diag(cov))
    elif se == "boot":
        from quantreg.boot import boot_rq

        bootstrap = boot_rq(design, response, tau=tau, r=int(R), bsmethod="xy")
        cov = np.atleast_2d(np.cov(np.asarray(bootstrap["B"], dtype=float), rowvar=False))
        serr = np.sqrt(np.diag(cov))
        scale = None
        fxxinv = None
    else:
        raise ValueError(f"unknown se {se}")
    table = np.column_stack(
        [
            coefficient,
            serr,
            coefficient / serr,
            2.0 * (1.0 - t.cdf(np.abs(coefficient / serr), rdf)) if rdf > 0 else np.full(p, np.nan),
        ]
    )
    result = {
        "call": object.get("call"),
        "terms": object.get("terms"),
        "coefficients": table,
        "names": names,
        "columns": ["Value", "Std. Error", "t value", "Pr(>|t|)"],
        "residuals": residual,
        "rdf": rdf,
        "tau": tau,
        "class": "summary.rq",
        "x": unweighted_x,
        "y": unweighted_y,
        "model": object.get("model"),
    }
    if covariance:
        result["cov"] = cov
        if scale is not None:
            result["scale"] = scale
        if se in ("nid", "ker"):
            result["Hinv"] = fxxinv
            result["J"] = design.T @ design
        elif se == "boot":
            result["B"] = np.asarray(bootstrap["B"], dtype=float)
            result["U"] = bootstrap["U"]
    return result


def _format_named(values, names, digits=7):
    text = [f"{value:.{digits}g}" for value in values]
    width = max([len(name) for name in names] + [len(item) for item in text])
    name_line = " ".join(name.rjust(width) for name in names)
    value_line = " ".join(item.rjust(width) for item in text)
    return name_line + "\n" + value_line


def print_rqs(x):
    """Coefficients at every tau, then the observation count and residual degrees of freedom."""
    coefficient = np.asarray(x["coefficients"], dtype=float)
    nobs = np.asarray(x["residuals"]).shape[0]
    rdf = nobs - coefficient.shape[0]
    return np.concatenate([coefficient.ravel(order="F"), [nobs, rdf]])


def print_summary_rqs(x):
    """The coefficient tables from each tau, stacked in the order R prints them."""
    tables = [np.asarray(piece["coefficients"], dtype=float).ravel(order="F") for piece in x]
    return np.concatenate(tables)


def print_rq(x):
    """The print.rq text. The function also returns the fit, as R does."""
    lines = []
    if x.get("call"):
        lines.append("Call:")
        lines.append(x["call"])
    lines.append("")
    lines.append("Coefficients:")
    coefficient = np.asarray(x["coefficients"], dtype=float)
    names = list(x.get("names") or [])
    if coefficient.ndim == 1:
        lines.append(_format_named(coefficient, names or [str(i) for i in range(coefficient.size)]))
        p = coefficient.size
        nobs = np.asarray(x["residuals"]).shape[0]
    else:
        p = coefficient.shape[0]
        nobs = np.asarray(x["residuals"]).shape[0]
        lines.append(str(coefficient))
    rdf = nobs - p
    lines.append("")
    lines.append(f"Degrees of freedom: {nobs} total; {rdf} residual")
    return "\n".join(lines)


def print_summary_rq(x, digits=5):
    """print.summary.rq at the default digits, which is max(5, getOption('digits') - 2)."""
    tau = np.round(float(x["tau"]), digits)
    header = ["Value", "Std. Error", "t value", "Pr(>|t|)"]
    table = np.round(np.asarray(x["coefficients"], dtype=float), digits)
    names = list(x["names"])
    widths = [max(len(header[j]), max(len(f"{table[i, j]:.5f}") for i in range(table.shape[0]))) for j in range(4)]
    name_width = max(len(name) for name in names)
    lines = ["", f"Call: {x.get('call')}", "", f"tau: {tau}", "", "Coefficients:"]
    lines.append(" " * (name_width + 1) + " ".join(title.ljust(widths[j]) for j, title in enumerate(header)))
    for i, name in enumerate(names):
        cells = " ".join(f"{table[i, j]:.5f}".rjust(widths[j]) for j in range(4))
        lines.append(name.ljust(name_width) + " " + cells)
    return "\n".join(lines)
