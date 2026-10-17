"""Row and weighted bootstraps of the quantile regression linear program."""

from __future__ import annotations

import math

import numpy as np
from boot.rng import sample_int

from quantreg.fit import _as_matrix, rq_fit_br, rq_wfit


def boot_rq_xy(x, y, s, tau=0.5):
    """One regression quantile on each column of row indices. Indices are 1-based."""
    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    index = np.asarray(s, dtype=int)
    if index.ndim == 1:
        index = index.reshape(-1, 1)
    rows = []
    for column in range(index.shape[1]):
        chosen = index[:, column] - 1
        fit = rq_fit_br(design[chosen], response[chosen], tau=float(tau))
        rows.append(fit["coefficients"])
    return np.vstack(rows)


def boot_rq_wxy(x, y, w, tau=0.5):
    """One weighted regression quantile for each column of exponential weights."""
    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    weight = np.asarray(w, dtype=float)
    if weight.ndim == 1:
        weight = weight.reshape(-1, 1)
    rows = []
    for column in range(weight.shape[1]):
        fit = rq_wfit(design, response, tau=float(tau), weights=weight[:, column])
        rows.append(fit["coefficients"])
    return np.vstack(rows)


def boot_rq(x, y, tau=0.5, r=200, bsmethod="xy", mofn=None, u=None):
    """Bootstrap coefficients. xy resamples rows. wxy weights them by rexp.

    jack deletes about 2*sqrt(n) rows. The other methods in R call Fortran
    that is not this linear program, and they are left open.
    """
    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    tau = float(tau)
    if tau < 0 or tau > 1:
        raise ValueError("tau outside (0,1) not allowed")
    replicates = int(r)
    if bsmethod == "xy":
        if mofn is None:
            mofn = n
        if u is None:
            if mofn < p or mofn > n:
                raise ValueError("mofn is out of range")
            draws = sample_int(n, int(mofn) * replicates, replace=True)
            u = np.asarray(draws, dtype=int).reshape((int(mofn), replicates), order="F")
        scale = math.sqrt(mofn / n)
        return {"B": scale * boot_rq_xy(design, response, u, tau), "U": u}
    if bsmethod == "wxy":
        if u is None:
            from quantreg.more import _rexp

            draws = np.array([_rexp() for _ in range(n * replicates)])
            u = draws.reshape((n, replicates), order="F")
        return {"B": boot_rq_wxy(design, response, u, tau), "U": u}
    if bsmethod == "jack":
        if mofn is None:
            mofn = n - math.ceil(2 * math.sqrt(n))
        mofn = int(mofn)
        if u is None:
            if mofn < p or mofn > n:
                raise ValueError("mofn is out of range")
            columns = [sample_int(n, mofn, replace=False) for _ in range(replicates)]
            u = np.column_stack(columns)
        scale = (mofn - p + 1) / math.sqrt(n * (n - mofn))
        return {"B": scale * boot_rq_xy(design, response, u, tau), "U": u}
    raise NotImplementedError(f"bootstrap method {bsmethod} is not implemented")


def boot_rq_pwxy(x, y, tau=0.5, coef=None, R=200, m0=None, eps=1e-6):
    """boot.rq.pwxy: preprocessed weighted pairs bootstrap, R replicates.

    Returns B (R x p), nit (5 x R), and the info of each replicate. The exponential
    weights come from R's generator through crates/quantreg, as grexp does in the Fortran.
    """
    from quantreg._kernel import pwxy
    from quantreg.interior import band_scale

    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    if coef is None:
        raise TypeError("coef is required")
    coef = np.asarray(coef, dtype=float).reshape(-1)
    if m0 is None:
        m0 = int(np.round(np.sqrt(n * p)))
    residuals = response - design @ coef
    band = band_scale(design, design, eps)
    scaled = residuals / band
    order = np.argsort(scaled, kind="stable")
    scaled = np.ascontiguousarray(scaled[order])
    response = np.ascontiguousarray(response[order])
    design = np.ascontiguousarray(design[order])
    duals, nit, info = pwxy(design, response, float(tau), scaled, int(m0), int(R))
    return {"B": -duals.T, "nit": nit, "info": info}


