"""stats::glm.fit restricted to the binomial families ordinal uses for start values.

clm2's setStart() runs a logistic or probit regression on the middle cut
(clm2.R:174). Only the coefficients are consumed, but they have to match R
bit for bit, so the IRLS loop and the LINPACK QR below follow R's arithmetic:
dqrls is dqrdc2 plus dqrsl, and the deviance is the C binomial_dev_resids
accumulated the way R's sum() does.
"""

from __future__ import annotations

import math

import numpy as np

_DBL_EPS = np.finfo(float).eps


# ------------------------------------------------------------------ LINPACK


def _dnrm2(values) -> float:
    scale = 0.0
    ssq = 1.0
    for value in values:
        value = float(value)
        if value != 0.0:
            absxi = abs(value)
            if scale < absxi:
                ratio = scale / absxi
                ssq = 1.0 + ssq * ratio * ratio
                scale = absxi
            else:
                ratio = absxi / scale
                ssq = ssq + ratio * ratio
    return scale * math.sqrt(ssq)


def _ddot(left, right) -> float:
    total = 0.0
    for a, b in zip(left, right):
        total += float(a) * float(b)
    return total


def dqrdc2(x, tol: float) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    """LINPACK dqrdc2 on a copy of ``x``: returns (rank, qraux, pivot, qr).

    ``pivot`` is 0-based. Householder columns are stored in ``qr`` exactly as
    the Fortran leaves them.
    """
    qr = np.array(x, dtype=np.float64, copy=True)
    n, p = qr.shape
    qraux = [0.0] * p
    work1 = [0.0] * p
    work2 = [0.0] * p
    pivot = list(range(p))
    for j in range(p):
        qraux[j] = _dnrm2(qr[:, j])
        work1[j] = qraux[j]
        work2[j] = qraux[j] if qraux[j] != 0.0 else 1.0
    lup = min(n, p)
    k = p + 1
    for col in range(lup):
        while (col + 1) < k and qraux[col] < work2[col] * tol:
            block = qr[:, col:p].copy()
            qr[:, col : p - 1] = block[:, 1:]
            qr[:, p - 1] = block[:, 0]
            piv = pivot[col:p]
            pivot[col : p - 1] = piv[1:]
            pivot[p - 1] = piv[0]
            saved_q, saved_1, saved_2 = qraux[col], work1[col], work2[col]
            for j in range(col, p - 1):
                qraux[j] = qraux[j + 1]
                work1[j] = work1[j + 1]
                work2[j] = work2[j + 1]
            qraux[p - 1] = saved_q
            work1[p - 1] = saved_1
            work2[p - 1] = saved_2
            k -= 1
        if (col + 1) != n:
            nrmxl = _dnrm2(qr[col:, col])
            if nrmxl != 0.0:
                diag = float(qr[col, col])
                if diag != 0.0:
                    nrmxl = math.copysign(nrmxl, diag)
                qr[col:, col] = qr[col:, col] / nrmxl
                qr[col, col] = 1.0 + float(qr[col, col])
                if p >= col + 2:
                    for j in range(col + 1, p):
                        dot = _ddot(qr[col:, col], qr[col:, j])
                        scale = -dot / float(qr[col, col])
                        qr[col:, j] = qr[col:, j] + scale * qr[col:, col]
                        if qraux[j] != 0.0:
                            entry = abs(float(qr[col, j])) / qraux[j]
                            tt = 1.0 - entry * entry
                            if tt < 0.0:
                                tt = 0.0
                            if abs(tt) >= 1e-6:
                                qraux[j] = qraux[j] * math.sqrt(tt)
                            else:
                                qraux[j] = _dnrm2(qr[col + 1 :, j])
                                work1[j] = qraux[j]
                qraux[col] = float(qr[col, col])
                qr[col, col] = -nrmxl
    rank = int(min(k - 1, n))
    return rank, np.array(qraux, dtype=np.float64), np.array(pivot, dtype=int), qr


