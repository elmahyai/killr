"""Frisch-Newton interior point solver used by rq.fit.fnb.

This is the Fortran lpfnb / stepy loop. The coefficient R returns is the
negated dual variable stored in the first p entries of wp.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.linalg.lapack import dposv, dpotrs


def _as_observations(x):
    """Fortran a(p, n): one column per observation."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    return np.ascontiguousarray(design.T)


def _stepy(a, d, rhs):
    """Upper Cholesky solve of (A diag(d) A') y = rhs. Returns y and the factor."""
    gram = np.zeros((a.shape[0], a.shape[0]), dtype=float, order="F")
    scaled = a * d
    gram += scaled @ a.T
    factor, solution, info = dposv(gram, np.array(rhs, dtype=float, order="F").reshape(-1, 1), lower=0, overwrite_a=1, overwrite_b=1)
    if info != 0:
        raise np.linalg.LinAlgError(f"stepy info {info}")
    return np.array(solution, dtype=float).reshape(-1), np.array(factor, dtype=float, order="F")


def _potrs(factor, rhs):
    solution, info = dpotrs(factor, np.array(rhs, dtype=float, order="F").reshape(-1, 1), lower=0, overwrite_b=1)
    if info != 0:
        raise np.linalg.LinAlgError(f"dpotrs info {info}")
    return np.array(solution, dtype=float).reshape(-1)


def lpfnb(a, c, b, u, x, beta=0.99995, eps=1e-6):
    """One primal-dual step sequence. a is p by n, as in the Fortran argument."""
    n = c.shape[0]
    p = b.shape[0]
    nit = np.array([0, 0, n], dtype=int)
    y = a @ c
    d = np.ones(n)
    try:
        y, factor = _stepy(a, d, y)
    except np.linalg.LinAlgError:
        return {"y": y, "nit": nit, "info": 1}
    s = c - a.T @ y
    z = np.empty(n)
    w = np.empty(n)
    small = np.abs(s) < eps
    z[small] = np.maximum(s[small], 0.0) + eps
    w[small] = np.maximum(-s[small], 0.0) + eps
    z[~small] = np.maximum(s[~small], 0.0)
    w[~small] = np.maximum(-s[~small], 0.0)
    s = np.array(u, dtype=float) - x
    upper = np.array(u, dtype=float)
    gap = float(z @ x + w @ s)
    big = 1.0e20
    maxit = 500
    while gap > eps and nit[0] < maxit:
        nit[0] += 1
        d = 1.0 / (z / x + w / s)
        ds = z - w
        dz = d * ds
        dy = b - a @ x + a @ dz
        rhs = dy.copy()
        try:
            dy, factor = _stepy(a, d, dy)
        except np.linalg.LinAlgError:
            return {"y": y, "nit": nit, "info": 1}
        ds = a.T @ dy - ds
        dx = d * ds
        ds = -dx
        dz = -z * (dx / x + 1.0)
        dw = -w * (ds / s + 1.0)
        deltap = big
        deltad = big
        neg = dx < 0
        if np.any(neg):
            deltap = min(deltap, np.min(-x[neg] / dx[neg]))
        neg = ds < 0
        if np.any(neg):
            deltap = min(deltap, np.min(-s[neg] / ds[neg]))
        neg = dz < 0
        if np.any(neg):
            deltad = min(deltad, np.min(-z[neg] / dz[neg]))
        neg = dw < 0
        if np.any(neg):
            deltad = min(deltad, np.min(-w[neg] / dw[neg]))
        deltap = min(beta * deltap, 1.0)
        deltad = min(beta * deltad, 1.0)
        if min(deltap, deltad) < 1.0:
            nit[1] += 1
            mu = float(x @ z + s @ w)
            g = (
                mu
                + deltap * float(dx @ z)
                + deltad * float(dz @ x)
                + deltap * deltad * float(dz @ dx)
                + deltap * float(ds @ w)
                + deltad * float(dw @ s)
                + deltap * deltad * float(ds @ dw)
            )
            mu = mu * ((g / mu) ** 3) / (2.0 * n)
            dr = d * (mu * (1.0 / s - 1.0 / x) + dx * dz / x - ds * dw / s)
            dy, rhs = rhs, dy
            dy = dy + a @ dr
            dy = _potrs(factor, dy)
            upper = a.T @ dy
            dxdz = dx * dz
            dsdw = ds * dw
            dx = d * (upper - z + w) - dr
            ds = -dx
            dz = -z + (mu - z * dx - dxdz) / x
            dw = -w + (mu - w * ds - dsdw) / s
            deltap = big
            deltad = big
            neg = dx < 0
            if np.any(neg):
                deltap = min(deltap, np.min(-x[neg] / dx[neg]))
            neg = ds < 0
            if np.any(neg):
                deltap = min(deltap, np.min(-s[neg] / ds[neg]))
            neg = dz < 0
            if np.any(neg):
                deltad = min(deltad, np.min(-z[neg] / dz[neg]))
            neg = dw < 0
            if np.any(neg):
                deltad = min(deltad, np.min(-w[neg] / dw[neg]))
            deltap = min(beta * deltap, 1.0)
            deltad = min(beta * deltad, 1.0)
        x = x + deltap * dx
        s = s + deltap * ds
        y = y + deltad * dy
        z = z + deltad * dz
        w = w + deltad * dw
        gap = float(z @ x + w @ s)
    return {"y": y, "nit": nit, "info": 0}