def boot_rq_mcmb(x, y, tau=0.5, R=200):
    """boot.rq.mcmb: Markov chain marginal bootstrap, R replicates (R x p).

    The point estimate is rq.fit.br for n < 2000 and the Frisch-Newton fit otherwise.
    The chain draws come from R's generator through crates/quantreg (bootnp).
    """
    from quantreg._kernel import bootnp
    from quantreg.interior import rq_fit_fnb

    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    if n < 2000:
        fit = rq_fit_br(design, response, tau=tau)
    else:
        fit = rq_fit_fnb(design, response, tau=tau)
    coef = np.asarray(fit["coefficients"], dtype=float).reshape(-1)
    residuals = response - design @ coef
    # The LP basis interpolates p points, whose residuals are exactly zero. sign(0) is
    # 0 in psi, so a residual at rounding level is snapped to zero, at rq.fit.br's tol.
    tol = np.finfo(float).eps ** (2.0 / 3.0)
    residuals = np.where(np.abs(residuals) <= tol, 0.0, residuals)

    _u, d, vt = np.linalg.svd(design, full_matrices=False)
    v = vt.T
    ainv = v @ np.diag(d) @ v.T
    coef_tilde = ainv @ coef
    a_matrix = v @ np.diag(1.0 / d) @ v.T
    sign_r = np.sign(residuals)
    psi = np.where(sign_r > 0, tau, np.where(sign_r < 0, tau - 1.0, 0.0))
    transformed = design @ a_matrix
    z_tilde = transformed * psi[:, None]
    sumxij = transformed.sum(axis=0)
    sumabsxij = np.abs(transformed).sum(axis=0)
    theta = bootnp(transformed, response, float(tau), coef_tilde, z_tilde, sumxij, sumabsxij, int(R))
    b_matrix = theta[:, 1:]
    return (a_matrix @ b_matrix).T


def boot_rq_pxy(x, y, s, tau=0.5, coef=None, method="fn", mm_factor=3.0):
    """Preprocessed pairs bootstrap. s holds 1-based row draws, one replicate per column."""
    from quantreg.fit import rq_wfit

    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    index = np.asarray(s, dtype=int)
    if index.ndim == 1:
        index = index.reshape(-1, 1)
    if coef is None:
        raise TypeError("coef is required")
    coef = np.asarray(coef, dtype=float).reshape(-1)
    n, p = design.shape
    replicates = index.shape[1]
    counts = np.vstack([np.bincount(index[:, col] - 1, minlength=n) for col in range(replicates)]).T
    m = int(np.round(np.sqrt(p * n)))
    factor = np.linalg.cholesky(design.T @ design)
    inverse = np.linalg.solve(factor.T, np.eye(p))
    band = np.sqrt(np.sum((design @ inverse) ** 2, axis=1))
    ratio = (response - design @ coef) / band
    ordered = np.sort(ratio)
    design = np.vstack([np.zeros((2, p)), design])
    response = np.concatenate([[0.0, 0.0], response])
    counts = np.vstack([np.ones((2, replicates)), counts])
    fitted = np.empty((replicates, p))
    tau = float(tau)
    for i in range(replicates):
        mm = m
        not_optimal = True
        keep_weight = counts[:, i] > 0
        xb = design[keep_weight].copy()
        yb = response[keep_weight].copy()
        rb = ratio[keep_weight[2:]]
        wb = counts[keep_weight, i].copy()
        while not_optimal:
            span = mm_factor * mm
            lo = max(1, int(np.ceil(n * tau - span / 2.0)))
            hi = min(int(np.floor(n * tau + span / 2.0)), n)
            kappa = ordered[np.array([lo, hi]) - 1]
            sl = np.concatenate([[False, False], rb < kappa[0]])
            su = np.concatenate([[False, False], rb > kappa[1]])
            while not_optimal:
                if np.any(sl):
                    xb[0] = np.sum(xb[sl] * wb[sl, None], axis=0)
                    yb[0] = np.sum(yb[sl] * wb[sl])
                else:
                    sl[0] = True
                if np.any(su):
                    xb[1] = np.sum(xb[su] * wb[su, None], axis=0)
                    yb[1] = np.sum(yb[su] * wb[su])
                else:
                    su[1] = True
                chosen = ~su & ~sl
                try:
                    solved = rq_wfit(xb[chosen], yb[chosen], weights=wb[chosen], tau=tau, method=method)
                except (np.linalg.LinAlgError, RuntimeError, ValueError):
                    mm *= 2
                    import warnings

                    warnings.warn("Singular design: doubling m", stacklevel=2)
                    break
                beta = solved["coefficients"]
                active = int(np.sum(keep_weight))
                rb = yb[2:active] - xb[2:active] @ beta
                su_bad = np.concatenate([[False, False], rb < 0]) & su
                sl_bad = np.concatenate([[False, False], rb > 0]) & sl
                bad = int(np.sum(su_bad | sl_bad))
                if bad > 0:
                    if bad > 0.1 * span:
                        mm *= 2
                        break
                    su = su & ~su_bad
                    sl = sl & ~sl_bad
                else:
                    not_optimal = False
        fitted[i] = beta
    return fitted


