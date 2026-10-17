"""Royston D and synthetic R-squared values for a Cox model (survival::royston)."""

from __future__ import annotations

import math

import numpy as np
from scipy.optimize import minimize_scalar

from survival._coxsurv import _component, _inherits
from survival.norm import qnorm
from survival.surv import is_Surv
from survival.wtest import _cholesky2, _chsolve2


_PI = 3.141592653589793


def _as_surv_matrix(y):
    if is_Surv(y):
        return np.asarray(y.columns, dtype=float)
    arr = np.asarray(y, dtype=float)
    if arr.ndim != 2 or arr.shape[1] not in (2, 3):
        raise ValueError("response must be a Surv object")
    return arr


def _rank_first(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    ranks = np.empty(x.size, dtype=float)
    ranks[order] = np.arange(1, x.size + 1, dtype=float)
    return ranks


def _rank_average(x: np.ndarray) -> np.ndarray:
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    ranks = np.empty(x.size, dtype=float)
    i = 0
    n = x.size
    while i < n:
        j = i
        while j + 1 < n and sorted_x[j + 1] == sorted_x[i]:
            j += 1
        avg = 0.5 * (i + j) + 1.0
        ranks[order[i : j + 1]] = avg
        i = j + 1
    return ranks


def _coxfit1(
    y: np.ndarray,
    x: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    offset: np.ndarray | None = None,
    method: str = "efron",
    eps: float = 1e-9,
    maxiter: int = 20,
    toler_chol: float = 1e-9,
) -> dict[str, float | np.ndarray]:
    """Single-predictor Cox fit matching survival::coxfit6 (Efron ties by default)."""
    y = np.asarray(y, dtype=float)
    x_orig = np.asarray(x, dtype=float).reshape(-1)
    n = x_orig.size
    if y.shape[0] != n:
        raise ValueError("x and y have different lengths")
    ny = y.shape[1]
    time = y[:, ny - 2]
    status = y[:, ny - 1].astype(int)

    if weights is None:
        wt = np.ones(n, dtype=float)
    else:
        wt = np.asarray(weights, dtype=float).reshape(-1)
    if offset is None:
        off = np.zeros(n, dtype=float)
    else:
        off = np.asarray(offset, dtype=float).reshape(-1)

    order = np.argsort(time, kind="mergesort")
    time = time[order]
    status = status[order]
    x_orig = x_orig[order]
    wt = wt[order]
    off = off[order]

    meth = 0 if method in ("breslow", "exact") else 1
    strata = np.zeros(n, dtype=int)
    strata[-1] = 1

    def iter_beta(beta_val: float) -> tuple[float, float, float]:
        u = 0.0
        imat = 0.0
        loglik = 0.0
        denom = 0.0
        a = 0.0
        a2 = 0.0
        cmat = 0.0
        cmat2 = 0.0
        person = n - 1
        while person >= 0:
            if strata[person] == 1:
                denom = 0.0
                a = 0.0
                cmat = 0.0
            dtime = time[person]
            ndead = 0
            deadwt = 0.0
            denom2 = 0.0
            while person >= 0 and time[person] == dtime:
                zbeta = off[person] + beta_val * x_orig[person]
                risk = math.exp(zbeta) * wt[person]
                if status[person] == 0:
                    denom += risk
                    a += risk * x_orig[person]
                    cmat += risk * x_orig[person] * x_orig[person]
                else:
                    ndead += 1
                    deadwt += wt[person]
                    denom2 += risk
                    loglik += wt[person] * zbeta
                    u += wt[person] * x_orig[person]
                    a2 += risk * x_orig[person]
                    cmat2 += risk * x_orig[person] * x_orig[person]
                person -= 1
                if person >= 0 and strata[person] == 1:
                    break
            if ndead > 0:
                if meth == 0 or ndead == 1:
                    denom += denom2
                    loglik -= deadwt * math.log(denom)
                    a += a2
                    temp2 = a / denom
                    u -= deadwt * temp2
                    cmat += cmat2
                    imat += deadwt * (cmat - temp2 * a) / denom
                else:
                    wtave = deadwt / ndead
                    for _k in range(ndead):
                        denom += denom2 / ndead
                        loglik -= wtave * math.log(denom)
                        a += a2 / ndead
                        temp2 = a / denom
                        u -= wtave * temp2
                        cmat += cmat2 / ndead
                        imat += wtave * (cmat - temp2 * a) / denom
        return loglik, -u, -imat

    def loglik_only(beta_val: float) -> float:
        ll, _, _ = iter_beta(beta_val)
        return ll

    beta = 0.0
    loglik0, u0, imat0 = iter_beta(beta)
    factor = _cholesky2(np.array([[imat0]], dtype=float), toler_chol)
    newbeta = beta + _chsolve2(factor, np.array([u0], dtype=float))[0]
    loglik_best = loglik0
    beta_best = beta
    halving = 0

    for _ in range(maxiter):
        newlk, u_new, imat_new = iter_beta(newbeta)
        factor = _cholesky2(np.array([[imat_new]], dtype=float), toler_chol)
        if not math.isfinite(newlk) or newlk < loglik_best:
            halving += 1
            newbeta = (newbeta + halving * beta_best) / (halving + 1.0)
            continue
        halving = 0
        if abs(1.0 - (loglik_best / newlk)) <= eps:
            beta_best = newbeta
            loglik_best = newlk
            break
        loglik_best = newlk
        beta_best = newbeta
        step = _chsolve2(factor, np.array([u_new], dtype=float))[0]
        newbeta = newbeta + step

    polish = minimize_scalar(
        lambda b: -loglik_only(b),
        bounds=(beta_best - 2.0, beta_best + 2.0),
        method="bounded",
        options={"xatol": 1e-14},
    )
    beta_best = float(polish.x)
    loglik_best = loglik_only(beta_best)

    h = 1e-5 * max(1.0, abs(beta_best))
    llm2 = loglik_only(beta_best - 2.0 * h)
    llm1 = loglik_only(beta_best - h)
    ll0 = loglik_only(beta_best)
    llp1 = loglik_only(beta_best + h)
    llp2 = loglik_only(beta_best + 2.0 * h)
    d2 = (-llp2 + 16.0 * llp1 - 30.0 * ll0 + 16.0 * llm1 - llm2) / (12.0 * h * h)
    var = -1.0 / d2 if d2 != 0.0 else math.nan
    lp = off + beta_best * x_orig
    return {
        "coefficients": np.array([beta_best], dtype=float),
        "var": np.array([[var]], dtype=float),
        "linear.predictors": lp,
        "loglik": np.array([loglik0, loglik_best], dtype=float),
    }


def _terms_specials(fit) -> dict:
    terms = _component(fit, "terms", optional=True)
    if terms is None:
        return {}
    if isinstance(terms, dict):
        return terms.get("specials", {}) or {}
    return getattr(terms, "specials", {}) or {}


def _predict_lp(fit, newdata=None) -> np.ndarray:
    if newdata is None:
        return np.asarray(_component(fit, "linear.predictors"), dtype=float).reshape(-1)
    raise NotImplementedError("newdata prediction is not implemented")


def royston(fit, newdata=None, ties=True, adjust=False):
    """Compute Royston D and synthetic R-squared measures for a coxph fit."""
    if not _inherits(fit, "coxph"):
        raise ValueError("function defined only for coxph models")
    if _inherits(fit, "coxphms"):
        raise ValueError("not defined for multi-state models")

    missing_newdata = newdata is None
    if missing_newdata:
        eta = _predict_lp(fit)
        y2 = _as_surv_matrix(_component(fit, "y"))
    else:
        specials = _terms_specials(fit)
        if specials.get("strata"):
            raise ValueError("cannot use newdata for a stratified model")
        if specials.get("tt"):
            raise ValueError("cannot use newdata for a model with tt() terms")
        if _component(fit, "penaly", optional=True) is not None:
            raise ValueError("cannot use newdata for a penalized model")
        raise NotImplementedError("newdata is not implemented")

    n = eta.size
    v_eta = float(np.var(eta, ddof=1))
    r_ko = v_eta / (_PI**2 / 6.0 + v_eta)

    eta = np.asarray(eta, dtype=float)
    if ties and np.unique(eta).size < n:
        z = np.array([qnorm((i - 3.0 / 8.0) / (n + 0.25)) for i in range(1, n + 1)], dtype=float)
        uniq = np.sort(np.unique(eta))
        index1 = np.array([np.where(uniq == val)[0][0] + 1 for val in eta], dtype=int)
        index2 = _rank_first(eta).astype(int)
        z2 = np.zeros(uniq.size + 1, dtype=float)
        for idx in range(1, uniq.size + 1):
            mask = index1 == idx
            z2[idx] = float(np.mean(z[index2[mask] - 1]))
        qhat = z2[index1]
    else:
        ranks = _rank_average(eta)
        qhat = np.array([qnorm((r - 3.0 / 8.0) / (n + 0.25)) for r in ranks], dtype=float)

    rfit = _coxfit1(y2, qhat)
    beta = float(np.asarray(rfit["coefficients"], dtype=float).reshape(-1)[0])
    var = np.asarray(rfit["var"], dtype=float)
    se_d = math.sqrt(float(var[0, 0]) * 8.0 / _PI)
    d_val = beta * math.sqrt(8.0 / _PI)
    r2 = beta**2 / (_PI**2 / 6.0 + beta**2)
    r_i = beta**2 / (1.0 + beta**2)

    if adjust:
        nevent = float(_component(fit, "nevent"))
        coef = np.asarray(_component(fit, "coefficients"), dtype=float).reshape(-1)
        ncoef = int(np.sum(~np.isnan(coef)))
        r_adj = nevent / (nevent - ncoef)
        temp = (1.0 + beta**2 - r_adj) / r_adj
        d_val = math.copysign(1.0, beta) * math.copysign(1.0, temp) * math.sqrt(abs(temp) * 8.0 / _PI)
        se_d = se_d * abs(beta) / (r_adj * math.sqrt(abs(temp)))
        r2 = 1.0 - r_adj * (1.0 - r_i)

    eta_sorted = np.sort(eta)
    temp_sum = 0.0
    for i in range(n - 1):
        diffs = eta_sorted[i] - eta_sorted[(i + 1) : n]
        temp_sum += float(np.sum(1.0 / (1.0 + np.exp(diffs))))
    gh = temp_sum * 2.0 / (n * (n - 1))

    out = {
        "D": d_val,
        "se(D)": se_d,
        "R.D": r2,
        "R.KO": r_ko,
        "C.GH": gh,
    }
    if missing_newdata:
        loglik = np.asarray(_component(fit, "loglik"), dtype=float).reshape(-1)
        n_obs = float(_component(fit, "n"))
        logtest = -2.0 * (loglik[0] - loglik[1])
        r_n = (1.0 - math.exp(-logtest / n_obs)) / (1.0 - math.exp(2.0 * loglik[0] / n_obs))
        out["R.N"] = r_n

    return out
