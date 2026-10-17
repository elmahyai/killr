"""Saddlepoint approximations from CRAN boot 1.3-32.

The density and distribution formulas are the ones in R/bootfuns.q.
Nelder-Mead, the GLM iteration, and the smoothing spline follow the same
numerical steps R uses to evaluate those formulas. The linear program is
boot.simplex, which already matches the tableau in that file.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

import numpy as np

from boot.simplex import simplex as _simplex

_EPS = 2.220446049250313e-16
_RELTOL = math.sqrt(_EPS)
_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)
_GLM_EPS = 1e-8
_GLM_MAXIT = 100

# Unit-interval Gram matrix of second derivatives of the Bernstein basis,
# as returned by R's sgram: the analytic integral minus 0.012 * v v'.
_V3 = np.array([1.0, -3.0, 3.0, -1.0])
_EXACT_BERN = np.array(
    [
        [12.0, -18.0, 0.0, 6.0],
        [-18.0, 36.0, -18.0, 0.0],
        [0.0, -18.0, 36.0, -18.0],
        [6.0, 0.0, -18.0, 12.0],
    ],
    dtype=float,
)
_SGRAM_BERN = _EXACT_BERN - 0.012 * np.outer(_V3, _V3)
_BERN_U = np.array([0.2, 0.4, 0.6, 0.8])


def _pnorm(x: float) -> float:
    return 0.5 * math.erfc(-float(x) / _SQRT2)


def _dnorm(x: float) -> float:
    return math.exp(-0.5 * float(x) * float(x)) / _SQRT2PI


def _qnorm_acklam(p: float) -> float:
    a = (
        -3.969683028665376e01,
        2.209460984245205e02,
        -2.759285104469687e02,
        1.383577518672690e02,
        -3.066479806614716e01,
        2.506628277459239e00,
    )
    b = (
        -5.447609879822406e01,
        1.615858368580409e02,
        -1.556989798598866e02,
        6.680131188771972e01,
        -1.328068155288572e01,
    )
    c = (
        -7.784894002430293e-03,
        -3.223964580411365e-01,
        -2.400758277161838e00,
        -2.549732539343734e00,
        4.374664141464968e00,
        2.938163982698783e00,
    )
    d = (
        7.784695709041462e-03,
        3.224671290700398e-01,
        2.445134137142996e00,
        3.754408661907416e00,
    )
    plow = 0.02425
    if p < plow:
        q = math.sqrt(-2.0 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    if p > 1.0 - plow:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / (
            (((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1.0
        )
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (
        (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0)
    )


def _qnorm(p: float) -> float:
    """Acklam's approximation, polished so the pure-Python cdf matches R."""
    if p == 0.5:
        return 0.0
    if p <= 0.0 or p >= 1.0:
        if p == 0.0:
            return -math.inf
        if p == 1.0:
            return math.inf
        return math.nan
    x = _qnorm_acklam(p)
    for _ in range(4):
        pdf = _dnorm(x)
        if pdf == 0.0 or not math.isfinite(pdf):
            break
        x -= (_pnorm(x) - p) / pdf
    return x


def _qnorm_vec(p) -> np.ndarray:
    return np.array([_qnorm(float(v)) for v in np.asarray(p, dtype=float)], dtype=float)


def _isna(value) -> bool:
    try:
        return bool(value != value)
    except Exception:
        return False


def _sgn(x: float, eps: float = 1e-10) -> float:
    if abs(x) < eps:
        return 0.0
    return 1.0 if x > 0.0 else -1.0


def _det_abs(mat) -> float:
    """abs(prod(eigenvalues)), with R's NA and non-finite rules."""
    arr = np.asarray(mat, dtype=float)
    if arr.size == 0:
        return 1.0
    if arr.ndim == 0 or arr.size == 1:
        val = float(arr.reshape(-1)[0])
        if _isna(val):
            return math.nan
        if not math.isfinite(val):
            return math.inf
        return abs(val)
    arr = np.atleast_2d(arr)
    if np.any(np.isnan(arr)):
        return math.nan
    if not np.all(np.isfinite(arr)):
        return math.inf
    return float(abs(np.prod(np.linalg.eigvals(arr))))


def _as_2d(a) -> np.ndarray:
    arr = np.asarray(a, dtype=float)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    if arr.ndim != 2:
        raise ValueError("A must be a vector or a matrix")
    return np.array(arr, dtype=float, copy=True)


def _colon(start: int, end: int) -> list[int]:
    """R's colon, which walks backwards and is never empty."""
    if start <= end:
        return list(range(start, end + 1))
    return list(range(start, end - 1, -1))


def _seq_int(start: float, stop: float, length: int) -> np.ndarray:
    length = int(length)
    if length <= 0:
        return np.zeros(0)
    if length == 1:
        return np.array([float(start)])
    return np.linspace(float(start), float(stop), length)