def boot_rq_pwy(u, x, y, tau=0.5, tol=1e-4, method="rq0"):
    """boot.rq.pwy(U, X, y, tau, tol): the Parzen-Wei-Ying resampling, dense X.

    U is p x R, as the `pwy` branch of boot.rq passes W = t(X) %*% ((U < tau) - tau).
    Each replicate is the rq LP on X with one artificial observation, the row U[, i] / tau,
    whose response is n * max(|y|). R solves that LP with the Fortran `pwy`, which calls
    `rq0` (the Koenker-D'Orey simplex, dense, not sparse) once per replicate.

    method="rq0" (default) runs rq0 from the crate quantreg_rq0, as R does.
    method="br" solves each LP with rq_fit_br (HiGHS); it is exact but about 4e-11 from R.
    method="sfn" solves each LP with the srqfn kernel through rq_fit_sfn; its gap tolerance
    leaves about 5e-6 from R's pwy.
    `tol` is rq0's TOLER (R's default is 1e-4). Returns R x p.
    """
    if method not in ("rq0", "br", "sfn"):
        raise ValueError("method must be 'rq0', 'br', or 'sfn'")
    if method == "rq0":
        from quantreg_rq0_kernel import rq0
    else:
        from quantreg.sfn import rq_fit_sfn

    design = _as_matrix(x)
    response = np.asarray(y, dtype=float).reshape(-1)
    n, p = design.shape
    if response.shape[0] != n:
        raise ValueError("x and y don't match n")
    weights = np.asarray(u, dtype=float)
    if weights.ndim == 1:
        weights = weights.reshape(-1, 1)
    if weights.shape[0] != p:
        raise ValueError("U row dimension not compatible with design matrix")
    tau = float(tau)
    if tau < 0 or tau > 1:
        raise ValueError("tau outside (0,1) not allowed")
    response_aug = np.concatenate([response, [n * np.max(np.abs(response))]])
    out = np.empty((weights.shape[1], p))
    if method == "rq0":
        # One buffer for the augmented design: the last row is replaced by U[, i] / tau each replicate.
        augmented = np.empty((n + 1, p))
        augmented[:n] = design
        for i in range(weights.shape[1]):
            augmented[n] = weights[:, i] / tau
            out[i] = rq0(augmented, response_aug, tau, tol)[0]
        return out
    for i in range(weights.shape[1]):
        augmented = np.vstack([design, weights[:, i] / tau])
        if method == "br":
            out[i] = rq_fit_br(augmented, response_aug, tau=tau)["coefficients"]
        else:
            out[i] = rq_fit_sfn(augmented, response_aug, tau=tau)["coefficients"]
    return out


def boot_rq_spwy(w, a, y, tau=0.5):
    """boot.rq.spwy(W, a, y, tau): the sparse weighted pairs resampling.

    `a` is a scipy.sparse design (SparseM matrix.csr in R), `w` is p x R. The R code appends
    a row of ones to `a`, and for each replicate replaces that row's values with W[, i] / tau,
    then runs rq.fit.sfn (the srqfn kernel). The response gets the artificial value
    n * max(|y|). Returns R x p.
    """
    import scipy.sparse as sp

    from quantreg.sfn import rq_fit_sfn

    design = sp.csr_matrix(a, dtype=float)
    design.sum_duplicates()
    design.sort_indices()
    n, m = design.shape
    response = np.asarray(y, dtype=float).reshape(-1)
    if response.shape[0] != n:
        raise ValueError("Dimensions of design matrix and the response vector not compatible")
    weights = np.asarray(w, dtype=float)
    if weights.ndim == 1:
        weights = weights.reshape(-1, 1)
    if weights.shape[0] != m:
        raise ValueError("W row dimension not compatible with design matrix")
    tau = float(tau)
    weights = weights / tau
    response_aug = np.concatenate([response, [response.shape[0] * np.max(np.abs(response))]])
    augmented = sp.vstack([design, sp.csr_matrix(np.ones((1, m)))], format="csr")
    augmented.sum_duplicates()
    augmented.sort_indices()
    # The appended row is the last row, so its m values are the last m stored entries.
    out = np.empty((weights.shape[1], m))
    for i in range(weights.shape[1]):
        augmented.data[-m:] = weights[:, i]
        out[i] = rq_fit_sfn(augmented, response_aug, tau=tau)["coefficients"]
    return out