def _fnb_coefficient(design, response, rhs, x0, beta, eps):
    solved = lpfnb(
        _as_observations(design),
        -np.asarray(response, dtype=float).reshape(-1),
        np.asarray(rhs, dtype=float).reshape(-1),
        np.ones(design.shape[0]),
        np.asarray(x0, dtype=float).reshape(-1),
        beta=float(beta),
        eps=float(eps),
    )
    if solved["info"] != 0:
        return -solved["y"], solved["nit"], solved["info"]
    coefficient = -solved["y"]
    return coefficient, solved["nit"], solved["info"]


def rq_fit_lasso(x, y, tau=0.5, lambda_=None, beta=0.99995, eps=1e-6):
    """Penalized quantile fit. A length-1 lambda is applied to every slope."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    tau = float(tau)
    if lambda_ is None:
        from quantreg.more import lasso_lambda_hat

        penalty = lasso_lambda_hat(design, tau=tau)
    else:
        penalty = np.asarray(lambda_, dtype=float).reshape(-1)
        if penalty.size == 1:
            penalty = np.concatenate([np.zeros(1), np.repeat(float(penalty.reshape(-1)[0]), p - 1)])
        elif penalty.size != p:
            raise ValueError(f"lambda must be either of length  {p} or length one")
    if np.any(penalty < 0):
        raise ValueError("negative lambdas disallowed")
    if tau < eps or tau > 1.0 - eps:
        raise ValueError("No parametric Frisch-Newton method.  Set tau in (0,1)")
    keep = penalty != 0
    extra = np.diag(penalty)[keep]
    stacked_x = np.vstack([design, extra]) if extra.size else design
    stacked_y = np.concatenate([response, np.zeros(extra.shape[0])])
    column_sum = extra.sum(axis=0) if extra.size else np.zeros(p)
    rhs = (1.0 - tau) * design.sum(axis=0) + 0.5 * column_sum
    coefficient, nit, info = _fnb_coefficient(
        stacked_x, stacked_y, rhs, np.full(stacked_y.size, 0.5), beta, eps
    )
    if info != 0:
        raise RuntimeError(f"Error info =  {info} in stepy2: singular design")
    return {
        "coefficients": coefficient,
        "residuals": response - design @ coefficient,
        "tau": tau,
        "lambda": penalty,
        "it": nit,
    }


def _dscad(values, alpha, penalty):
    values = np.asarray(values, dtype=float)
    magnitude = np.abs(values)
    return penalty * np.sign(values) * (magnitude <= penalty) + np.sign(values) * (alpha * penalty - magnitude) / (
        alpha - 1.0
    ) * (magnitude <= alpha * penalty) * (magnitude > penalty)


def rq_fit_scad(x, y, tau=0.5, alpha=3.2, lambda_=1.0, start="rq", beta=0.9995, eps=1e-6):
    """SCAD-penalized quantile regression, iterated from an fnb or lasso start."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    tau = float(tau)
    eps = float(eps)
    if tau < eps or tau > 1.0 - eps:
        raise ValueError("No parametric Frisch-Newton method.  Set tau in (0,1)")
    penalty = np.asarray(lambda_, dtype=float).reshape(-1)
    if penalty.size == 1:
        penalty = np.concatenate([np.zeros(1), np.repeat(float(penalty.reshape(-1)[0]), p - 1)])
    if penalty.size != p:
        raise ValueError(f"lambda must be either of length  {p} or length one")
    if np.any(penalty < 0):
        raise ValueError("negative lambdas disallowed")
    keep = penalty != 0
    extra = np.diag(penalty)[keep]
    stacked_x = np.vstack([design, extra])
    stacked_y = np.concatenate([response, np.zeros(extra.shape[0])])
    rhs = (1.0 - tau) * design.sum(axis=0) + extra.sum(axis=0)
    if start == "rq":
        slopes = rq_fit_fnb(design, response, tau=tau)["coefficients"][1:]
    elif start == "lasso":
        slopes = rq_fit_lasso(design, response, tau=tau, lambda_=penalty)["coefficients"][1:]
    else:
        raise ValueError(f"unknown start {start}")
    coefficient = np.full(p, np.finfo(float).max)
    # dscad() is called with its own defaults, a=3.7 and lambda=2, not alpha.
    adjustment = rhs - np.concatenate([np.zeros(1), _dscad(slopes, 3.7, 2.0) * np.sign(slopes)])
    nit = None
    info = 0
    with np.errstate(over="ignore"):
        changed = not np.isfinite(np.max(np.abs(slopes - coefficient[1:]))) or np.max(np.abs(slopes - coefficient[1:])) > eps
    while changed:
        slopes = coefficient[1:]
        x0 = np.concatenate([np.full(n, 1.0 - tau), np.full(extra.shape[0], 0.5)])
        coefficient, nit, info = _fnb_coefficient(
            stacked_x, stacked_y, rhs - adjustment, x0, beta, eps
        )
        adjustment = np.concatenate(
            [np.zeros(1), _dscad(coefficient[1:], 3.7, 2.0) * np.sign(coefficient[1:])]
        )
        with np.errstate(over="ignore"):
            gap = np.max(np.abs(slopes - coefficient[1:]))
        changed = not np.isfinite(gap) or gap > eps
    if info:
        raise RuntimeError(f"Error info =  {info} in stepy2: singular design")
    return {
        "coefficients": coefficient,
        "residuals": response - design @ coefficient,
        "tau": tau,
        "lambda": penalty,
        "it": nit,
    }