def _optim_nm(start: np.ndarray, fn: Callable[[np.ndarray], float], maxit: int = 500):
    """R optim(method='Nelder-Mead') with the default control list.

    The returned point is the best vertex when the simplex stops, which is
    the value boot stores as zeta. It is not the root of the derivative.
    """
    start = [float(v) for v in np.asarray(start, dtype=float).reshape(-1)]
    n = len(start)
    step = 0.0
    for value in start:
        if abs(value) > step:
            step = abs(value)
    step = 0.1 * step if step != 0.0 else 0.1
    verts = [start[:]]
    for j in range(n):
        vert = start[:]
        vert[j] = start[j] + step
        verts.append(vert)
    f = [float(fn(np.asarray(vert, dtype=float))) for vert in verts]
    fncount = n + 1
    intol = _RELTOL * (abs(f[0]) + _RELTOL)
    hit_maxit = False
    while True:
        order = sorted(range(n + 1), key=lambda i: (f[i], i))
        ilo = order[0]
        ihi = order[-1]
        inext = order[-2]
        vh, vl = f[ihi], f[ilo]
        if vl <= -math.inf or (vh - vl) <= intol:
            break
        if fncount >= maxit:
            hit_maxit = True
            break
        xbar = [0.0] * n
        for i in range(n + 1):
            if i == ihi:
                continue
            for k in range(n):
                xbar[k] += verts[i][k]
        for k in range(n):
            xbar[k] /= n
        xr = [xbar[k] + (xbar[k] - verts[ihi][k]) for k in range(n)]
        fr = float(fn(np.asarray(xr, dtype=float)))
        fncount += 1
        if fr < f[ilo]:
            xe = [xbar[k] + 2.0 * (xr[k] - xbar[k]) for k in range(n)]
            fe = float(fn(np.asarray(xe, dtype=float)))
            fncount += 1
            if fe < fr:
                verts[ihi] = xe
                f[ihi] = fe
            else:
                verts[ihi] = xr
                f[ihi] = fr
        elif fr < f[inext]:
            verts[ihi] = xr
            f[ihi] = fr
        elif fr < f[ihi]:
            xc = [xbar[k] + 0.5 * (xr[k] - xbar[k]) for k in range(n)]
            fc = float(fn(np.asarray(xc, dtype=float)))
            fncount += 1
            if fc <= fr:
                verts[ihi] = xc
                f[ihi] = fc
            else:
                for i in range(n + 1):
                    if i == ilo:
                        continue
                    verts[i] = [(verts[i][k] + verts[ilo][k]) / 2.0 for k in range(n)]
                    f[i] = float(fn(np.asarray(verts[i], dtype=float)))
                    fncount += 1
        else:
            xc = [xbar[k] + 0.5 * (verts[ihi][k] - xbar[k]) for k in range(n)]
            fc = float(fn(np.asarray(xc, dtype=float)))
            fncount += 1
            if fc < f[ihi]:
                verts[ihi] = xc
                f[ihi] = fc
            else:
                for i in range(n + 1):
                    if i == ilo:
                        continue
                    verts[i] = [(verts[i][k] + verts[ilo][k]) / 2.0 for k in range(n)]
                    f[i] = float(fn(np.asarray(verts[i], dtype=float)))
                    fncount += 1
    ilo = min(range(n + 1), key=lambda i: (f[i], i))
    return np.asarray(verts[ilo], dtype=float), 1 if hit_maxit else 0


def _levels_sorted(strata: np.ndarray) -> list:
    values = strata.tolist()
    unique = []
    seen = set()
    for value in values:
        key = value if isinstance(value, (int, float, str)) else str(value)
        if key not in seen:
            seen.add(key)
            unique.append(value)
    return sorted(unique)


def _group_sum(values: np.ndarray, strata: np.ndarray, levels: Sequence) -> np.ndarray:
    out = np.empty(len(levels), dtype=float)
    for i, level in enumerate(levels):
        out[i] = float(np.sum(values[strata == level]))
    return out