def dqrsl(qr, k: int, qraux, y, job: int) -> dict:
    """LINPACK dqrsl. ``job`` is decimal digits: qy, qty, b, rsd, xb."""
    n, p = qr.shape
    cqy = job // 10000 != 0
    cqty = (job % 10000) // 1000 != 0
    cb = (job % 1000) // 100 != 0
    cr = (job % 100) // 10 != 0
    ju = min(k, n - 1)
    work = np.array(y, dtype=np.float64, copy=True).reshape(-1)
    qy = work.copy() if cqy else None
    qty = work.copy() if cqty else None
    # qy applies the reflectors in reverse order, qty in forward order. The
    # stored diagonal holds -nrmxl; the reflector's leading element is qraux.
    if cqy:
        for j in range(ju, 0, -1):
            if qraux[j - 1] == 0.0:
                continue
            col = qr[j - 1 :, j - 1].copy()
            col[0] = qraux[j - 1]
            t = -_ddot(col, qy[j - 1 :]) / col[0]
            qy[j - 1 :] = qy[j - 1 :] + t * col
    if cqty:
        for j in range(1, ju + 1):
            if qraux[j - 1] == 0.0:
                continue
            col = qr[j - 1 :, j - 1].copy()
            col[0] = qraux[j - 1]
            t = -_ddot(col, qty[j - 1 :]) / col[0]
            qty[j - 1 :] = qty[j - 1 :] + t * col
    b = None
    info = 0
    if cb:
        b = qty[:k].copy()
        for j in range(k, 0, -1):
            if qr[j - 1, j - 1] == 0.0:
                info = j
                b = None
                break
            b[j - 1] = b[j - 1] / qr[j - 1, j - 1]
            if j != 1:
                b[: j - 1] = b[: j - 1] + (-b[j - 1]) * qr[: j - 1, j - 1]
    return {"qy": qy, "qty": qty, "b": b, "info": info}


def dqrls(x, y, tol: float) -> dict:
    """R's C_Cdqrls: dqrdc2 then dqrsl(job = 1110), coefficients unpermuted."""
    copy = np.array(x, dtype=np.float64, copy=True)
    rank, qraux, pivot, qr = dqrdc2(copy, tol)
    out = dqrsl(qr, rank, qraux, y, 1110)
    coef = None
    if out["b"] is not None:
        coef = np.zeros(x.shape[1], dtype=np.float64)
        coef[pivot] = out["b"]
    return {
        "coefficients": coef,
        "rank": rank,
        "qr": qr,
        "qraux": qraux,
        "pivot": pivot,
        "effects": out["qy"],
        "qty": out["qty"],
    }


# ------------------------------------------------- binomial family internals


def _linkinv(kind: str, eta):
    eta = np.asarray(eta, dtype=np.float64).reshape(-1)
    if kind == "logit":
        # R's C_logit_linkinv computes exp(eta)/(1+exp(eta)) directly.
        out = np.empty(eta.shape, dtype=np.float64)
        for i, value in enumerate(eta):
            if not np.isfinite(value):
                out[i] = math.nan
            elif value > 37.0:
                out[i] = 1.0
            elif value < -37.0:
                out[i] = 0.0
            else:
                e = math.exp(value)
                out[i] = e / (1.0 + e)
        return out
    from scipy.stats import cauchy, norm

    if kind == "probit":
        thresh = -norm.ppf(_DBL_EPS)
        return norm.cdf(np.clip(eta, -thresh, thresh))
    thresh = -cauchy.ppf(_DBL_EPS)
    return cauchy.cdf(np.clip(eta, -thresh, thresh))


def _mu_eta(kind: str, eta):
    eta = np.asarray(eta, dtype=np.float64).reshape(-1)
    if kind == "logit":
        out = np.empty(eta.shape, dtype=np.float64)
        for i, value in enumerate(eta):
            if not np.isfinite(value):
                out[i] = 0.0
            elif value > 37.0 or value < -37.0:
                out[i] = 0.0
            else:
                e = math.exp(-abs(value))
                f = 1.0 + e
                out[i] = e / (f * f)
        return out
    from scipy.stats import cauchy, norm

    if kind == "probit":
        return np.maximum(norm.pdf(eta), _DBL_EPS)
    return np.maximum(cauchy.pdf(eta), _DBL_EPS)