def rq_fit_hogg(x, y, taus=(0.1, 0.3, 0.5), weights=(0.7, 0.2, 0.1), constraints=None, bound=None, beta=0.99995, eps=1e-6):
    """Composite quantile regression. constraints and bound are R and r."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    taus = np.atleast_1d(np.asarray(taus, dtype=float))
    weights = np.atleast_1d(np.asarray(weights, dtype=float))
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    if taus.size != weights.size:
        raise ValueError("taus and weights differ in length")
    eps = float(eps)
    if np.any(taus < eps) or np.any(taus > 1.0 - eps):
        raise ValueError("taus outside (0,1)")
    intercepts = np.repeat(weights, n)
    slopes = np.repeat(weights, n)[:, None] * np.tile(design, (weights.size, 1))
    # kronecker(diag(weights), ones) places each weight in its own intercept column.
    intercept = np.zeros((n * weights.size, weights.size))
    for i, weight in enumerate(weights):
        intercept[i * n : (i + 1) * n, i] = weight
    expanded_x = np.column_stack([intercept, slopes])
    expanded_y = np.tile(response, weights.size) * intercepts
    level = float(np.sum(weights * (1.0 - taus)))
    rhs = np.concatenate([weights * (1.0 - taus) * n, level * design.sum(axis=0)])
    if constraints is not None:
        from quantreg.constrained import lpfnc

        constraints = np.asarray(constraints, dtype=float)
        if constraints.ndim == 1:
            constraints = constraints.reshape(1, -1)
        bound = np.zeros(constraints.shape[0]) if bound is None else np.asarray(bound, dtype=float).reshape(-1)
        if constraints.shape[0] != bound.shape[0]:
            raise ValueError("R and r of incompatible dimension")
        if constraints.shape[1] != expanded_x.shape[1]:
            raise ValueError("R and X of incompatible dimension")
        solved = lpfnc(
            _as_observations(expanded_x),
            -expanded_y,
            _as_observations(constraints),
            -bound,
            rhs,
            np.ones(max(expanded_y.size, bound.size)),
            np.full(expanded_y.size, 0.5),
            np.ones(bound.size),
            beta=float(beta),
            eps=eps,
        )
        if solved["info"] != 0:
            import warnings

            warnings.warn(
                f"Info =  {solved['info']} in stepy: singular design: iterations  {solved['nit'][0]}",
                stacklevel=2,
            )
        return {"coefficients": -solved["y"], "nit": solved["nit"], "flag": solved["info"]}
    coefficient, nit, info = _fnb_coefficient(
        expanded_x, expanded_y, rhs, np.full(expanded_y.size, 0.5), beta, eps
    )
    return {"coefficients": coefficient, "nit": nit, "flag": info}


def rq_fit_pfn(x, y, tau=0.5, mm_factor=0.8, max_bad_fixups=3, eps=1e-6):
    """Preprocessed Frisch-Newton fit. The subsample is R's sample without replacement."""
    from boot.rng import sample_int

    from quantreg.orderstats import kuantile

    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    tau = float(tau)
    if tau < 0 or tau > 1:
        raise ValueError("tau outside (0,1)")
    m = int(np.round(np.sqrt(p) * n ** (2.0 / 3.0)))
    not_optimal = True
    ifix = 0
    ibad = 0
    solved = None
    while not_optimal:
        ibad += 1
        if m < n:
            chosen = np.array(sample_int(n, m, replace=False), dtype=int) - 1
        else:
            solved = rq_fit_fnb(design, response, tau=tau, eps=eps)
            break
        subset = rq_fit_fnb(design[chosen], response[chosen], tau=tau, eps=eps)
        gram = subset_design = design[chosen]
        factor = np.linalg.cholesky(subset_design.T @ subset_design)
        inverse = np.linalg.solve(factor.T, np.eye(p))
        band = np.sqrt(np.sum((design @ inverse) ** 2, axis=1))
        residual = response - design @ subset["coefficients"]
        span = mm_factor * m
        lo = max(1.0 / n, tau - span / (2.0 * n))
        hi = min(tau + span / (2.0 * n), (n - 1.0) / n)
        ratio = residual / np.maximum(eps, band)
        kappa = kuantile(ratio, [lo, hi])["y"]
        sl = residual < band * kappa[0]
        su = residual > band * kappa[1]
        bad_fixups = 0
        while not_optimal and bad_fixups < max_bad_fixups:
            ifix += 1
            keep = ~su & ~sl
            stacked_x = design[keep]
            stacked_y = response[keep]
            if np.any(sl):
                stacked_x = np.vstack([stacked_x, design[sl].sum(axis=0)])
                stacked_y = np.concatenate([stacked_y, [response[sl].sum()]])
            if np.any(su):
                stacked_x = np.vstack([stacked_x, design[su].sum(axis=0)])
                stacked_y = np.concatenate([stacked_y, [response[su].sum()]])
            solved = rq_fit_fnb(stacked_x, stacked_y, tau=tau, eps=eps)
            residual = response - design @ solved["coefficients"]
            su_bad = (residual < 0) & su
            sl_bad = (residual > 0) & sl
            if np.any(su_bad) or np.any(sl_bad):
                if np.sum(su_bad | sl_bad) > 0.1 * span:
                    import warnings

                    warnings.warn("Too many fixups:  doubling m", stacklevel=2)
                    bad_fixups += 1
                    m = 2 * m
                    break
                su = su & ~su_bad
                sl = sl & ~sl_bad
            else:
                not_optimal = False
    nit = np.concatenate([np.asarray(solved["nit"], dtype=int), [ifix, ibad]])
    return {"coefficients": solved["coefficients"], "tau": tau, "nit": nit}