def _pois_deviance(y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> float:
    out = np.empty(y.shape, dtype=float)
    positive = y > 0.0
    out[~positive] = wt[~positive] * mu[~positive]
    yy = y[positive]
    mm = mu[positive]
    out[positive] = wt[positive] * (yy * np.log(yy / mm) - (yy - mm))
    return float(2.0 * np.sum(out))


def _binom_deviance(y: np.ndarray, mu: np.ndarray, wt: np.ndarray) -> float:
    out = np.empty(y.shape, dtype=float)
    at_zero = y == 0.0
    at_one = y == 1.0
    middle = ~at_zero & ~at_one
    out[at_zero] = -2.0 * wt[at_zero] * np.log(1.0 - mu[at_zero])
    out[at_one] = -2.0 * wt[at_one] * np.log(mu[at_one])
    if np.any(middle):
        yy = y[middle]
        mm = mu[middle]
        out[middle] = 2.0 * wt[middle] * (
            yy * np.log(yy / mm) + (1.0 - yy) * np.log((1.0 - yy) / (1.0 - mm))
        )
    return float(np.sum(out))


def _glm_cov(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    """(X' W X)^{-1} from the weights of the iteration that accepted the step."""
    if x.shape[1] == 0:
        return np.zeros((0, 0))
    weighted = x * w[:, None]
    gram = weighted.T @ weighted
    return np.linalg.inv(gram)


def _glm_fit(x: np.ndarray, y: np.ndarray, family: str, offset: np.ndarray, weights: np.ndarray):
    """IRLS for poisson(log) or binomial(logit), no intercept, with an offset.

    The first linear predictor is the link of the starting mean and does not
    yet include the offset. That is the first step glm.fit takes.
    """
    x = np.asarray(x, dtype=float)
    if x.ndim == 1:
        x = x.reshape(-1, 1)
    y = np.asarray(y, dtype=float).reshape(-1)
    offset = np.asarray(offset, dtype=float).reshape(-1)
    weights = np.asarray(weights, dtype=float).reshape(-1)
    n_obs, n_vars = x.shape
    if family == "poisson":
        mustart = y + 0.1
        eta = np.log(mustart)
        mu = mustart.copy()
        dev_fun = _pois_deviance
        linkinv = np.exp
        def mu_eta(eta_now, mu_now):
            return np.exp(eta_now)
        def variance(mu_now):
            return mu_now
    elif family == "binomial":
        mustart = (weights * y + 0.5) / (weights + 1.0)
        mu = np.clip(mustart, 1e-16, 1.0 - 1e-16)
        eta = np.log(mu / (1.0 - mu))
        dev_fun = _binom_deviance
        def linkinv(eta_now):
            out = np.empty(eta_now.shape, dtype=float)
            low = eta_now < -30.0
            high = eta_now > 30.0
            mid = ~low & ~high
            out[low] = _EPS
            out[high] = 1.0 - _EPS
            if np.any(mid):
                ee = np.exp(eta_now[mid])
                out[mid] = ee / (1.0 + ee)
            return out
        def mu_eta(eta_now, mu_now):
            return mu_now * (1.0 - mu_now)
        def variance(mu_now):
            return mu_now * (1.0 - mu_now)
    else:
        raise ValueError(f"family must be 'poisson' or 'binomial', not {family!r}")

    if n_vars == 0:
        eta = offset.copy()
        mu = linkinv(eta)
        dev = dev_fun(y, mu, weights)
        return {
            "coef": np.zeros(0),
            "deviance": dev,
            "cov_unscaled": np.zeros((0, 0)),
            "converged": True,
        }

    dev_old = dev_fun(y, mu, weights)
    beta = np.zeros(n_vars, dtype=float)
    beta_old = None
    cov = np.eye(n_vars)
    converged = False
    for _iteration in range(_GLM_MAXIT):
        mu_eta_val = mu_eta(eta, mu)
        var_mu = variance(mu)
        z = (eta - offset) + (y - mu) / mu_eta_val
        w = np.sqrt((weights * mu_eta_val**2) / var_mu)
        weighted_x = x * w[:, None]
        weighted_z = z * w
        beta_new, _, _, _ = np.linalg.lstsq(weighted_x, weighted_z, rcond=None)
        eta_linear = x @ beta_new
        eta_new = eta_linear + offset
        mu_new = linkinv(eta_new)
        dev = dev_fun(y, mu_new, weights)
        if not np.isfinite(dev):
            if beta_old is None:
                break
            for _half in range(_GLM_MAXIT):
                beta_new = 0.5 * (beta_new + beta_old)
                eta_new = x @ beta_new + offset
                mu_new = linkinv(eta_new)
                dev = dev_fun(y, mu_new, weights)
                if np.isfinite(dev):
                    break
        cov = _glm_cov(x, w)
        beta = beta_new
        eta = eta_new
        mu = mu_new
        if abs(dev - dev_old) / (0.1 + abs(dev)) < _GLM_EPS:
            converged = True
            break
        dev_old = dev
        beta_old = beta.copy()
    return {
        "coef": beta,
        "deviance": float(dev),
        "cov_unscaled": cov,
        "converged": converged,
    }


def _spa_from_r(r: float, v: float, LR: bool, plus: bool) -> float:
    if LR:
        sign = 1.0 if plus else -1.0
        return _pnorm(r) + _dnorm(r) * (1.0 / r + sign * 1.0 / v)
    return _pnorm(r + math.log(v / r) / r)


def _nan_pair():
    return np.array([math.nan, math.nan]), np.array([math.nan])


def saddle(
    A=None,
    u=None,
    wdist="m",
    type="simp",
    d=None,
    d1=1,
    init=None,
    mu=None,
    LR=False,
    strata=None,
    k_adj=None,
    k2=None,
):
    """Saddlepoint density and cdf at one point.

    Returns spa (pdf, cdf), zeta.hat, and zeta2.hat when type is cond.
    k_adj and k2 are K.adj and K2. A supplied matrix sets d to its column count.
    init and mu follow the lazy defaults rep(0.1, d) and rep(0.5, n).
    """
    if A is not None:
        A = _as_2d(A)
        d = int(A.shape[1])
        u = np.asarray(u, dtype=float).reshape(-1)
        if u.size != d:
            raise ValueError(
                f"number of columns of 'A' ({d}) not equal to length of 'u' ({u.size})"
            )
        n = int(A.shape[0])
    elif k_adj is None:
        raise ValueError("either 'A' and 'u' or 'K.adj' and 'K2' must be supplied")
    else:
        n = None

    if k_adj is not None:
        if d is None:
            d = 1
        d = int(d)
        type = "simp"
        wdist = "o"
        if init is None:
            init = np.full(d, 0.1)
        init = np.asarray(init, dtype=float).reshape(-1)
        zeta, conv = _optim_nm(init, lambda al: float(k_adj(al)))
        if conv == 0:
            ahat = zeta
            khat = float(k_adj(ahat))
            k2hat = _det_abs(k2(ahat))
            gs = math.exp(khat) / math.sqrt((2.0 * math.pi) ** d * k2hat)
            if d == 1:
                r = _sgn(float(ahat.reshape(-1)[0])) * math.sqrt(-2.0 * khat)
                v = float(ahat.reshape(-1)[0]) * math.sqrt(k2hat)
                gs_cdf = _spa_from_r(r, v, LR, plus=True)
            else:
                gs_cdf = math.nan
            spa = np.array([gs, gs_cdf])
        else:
            spa, ahat = _nan_pair()
        return {"spa": spa, "zeta.hat": np.asarray(ahat, dtype=float).reshape(-1)}

    d = int(d)
    d1 = int(d1)
    if init is None:
        init = np.full(d, 0.1)
    init = np.asarray(init, dtype=float).reshape(-1)
    if mu is None:
        if n is None:
            raise ValueError("mu is required when A does not set n")
        mu = np.full(n, 0.5)
    mu = np.asarray(mu, dtype=float).reshape(-1)

    if wdist == "m":
        type = "simp"
        if strata is None:
            p = mu / np.sum(mu)

            def objective(al):
                al = np.asarray(al, dtype=float).reshape(-1)
                w = p * np.exp(A @ al)
                return n * math.log(float(np.sum(w))) - float(np.dot(al, u))

            zeta, conv = _optim_nm(init, objective)
            ahat = zeta
            w = p * np.exp(A @ ahat)
            khat = n * math.log(float(np.sum(w))) - float(np.dot(ahat, u))
            sw = float(np.sum(w))
            if d == 1:
                column = A[:, 0]
                k2hat = n * (
                    float(np.sum(w * column * column)) / sw
                    - (float(np.sum(w * column)) / sw) ** 2
                )
            else:
                saw = w @ A
                sa2w = (A * w[:, None]).T @ A
                k2hat = _det_abs(n / sw * (sa2w - np.outer(saw, saw) / sw))
        else:
            strata_arr = np.asarray(strata)
            levels = _levels_sorted(strata_arr)
            counts = np.array(
                [float(np.sum(strata_arr == level)) for level in levels], dtype=float
            )
            group = _group_sum(mu, strata_arr, levels)
            sm = np.empty(n, dtype=float)
            for level, total in zip(levels, group):
                sm[strata_arr == level] = total
            p = mu / sm

            def objective(al):
                al = np.asarray(al, dtype=float).reshape(-1)
                w = p * np.exp(A @ al)
                grouped = _group_sum(w, strata_arr, levels)
                return float(np.sum(counts * np.log(grouped)) - np.dot(al, u))

            zeta, conv = _optim_nm(init, objective)
            ahat = zeta
            w = p * np.exp(A @ ahat)
            grouped = _group_sum(w, strata_arr, levels)
            khat = float(np.sum(counts * np.log(grouped)) - np.dot(ahat, u))
            temp = np.zeros((d, d))
            # seq_along(table) compares strata with 1..S, not with the level label.
            for s, count in enumerate(counts, start=1):
                gp = np.flatnonzero(strata_arr == s)
                sw = float(np.sum(w[gp]))
                saw = w[gp] @ A[gp, :]
                sa2w = (A[gp, :] * w[gp, None]).T @ A[gp, :]
                temp = temp + count / sw * (sa2w - np.outer(saw, saw) / sw)
            k2hat = _det_abs(temp)
        if conv == 0:
            gs = math.exp(khat) / (math.sqrt(2.0 * math.pi * k2hat) ** d)
            if d == 1:
                r = _sgn(float(ahat.reshape(-1)[0])) * math.sqrt(-2.0 * khat)
                v = float(ahat.reshape(-1)[0]) * math.sqrt(k2hat)
                gs_cdf = _spa_from_r(r, v, LR, plus=False)
            else:
                gs_cdf = math.nan
            spa = np.array([gs, gs_cdf])
        else:
            spa, ahat = _nan_pair()
        return {"spa": spa, "zeta.hat": np.asarray(ahat, dtype=float).reshape(-1)}

    if wdist == "p":
        if type != "cond":
            raise ValueError("this type not implemented for Poisson")
        solved = _simplex(np.zeros(n), A3=A.T, b3=u)
        if solved.solved == 1:
            y = np.asarray(solved.soln, dtype=float)
            design1 = A[:, :d1]
            design2 = A[:, d1:]
            x1 = A
            offset = np.log(mu)
            weights = np.ones(n)
            mod1 = _glm_fit(x1, y, "poisson", offset, weights)
            mod2 = _glm_fit(design2, y, "poisson", offset, weights)
            ahat = mod1["coef"]
            ahat2 = mod2["coef"]
            temp1 = mod2["deviance"] - mod1["deviance"]
            temp2 = _det_abs(mod2["cov_unscaled"]) / _det_abs(mod1["cov_unscaled"])
            gs = math.exp(-temp1 / 2.0) / math.sqrt((2.0 * math.pi) ** d1 * temp2)
            if d1 == 1:
                r = _sgn(float(ahat[0])) * math.sqrt(temp1)
                v = float(ahat[0]) * math.sqrt(temp2)
                gs_cdf = _spa_from_r(r, v, LR, plus=False)
            else:
                gs_cdf = math.nan
            spa = np.array([gs, gs_cdf])
        else:
            spa = np.array([math.nan, math.nan])
            ahat = np.array([math.nan])
            ahat2 = np.array([math.nan])
        return {
            "spa": spa,
            "zeta.hat": np.asarray(ahat, dtype=float).reshape(-1),
            "zeta2.hat": np.asarray(ahat2, dtype=float).reshape(-1),
        }

    if wdist == "b":
        if type != "cond":
            raise ValueError("this type not implemented for Binary")
        solved = _simplex(
            np.zeros(n),
            A1=np.eye(n),
            b1=np.full(n, 1.0 - 2e-6),
            A3=A.T,
            b3=u - 1e-6 * A.sum(axis=0),
        )
        if solved.solved == 1:
            y = np.asarray(solved.soln, dtype=float) + 1e-6
            design2 = A[:, d1:]
            offset = np.log(mu / (1.0 - mu))
            weights = np.ones(n)
            mod1 = _glm_fit(A, y, "binomial", offset, weights)
            mod2 = _glm_fit(design2, y, "binomial", offset, weights)
            ahat = mod1["coef"]
            ahat2 = mod2["coef"]
            temp1 = mod2["deviance"] - mod1["deviance"]
            temp2 = _det_abs(mod2["cov_unscaled"]) / _det_abs(mod1["cov_unscaled"])
            gs = math.exp(-temp1 / 2.0) / math.sqrt((2.0 * math.pi) ** d1 * temp2)
            if d1 == 1:
                r = _sgn(float(ahat[0])) * math.sqrt(temp1)
                v = float(ahat[0]) * math.sqrt(temp2)
                gs_cdf = _spa_from_r(r, v, LR, plus=False)
            else:
                gs_cdf = math.nan
            spa = np.array([gs, gs_cdf])
        else:
            spa = np.array([math.nan, math.nan])
            ahat = np.array([math.nan])
            ahat2 = np.array([math.nan])
        return {
            "spa": spa,
            "zeta.hat": np.asarray(ahat, dtype=float).reshape(-1),
            "zeta2.hat": np.asarray(ahat2, dtype=float).reshape(-1),
        }

    raise ValueError(f"wdist must be 'm', 'p', 'b', or 'o', not {wdist!r}")


def _basis_matrix(xs: np.ndarray, knots: np.ndarray, order: int = 4) -> np.ndarray:
    """Cox-de Boor basis. The last positive span includes its right endpoint."""
    xs = np.asarray(xs, dtype=float)
    knots = np.asarray(knots, dtype=float)
    n_span = len(knots) - 1
    degree0 = np.zeros((xs.size, n_span))
    last = None
    for i in range(n_span):
        if knots[i + 1] > knots[i]:
            last = i
    for i in range(n_span):
        left = knots[i]
        right = knots[i + 1]
        if right <= left:
            continue
        if i == last:
            degree0[:, i] = (xs >= left) & (xs <= right)
        else:
            degree0[:, i] = (xs >= left) & (xs < right)
    current = degree0
    for k in range(2, order + 1):
        n_col = len(knots) - k
        nxt = np.zeros((xs.size, n_col))
        for i in range(n_col):
            left_gap = knots[i + k - 1] - knots[i]
            right_gap = knots[i + k] - knots[i + 1]
            left = np.zeros(xs.size)
            right = np.zeros(xs.size)
            if left_gap > 0.0:
                left = (xs - knots[i]) / left_gap * current[:, i]
            if right_gap > 0.0:
                right = (knots[i + k] - xs) / right_gap * current[:, i + 1]
            nxt[:, i] = left + right
        current = nxt
    return current


def _basis_derivative(xs: np.ndarray, knots: np.ndarray, order: int = 4) -> np.ndarray:
    """Derivative of the order-4 basis with respect to the scaled coordinate."""
    lower = _basis_matrix(xs, knots, order=order - 1)
    n_col = len(knots) - order
    out = np.zeros((xs.size, n_col))
    degree = order - 1
    for i in range(n_col):
        left_gap = knots[i + degree] - knots[i]
        right_gap = knots[i + order] - knots[i + 1]
        if left_gap > 0.0:
            out[:, i] += degree / left_gap * lower[:, i]
        if right_gap > 0.0:
            out[:, i] -= degree / right_gap * lower[:, i + 1]
    return out


def _bernstein(u: np.ndarray) -> np.ndarray:
    u = np.asarray(u, dtype=float)
    one = 1.0 - u
    return np.column_stack(
        [one**3, 3.0 * u * one**2, 3.0 * u**2 * one, u**3]
    )


def _sgram(knots: np.ndarray) -> np.ndarray:
    """Penalty matrix matching R's sgram on each positive knot span."""
    knots = np.asarray(knots, dtype=float)
    n_basis = len(knots) - 4
    omega = np.zeros((n_basis, n_basis))
    bern = _bernstein(_BERN_U)
    for i in range(3, len(knots) - 1):
        width = float(knots[i + 1] - knots[i])
        if width <= 0.0:
            continue
        cols = [i - 3, i - 2, i - 1, i]
        if cols[0] < 0 or cols[-1] >= n_basis:
            continue
        sample = knots[i] + width * _BERN_U
        local = _basis_matrix(sample, knots)[:, cols]
        change = np.linalg.solve(bern, local)
        gram = change.T @ (_SGRAM_BERN / width**3) @ change
        for a, ia in enumerate(cols):
            for b, ib in enumerate(cols):
                omega[ia, ib] += gram[a, b]
    return 0.5 * (omega + omega.T)


def _nknots_smspl(n: int) -> int:
    if n < 50:
        return n
    a1, a2, a3, a4 = math.log2(50), math.log2(100), math.log2(140), math.log2(200)
    if n < 200:
        raw = 2 ** (a1 + (a2 - a1) * (n - 50) / 150)
    elif n < 800:
        raw = 2 ** (a2 + (a3 - a2) * (n - 200) / 600)
    elif n < 3200:
        raw = 2 ** (a3 + (a4 - a3) * (n - 800) / 2400)
    else:
        raw = 200 + (n - 3200) ** 0.2
    return int(math.trunc(raw))


def _smooth_spline(x, y, w=None) -> dict:
    """GCV smoothing spline on the scale R's smooth.spline uses for n < 50."""
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    n = int(x.size)
    if w is None:
        w = np.ones(n)
        no_weights = True
    else:
        w = np.asarray(w, dtype=float).reshape(-1)
        w = w * np.sum(w > 0.0) / np.sum(w)
        no_weights = False
    iqr = float(np.percentile(x, 75) - np.percentile(x, 25))
    tol = 1e-6 * iqr
    if not math.isfinite(tol) or tol <= 0.0:
        span = float(np.max(x) - np.min(x))
        tol = 1e-6 * span if span > 0.0 else 1e-6
    xx = np.round((x - float(np.mean(x))) / tol)
    order = np.argsort(x, kind="mergesort")
    xxs = xx[order]
    keep = np.empty(n, dtype=bool)
    keep[0] = True
    keep[1:] = xxs[:-1] < xxs[1:]
    ux = x[order][keep]
    nx = int(ux.size)
    if nx <= 3:
        raise ValueError("need at least four unique 'x' values")
    if nx == n:
        wbar = w[order]
        ybar = y[order]
    else:
        codes = np.empty(n, dtype=int)
        rank = np.empty(n, dtype=int)
        rank[order] = np.arange(n)
        group = np.cumsum(keep) - 1
        codes[order] = group
        wbar = np.zeros(nx)
        y_sum = np.zeros(nx)
        for i in range(n):
            wbar[codes[i]] += w[i]
            y_sum[codes[i]] += w[i] * y[i]
        ybar = y_sum / np.where(wbar > 0.0, wbar, 1.0)
    r_ux = float(ux[-1] - ux[0])
    xbar = (ux - ux[0]) / r_ux
    nknots = _nknots_smspl(nx)
    if nknots == nx:
        inner = xbar
    else:
        idx = np.trunc(np.linspace(1, nx, nknots)).astype(int) - 1
        inner = xbar[idx]
    knots = np.concatenate([np.repeat(xbar[0], 3), inner, np.repeat(xbar[-1], 3)])
    basis = _basis_matrix(xbar, knots)
    omega = _sgram(knots)
    gram = basis.T @ (basis * wbar[:, None])
    rhs = basis.T @ (wbar * ybar)
    ratio = float(np.trace(gram) / np.trace(omega))

    def fit_lambda(lam: float):
        # Penalized least squares, stacked so the null space of an
        # interpolating Gram matrix does not depend on a banded factorization.
        sw = np.sqrt(np.maximum(wbar, 0.0))
        target = np.concatenate([sw * ybar, np.zeros(basis.shape[1])])
        evals, evecs = np.linalg.eigh(omega)
        factor = (evecs * np.sqrt(np.clip(evals, 0.0, None))) @ evecs.T
        stacked = np.vstack([basis * sw[:, None], math.sqrt(lam) * factor])
        coef = np.linalg.lstsq(stacked, target, rcond=None)[0]
        penalty = gram + lam * omega
        fitted = basis @ coef
        resid = ybar - fitted
        rss = float(np.sum(wbar * resid**2))
        try:
            smoother = gram @ np.linalg.solve(penalty, np.eye(penalty.shape[0]))
            df = float(np.trace(smoother))
        except np.linalg.LinAlgError:
            df = math.nan
        if (not math.isfinite(df)) or df <= 1.0 or (not math.isfinite(rss)) or rss < 0.0:
            crit = 1e300
        elif abs(nx - df) < 1e-15:
            crit = 1e300
        else:
            crit = nx * rss / (nx - df) ** 2
            if not math.isfinite(crit):
                crit = 1e300
        return coef, fitted, df, crit, rss

    def lam_of(spar: float) -> float:
        return ratio * 256.0 ** (3.0 * spar - 1.0)

    def raw_crit(spar: float) -> float:
        lam = lam_of(spar)
        if not math.isfinite(lam) or lam <= 0.0:
            return 1e300
        return fit_lambda(lam)[3]

    # The roundoff well, where df crosses n, undercuts the GCV bowl by orders
    # of magnitude. A five-point median removes the wiggles inside the bowl,
    # and the first minimum met while spar decreases is the one sbart keeps.
    spars = np.linspace(1.5, -1.5, 121)
    crits = np.array([raw_crit(float(sp)) for sp in spars])
    anchor = raw_crit(0.0)
    floor = anchor / 100.0 if anchor < 1e299 else 0.0
    crits = np.where(crits < floor, 1e300, crits)
    med = crits.copy()
    for i in range(2, len(crits) - 2):
        med[i] = np.median(crits[i - 2 : i + 3])
    pivot = int(np.argmin(med))
    for i in range(2, len(med) - 2):
        if med[i] <= med[i - 1] and med[i] <= med[i + 1] and med[i] < 1e299:
            pivot = i
            break
    spar = float(spars[pivot])
    lam = lam_of(spar)
    coef, fitted, df, crit, rss = fit_lambda(lam)
    return {
        "x": ux,
        "y": fitted,
        "w": wbar,
        "yin": ybar,
        "spar": float(spar),
        "lambda": float(lam),
        "ratio": ratio,
        "df": df,
        "cv_crit": crit,
        "pen_crit": rss,
        "knot": knots,
        "coef": coef,
        "min": float(ux[0]),
        "range": r_ux,
        "no_weights": no_weights,
    }


def _predict_spline(fit: dict, x_new, deriv: int = 0) -> np.ndarray:
    """Predict a smooth.spline. Outside the knots the line follows the end slope."""
    x_new = np.asarray(x_new, dtype=float).reshape(-1)
    xmin = fit["min"]
    span = fit["range"]
    u = (x_new - xmin) / span
    knots = fit["knot"]
    coef = fit["coef"]
    inside = (u >= 0.0) & (u <= 1.0)
    out = np.empty(u.size)
    if np.any(inside):
        out[inside] = _basis_matrix(u[inside], knots) @ coef
    if np.any(~inside):
        left = u < 0.0
        right = u > 1.0
        if np.any(left):
            y0 = float(_basis_matrix(np.array([0.0]), knots) @ coef)
            slope = float(_basis_derivative(np.array([0.0]), knots) @ coef)
            out[left] = y0 + u[left] * slope
        if np.any(right):
            y1 = float(_basis_matrix(np.array([1.0]), knots) @ coef)
            slope = float(_basis_derivative(np.array([1.0]), knots) @ coef)
            out[right] = y1 + (u[right] - 1.0) * slope
    if deriv == 0:
        return out
    slopes = np.empty(u.size)
    u_clip = np.clip(u, 0.0, 1.0)
    slopes = (_basis_derivative(u_clip, knots) @ coef) / span
    return slopes


def _zeta_row(sad: dict, width: int) -> np.ndarray:
    parts = [np.asarray(sad["zeta.hat"], dtype=float).reshape(-1)]
    if "zeta2.hat" in sad and sad["zeta2.hat"] is not None:
        parts.append(np.asarray(sad["zeta2.hat"], dtype=float).reshape(-1))
    vec = np.concatenate(parts) if parts else np.array([math.nan])
    if vec.size == width:
        return vec
    if vec.size == 0:
        return np.full(width, math.nan)
    reps = int(math.ceil(width / vec.size))
    return np.tile(vec, reps)[:width]


def _store_sad(zeta, spa, index_r: int, sad: dict, width: int):
    zeta[index_r - 1, :] = _zeta_row(sad, width)
    spa[index_r - 1, :] = np.asarray(sad["spa"], dtype=float).reshape(2)


def _saddle_at(A, u, wdist, type, init, mu, LR, strata):
    return saddle(
        A=A,
        u=u,
        wdist=wdist,
        type=type,
        d1=1,
        init=init,
        mu=mu,
        LR=LR,
        strata=strata,
    )


def saddle_distn(
    A,
    u=None,
    alpha=None,
    wdist="m",
    type="simp",
    npts=20,
    t=None,
    t0=None,
    init=None,
    mu=None,
    LR=False,
    strata=None,
    **kwargs,
):
    """Saddlepoint distribution approximation and its quantiles.

    A may be a matrix or a function of t. The spline is fit to the probit
    of the cdf approximations. The returned dict has quantiles, points,
    distn, call, and LR.
    """
    if alpha is None:
        alpha = np.array(
            [0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.2, 0.5, 0.8, 0.9, 0.95, 0.975, 0.99, 0.995, 0.999]
        )
    else:
        alpha = np.asarray(alpha, dtype=float).reshape(-1)
    if t is None and t0 is None:
        raise ValueError("one of 't' or 't0' required")
    if t is not None:
        t = np.asarray(t, dtype=float).reshape(-1)
        npts = int(t.size)
    else:
        t0 = np.asarray(t0, dtype=float).reshape(-1)
        npts = int(npts)
    ep1 = min(float(np.min(alpha)), 0.01) / 10.0
    ep2 = (1.0 - max(float(np.max(alpha)), 0.99)) / 10.0
    if type == "simp":
        d = 1
    elif callable(u):
        probe = float(t0[0] if t is None else t[0])
        d = int(np.atleast_1d(u(probe, **kwargs)).size)
    else:
        d = 1 + int(np.atleast_1d(u).size)
    width = 2 * d - 1
    zeta = np.full((npts, width), math.nan)
    spa = np.full((npts, 2), math.nan)
    pts: list[float] = []
    i = 0

    def low_bad(cdf):
        if _isna(cdf):
            return True
        return cdf > ep1 or cdf < ep1 / 100.0

    def high_bad(cdf):
        if _isna(cdf):
            return True
        return (1.0 - cdf) > ep2 or (1.0 - cdf) < ep2 / 100.0

    if callable(A):
        if u is None or not callable(u):
            raise ValueError("'u' must be a function")
        if t is None:
            t1 = float(t0[0] - 2.0 * t0[1])
            sad = _saddle_at(A(t1, **kwargs), u(t1, **kwargs), wdist, type, init, mu, LR, strata)
            bdu = bdl = None
            nsads = 0
            while low_bad(float(sad["spa"][1])):
                nsads += 1
                if (not _isna(sad["spa"][1])) and float(sad["spa"][1]) > ep1:
                    i += 1
                    _store_sad(zeta, spa, i, sad, width)
                    pts.append(t1)
                    bdu = t1
                else:
                    bdl = t1
                if nsads == npts:
                    raise RuntimeError("unable to find range")
                if bdl is None:
                    t1 = 2.0 * t1 - float(t0[0])
                elif bdu is None:
                    t1 = (float(t0[0]) + bdl) / 2.0
                else:
                    t1 = (bdu + bdl) / 2.0
                sad = _saddle_at(A(t1, **kwargs), u(t1, **kwargs), wdist, type, init, mu, LR, strata)
            i1 = i = i + 1
            _store_sad(zeta, spa, i, sad, width)
            pts.append(t1)
            t2 = float(t0[0] + 2.0 * t0[1])
            sad = _saddle_at(A(t2, **kwargs), u(t2, **kwargs), wdist, type, init, mu, LR, strata)
            bdu = bdl = None
            nsads = 0
            while high_bad(float(sad["spa"][1])):
                nsads += 1
                if (not _isna(sad["spa"][1])) and (1.0 - float(sad["spa"][1])) > ep2:
                    i += 1
                    _store_sad(zeta, spa, i, sad, width)
                    pts.append(t2)
                    bdl = t2
                else:
                    bdu = t2
                if nsads == npts:
                    raise RuntimeError("unable to find range")
                if bdu is None:
                    t2 = 2.0 * t2 - float(t0[0])
                elif bdl is None:
                    t2 = (float(t0[0]) + bdu) / 2.0
                else:
                    t2 = (bdu + bdl) / 2.0
                sad = _saddle_at(A(t2, **kwargs), u(t2, **kwargs), wdist, type, init, mu, LR, strata)
            i = i + 1
            _store_sad(zeta, spa, i, sad, width)
            pts.append(t2)
            if npts % 2 == 0:
                tt1 = _seq_int(t1, float(t0[0]), npts / 2 - i1 + 2)[1:]
                tt2 = _seq_int(float(t0[0]), t2, npts / 2 + i1 - i + 2)[1:]
                t = np.concatenate([tt1[:-1], tt2[:-1]])
            else:
                ex = 1 if (t1 + t2) > 2.0 * float(t0[0]) else 0
                ll = npts // 2 + 2
                tt1 = _seq_int(t1, float(t0[0]), ll - i1 + 1 - ex)[1:]
                tt2 = _seq_int(float(t0[0]), t2, ll + i1 - i + ex)[1:]
                t = np.concatenate([tt1[:-1], tt2[:-1]])
        init1 = None if init is None else np.asarray(init, dtype=float).copy()
        for j in _colon(i + 1, npts):
            tj = float(t[j - i - 1])
            sad = _saddle_at(A(tj, **kwargs), u(tj, **kwargs), wdist, type, init1, mu, LR, strata)
            _store_sad(zeta, spa, j, sad, width)
            init1 = np.asarray(sad["zeta.hat"], dtype=float).copy()
    else:
        A = _as_2d(A)
        if u is None:
            u_fixed = np.zeros(0)
        else:
            u_fixed = np.asarray(u, dtype=float).reshape(-1)
        if t is None:
            t1 = float(t0[0] - 2.0 * t0[1])
            sad = _saddle_at(A, np.concatenate([[t1], u_fixed]), wdist, type, init, mu, LR, strata)
            bdu = bdl = None
            while low_bad(float(sad["spa"][1])):
                if (not _isna(sad["spa"][1])) and float(sad["spa"][1]) > ep1:
                    i += 1
                    _store_sad(zeta, spa, i, sad, width)
                    pts.append(t1)
                    bdu = t1
                else:
                    bdl = t1
                if i == npts // 2:
                    raise RuntimeError("unable to find range")
                if bdl is None:
                    t1 = 2.0 * t1 - float(t0[0])
                elif bdu is None:
                    t1 = (float(t0[0]) + bdl) / 2.0
                else:
                    t1 = (bdu + bdl) / 2.0
                sad = _saddle_at(A, np.concatenate([[t1], u_fixed]), wdist, type, init, mu, LR, strata)
            i1 = i = i + 1
            _store_sad(zeta, spa, i, sad, width)
            pts.append(t1)
            t2 = float(t0[0] + 2.0 * t0[1])
            sad = _saddle_at(A, np.concatenate([[t2], u_fixed]), wdist, type, init, mu, LR, strata)
            bdu = bdl = None
            while high_bad(float(sad["spa"][1])):
                if (not _isna(sad["spa"][1])) and (1.0 - float(sad["spa"][1])) > ep2:
                    i += 1
                    _store_sad(zeta, spa, i, sad, width)
                    pts.append(t2)
                    bdl = t2
                else:
                    bdu = t2
                if (i - i1) == npts // 2:
                    raise RuntimeError("unable to find range")
                if bdu is None:
                    t2 = 2.0 * t2 - float(t0[0])
                elif bdl is None:
                    t2 = (float(t0[0]) + bdu) / 2.0
                else:
                    t2 = (bdu + bdl) / 2.0
                sad = _saddle_at(A, np.concatenate([[t2], u_fixed]), wdist, type, init, mu, LR, strata)
            i = i + 1
            _store_sad(zeta, spa, i, sad, width)
            pts.append(t2)
            if npts % 2 == 0:
                tt1 = _seq_int(t1, float(t0[0]), npts / 2 - i1 + 2)[1:]
                tt2 = _seq_int(float(t0[0]), t2, npts / 2 + i1 - i + 2)[1:]
                t = np.concatenate([tt1[:-1], tt2[:-1]])
            else:
                ex = 1 if (t1 + t2) > 2.0 * float(t0[0]) else 0
                ll = npts // 2 + 2
                tt1 = _seq_int(t1, float(t0[0]), ll - i1 + 1 - ex)[1:]
                tt2 = _seq_int(float(t0[0]), t2, ll + i1 - i + ex)[1:]
                t = np.concatenate([tt1[:-1], tt2[:-1]])
        for j in _colon(i + 1, npts):
            # The matrix path computes init1 and then ignores it.
            tj = float(t[j - i - 1])
            sad = _saddle_at(
                A, np.concatenate([[tj], u_fixed]), wdist, type, init, mu, LR, strata
            )
            _store_sad(zeta, spa, j, sad, width)

    t_all = np.concatenate([np.asarray(pts, dtype=float), np.asarray(t, dtype=float)])
    keep = (np.abs(zeta[:, 0]) > 1e-6) & (np.abs(spa[:, 1] - 0.5) < 0.5 - 1e-10)
    pts_k = t_all[keep]
    zeta_k = np.atleast_2d(zeta[keep])
    spa_k = np.atleast_2d(spa[keep])
    distn = _smooth_spline(_qnorm_vec(spa_k[:, 1]), pts_k)
    predicted = _predict_spline(distn, _qnorm_vec(alpha))
    quans = np.column_stack([alpha, predicted])
    order = np.argsort(pts_k, kind="mergesort")
    psa = np.column_stack([pts_k[order], spa_k[order, :], zeta_k[order, :]])
    if d == 1:
        names = ["t", "gs", "Gs", "zeta"]
    else:
        names = ["t", "gs", "Gs"]
        names += [f"zeta1.{j}" for j in range(1, d + 1)]
        names += [f"zeta2.{j}" for j in range(1, d)]
    return {
        "quantiles": quans,
        "points": psa,
        "points_names": names,
        "distn": distn,
        "call": "saddle_distn()",
        "LR": bool(LR),
    }


def _r_round(values, digits: int) -> np.ndarray:
    scale = 10.0**digits
    scaled = np.asarray(values, dtype=float) * scale
    rounded = np.round(scaled)
    # R rounds a fractional part of exactly .5 to even, matching np.round
    # on binary ties that are exact. Re-apply that only at exact halves.
    return rounded / scale


def print_saddle_distn(x, **_unused) -> str:
    """Print quantile approximations and return that text."""
    points = np.asarray(x["points"], dtype=float)
    quantiles = np.asarray(x["quantiles"], dtype=float)
    rg = np.array([np.min(points[:, 0]), np.max(points[:, 0])])
    mid = float(np.mean(rg))
    digs = math.ceil(math.log10(abs(mid))) if mid != 0.0 else 0
    if digs <= 0:
        digs = 4
    elif digs >= 4:
        digs = 0
    else:
        digs = 4 - digs
    rg_r = _r_round(rg, digs)
    level = 100.0 * quantiles[:, 0]
    rounded = _r_round(quantiles, digs)
    lines = ["\nSaddlepoint Distribution Approximations\n\n", "Call : \n", str(x.get("call", "saddle_distn()")), "\n"]
    if not str(x.get("call", "")).endswith("\n"):
        lines.append("\n")
    lines.append("\nQuantiles of the Distribution\n")
    for i in range(quantiles.shape[0]):
        lines.append(f"\n{level[i]:g}%     {rounded[i, 1]:.{digs}f}")
    lines.append(
        f"\n\nSmoothing spline used {points.shape[0]} points in the range "
        f"{rg_r[0]:.{digs}f} to {rg_r[1]:.{digs}f}.\n"
    )
    if x.get("LR"):
        lines.append("Lugananni-Rice approximations used\n")
    text = "".join(lines)
    print(text, end="")
    return text


def _linestyle(lty) -> str:
    mapping = {1: "solid", 2: "dashed", 3: "dotted", 4: "dashdot", 5: "dashdot", 6: "dashdot"}
    if isinstance(lty, str):
        return lty
    return mapping.get(int(lty), "solid")


def lines_saddle_distn(x, dens=True, h=None, J=None, npts=50, lty=1, ax=None, **extra):
    """Add a saddlepoint density or cdf line and return the coordinates drawn."""
    import matplotlib.pyplot as plt

    if h is None:
        def h(u, **_k):
            return np.asarray(u, dtype=float)
    if J is None:
        def J(u, **_k):
            return np.ones(np.asarray(u, dtype=float).shape)
    tt = np.asarray(x["points"][:, 0], dtype=float)
    transformed = np.asarray(h(tt, **extra), dtype=float).reshape(-1)
    rg = np.array([float(np.min(transformed)), float(np.max(transformed))])
    tt1 = np.linspace(rg[0], rg[1], int(npts))
    if dens:
        gs = np.asarray(x["points"][:, 1], dtype=float)
        jacobian = np.asarray(J(tt, **extra), dtype=float).reshape(-1)
        spl = _smooth_spline(transformed, np.log(gs * jacobian))
        yy = np.exp(_predict_spline(spl, tt1))
    else:
        gs_cdf = np.asarray(x["points"][:, 2], dtype=float)
        spl = _smooth_spline(transformed, _qnorm_vec(gs_cdf))
        yy = np.array([_pnorm(float(v)) for v in _predict_spline(spl, tt1)])
    if ax is None:
        ax = plt.gca()
    ax.plot(tt1, yy, linestyle=_linestyle(lty))
    return {"x": tt1, "y": yy}