def _binomial_dev_resids(y, mu, wt):
    """R's C_binomial_dev_resids."""
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    mu = np.asarray(mu, dtype=np.float64).reshape(-1)
    wt = np.asarray(wt, dtype=np.float64).reshape(-1)
    out = np.zeros(y.shape, dtype=np.float64)
    for i in range(y.size):
        yi, mui = y[i], mu[i]
        if yi == 0.0:
            out[i] = -2.0 * wt[i] * math.log1p(-mui)
        elif yi == 1.0:
            out[i] = -2.0 * wt[i] * math.log(mui)
        else:
            out[i] = 2.0 * wt[i] * (
                yi * math.log(yi / mui if yi > 0 else 1.0)
                + (1.0 - yi) * math.log((1.0 - yi) / (1.0 - mui))
            )
    return out


def _valid_mu(mu) -> bool:
    mu = np.asarray(mu, dtype=np.float64)
    return bool(np.all(np.isfinite(mu)) and np.all(mu > 0.0) and np.all(mu < 1.0))


# ---------------------------------------------------------------- glm.fit


def glm_fit(
    x,
    y,
    weights=None,
    offset=None,
    family: str = "logit",
    maxit: int = 25,
    epsilon: float = 1e-8,
) -> dict:
    """stats::glm.fit for binomial(logit|probit|cauchit)."""
    design = np.asarray(x, dtype=np.float64)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=np.float64).reshape(-1)
    nobs, nvars = design.shape
    prior = np.ones(nobs) if weights is None else np.asarray(weights, dtype=np.float64).reshape(-1)
    off = np.zeros(nobs) if offset is None else np.asarray(offset, dtype=np.float64).reshape(-1)

    # binomial()$initialize, one-column branch.
    starts = (prior * response + 0.5) / (prior + 1.0)
    mustart = starts.copy()
    mustart[prior == 0.0] = 0.0

    eta = _linkinv_inverse(family, mustart)
    mu = _linkinv(family, eta)
    if not _valid_mu(mu):
        raise ValueError("cannot find valid starting values: please specify some")

    devold = math.fsum(_binomial_dev_resids(response, mu, prior))
    coef = np.zeros(nvars, dtype=np.float64)
    start = np.zeros(nvars, dtype=np.float64)
    fit = {"rank": nvars, "pivot": np.arange(nvars)}
    conv = False
    dev = devold
    iterations = 0
    for iterations in range(1, int(maxit) + 1):
        good = prior > 0
        mu_eta_val = _mu_eta(family, eta)
        good = good & (mu_eta_val != 0.0)
        if not np.any(good):
            break
        z = (eta - off)[good] + (response - mu)[good] / mu_eta_val[good]
        variance = mu[good] * (1.0 - mu[good])
        w = np.sqrt((prior[good] * mu_eta_val[good] ** 2) / variance)
        fit = dqrls(design[good, :] * w[:, None], z * w, min(1e-07, epsilon / 1000.0))
        if fit["coefficients"] is None:
            break
        start = np.asarray(fit["coefficients"], dtype=np.float64).copy()
        eta = design @ start
        eta = eta + off
        mu = _linkinv(family, eta)
        dev = math.fsum(_binomial_dev_resids(response, mu, prior))
        if abs(dev - devold) / (0.1 + abs(dev)) < epsilon:
            conv = True
            coef = start.copy()
            break
        devold = dev
        coef = start.copy()
    if fit["rank"] < nvars:
        dropped = np.zeros(nvars, dtype=np.float64)
        dropped[fit["pivot"][fit["rank"] :]] = np.nan
        coef = np.where(np.isnan(dropped), np.nan, coef)
    return {
        "coefficients": coef,
        "rank": fit["rank"],
        "fitted_values": mu,
        "linear_predictors": eta,
        "deviance": dev,
        "converged": conv,
        "iter": iterations,
    }


def _linkinv_inverse(kind: str, mu):
    mu = np.asarray(mu, dtype=np.float64).reshape(-1)
    if kind == "logit":
        return np.array([math.log(v / (1.0 - v)) for v in mu], dtype=np.float64)
    from scipy.stats import cauchy, norm

    if kind == "probit":
        return norm.ppf(mu)
    return cauchy.ppf(mu)