def rq_fit_ppro(x, y, tau, weights=None, mm_factor=0.8, eps=1e-6):
    """Preprocess a grid of taus. Each new tau starts from the previous residual."""
    from quantreg.orderstats import kuantile

    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    taus = np.atleast_1d(np.asarray(tau, dtype=float))
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    if weights is not None:
        weights = np.asarray(weights, dtype=float).reshape(-1)
        if np.any(weights < 0):
            raise ValueError("negative weights not allowed")
        if weights.size != n:
            raise ValueError("weights not of length(y)")
        design = design * weights[:, None]
        response = response * weights
    gap = np.diff(taus)
    width = n * np.sqrt(p) * (np.max(gap) if gap.size else np.nan)
    coefficient = np.empty((p, taus.size))
    residual = np.empty((n, taus.size))
    rho = np.empty(taus.size)

    def fidelity(u, level):
        return float(np.sum(u * (level - (u < 0))))

    first = rq_fit_fnb(design, response, tau=float(taus[0]), eps=eps)
    current = first["residuals"]
    coefficient[:, 0] = first["coefficients"]
    rho[0] = fidelity(current, float(taus[0]))
    factor = np.linalg.cholesky(design.T @ design)
    inverse = np.linalg.solve(factor.T, np.eye(p))
    band = np.maximum(eps, np.sqrt(np.sum((design @ inverse) ** 2, axis=1)))
    for i in range(1, taus.size):
        not_optimal = True
        mm = width
        while not_optimal:
            span = mm_factor * mm
            lo = max(1.0 / n, float(taus[i]) - span / (2.0 * n))
            hi = min(float(taus[i]) + span / (2.0 * n), (n - 1.0) / n)
            kappa = kuantile(current / band, [lo, hi])["y"]
            sl = current < band * kappa[0]
            su = current > band * kappa[1]
            while not_optimal:
                keep = ~su & ~sl
                stacked_x = design[keep]
                stacked_y = response[keep]
                if np.any(sl):
                    stacked_x = np.vstack([stacked_x, design[sl].sum(axis=0)])
                    stacked_y = np.concatenate([stacked_y, [response[sl].sum()]])
                if np.any(su):
                    stacked_x = np.vstack([stacked_x, design[su].sum(axis=0)])
                    stacked_y = np.concatenate([stacked_y, [response[su].sum()]])
                solved = rq_fit_fnb(stacked_x, stacked_y, tau=float(taus[i]), eps=eps)
                current = response - design @ solved["coefficients"]
                su_bad = (current < 0) & su
                sl_bad = (current > 0) & sl
                bad = int(np.sum(su_bad | sl_bad))
                if bad > 0:
                    if bad > 0.1 * span:
                        mm = 2 * mm
                        import warnings

                        warnings.warn("Too many fixups:  doubling m", stacklevel=2)
                        break
                    su = su & ~su_bad
                    sl = sl & ~sl_bad
                else:
                    not_optimal = False
        coefficient[:, i] = solved["coefficients"]
        residual[:, i] = response - design @ solved["coefficients"]
        rho[i] = fidelity(residual[:, i], float(taus[i]))
    residual[:, 0] = response - design @ coefficient[:, 0]
    return {"coefficients": coefficient, "residuals": residual, "rho": rho, "weights": weights}


def rq_fit_fnb(x, y, tau=0.5, rhs=None, beta=0.99995, eps=1e-6):
    """rq.fit.fnb. The initial dual slack is 1 - tau."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    tau = float(tau)
    eps = float(eps)
    if tau < eps or tau > 1.0 - eps:
        raise ValueError("No parametric Frisch-Newton method.  Set tau in (0,1)")
    if rhs is None:
        rhs = (1.0 - tau) * design.sum(axis=0)
    rhs = np.asarray(rhs, dtype=float).reshape(-1)
    solved = lpfnb(
        _as_observations(design),
        -response,
        rhs,
        np.ones(n),
        np.full(n, 1.0 - tau),
        beta=float(beta),
        eps=eps,
    )
    if solved["info"] != 0:
        import warnings

        warnings.warn(
            f"Error info =  {solved['info']} in stepy: possibly singular design",
            stacklevel=2,
        )
    coefficient = -solved["y"]
    return {
        "coefficients": coefficient,
        "tau": tau,
        "residuals": response - design @ coefficient,
        "nit": solved["nit"],
        "info": solved["info"],
    }


def band_scale(design, basis, eps):
    """R's band: pmax(eps, sqrt(rowSums(((x %*% solve(chol(crossprod(basis))))^2)))).

    chol is the upper factor U with U'U = crossprod(basis), so solve(U) is U^-1.
    """
    gram = basis.T @ basis
    upper = np.linalg.cholesky(gram).T
    inverse = np.linalg.inv(upper)
    return np.maximum(eps, np.sqrt(np.sum((design @ inverse) ** 2, axis=1)))


def rq_fit_pfnb(x, y, tau=0.5, m0=None, eps=1e-6):
    """rq.fit.pfnb: preprocessed Frisch-Newton over each tau.

    The subsample is R's sample(n, m0) from boot's Mersenne-Twister, and its fit is the
    Frisch-Newton kernel. The duals, nit, and flags come from crates/quantreg. The
    coefficient is the negated dual, as in R.
    """
    from boot.rng import sample_int

    from quantreg._kernel import fnb, pfnb

    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    taus = np.atleast_1d(np.asarray(tau, dtype=float))
    if m0 is None:
        m0 = math.floor(n ** (2.0 / 3.0) * math.sqrt(p))
    sample = np.asarray(sample_int(n, int(m0)), dtype=int) - 1
    xs = design[sample]
    ys = response[sample]
    subfit = fnb(xs, ys, taus[0])
    residuals = response - design @ subfit["coefficients"]
    band = band_scale(design, xs, eps)
    duals, nit, info = pfnb(design, response, taus, residuals, band, int(m0))
    flag = np.zeros(taus.size, dtype=int)
    flag[0] = info
    return {
        "coefficients": -duals,
        "dual": duals,
        "nit": nit,
        "flag": flag,
    }


def rq_fit_qfnb(x, y, tau):
    """One fnb fit per tau. The workspace is reset the way qfnb resets it."""
    design = np.asarray(x, dtype=float)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    response = np.asarray(y, dtype=float).reshape(-1)
    taus = np.atleast_1d(np.asarray(tau, dtype=float))
    n, p = design.shape
    a = _as_observations(design)
    columns = []
    nit = np.zeros(3, dtype=int)
    info = 0
    for value in taus:
        solved = lpfnb(
            a,
            -response,
            (1.0 - float(value)) * design.sum(axis=0),
            np.ones(n),
            np.full(n, 1.0 - float(value)),
            beta=0.99995,
            eps=1e-6,
        )
        nit = solved["nit"]
        info = solved["info"]
        if info != 0:
            import warnings

            warnings.warn(
                f"Info =  {info} in stepy: singular design: nit =  {nit[0]}",
                stacklevel=2,
            )
            break
        columns.append(-solved["y"])
    if not columns:
        coefficient = np.full((p, 0), np.nan)
    else:
        coefficient = np.column_stack(columns)
    return {"coefficients": coefficient, "nit": nit, "flag": info}
