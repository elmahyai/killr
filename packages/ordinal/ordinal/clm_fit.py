"""clm.fit for ordinal 2026.7-26: design-matrix fitter behind clm() and clm.fit().

Ports clm.fit.factor, clm.fit.default, clm.newRho, set.start, clm.start,
start.threshold, makeThresholds, drop.cols (non-scale path), clm_fit_NR,
clm.finalize, formatTheta (no nominal effects), conv.check and
print.conv.check. Not yet ported: the nlminb/optim/flexible-link paths, and
formatTheta with nominal effects.
"""

from __future__ import annotations

import math
import sys
import warnings
from typing import Any, Sequence

import numpy as np
from scipy.linalg.blas import dtrsm
from scipy.linalg.lapack import dpotrf, dpotri

from ordinal._clm_nll import clm_grad, clm_hess, clm_nll
from ordinal._clm_rho import ClmRho, rho_from_arrays
from ordinal.control import clm_control
from ordinal.convergence import cor_dec
from ordinal.drop_coef import _linpack_qr

MESSAGES = {
    0: "Absolute and relative convergence criteria were met",
    1: "Absolute convergence criterion was met, but relative criterion was not met",
    2: "iteration limit reached",
    3: "step factor reduced below minimum",
    4: "maximum number of consecutive Newton modifications reached",
}

_LINK_FOR_START = {
    "Aranda-Ordaz": "probit",
    "log-gamma": "probit",
    "cauchit": "probit",
}


# ---------------------------------------------------------------- thresholds


def make_thresholds(y_levels: Sequence[str], threshold: str = "flexible") -> dict[str, Any]:
    """makeThresholds: tJac (ntheta x nalpha), nalpha and alpha.names."""
    lev = [str(x) for x in y_levels]
    ntheta = len(lev) - 1
    if threshold == "flexible":
        tjac = np.eye(ntheta)
        nalpha = ntheta
        alpha_names = [f"{a}|{b}" for a, b in zip(lev[:-1], lev[1:])]
    elif threshold == "symmetric":
        if not ntheta >= 2:
            raise ValueError("symmetric thresholds are only meaningful for responses with 3 or more levels")
        if ntheta % 2:
            nalpha = (ntheta + 1) // 2
            a = -np.eye(nalpha)[::-1, : nalpha - 1]
            tjac = np.hstack([a, np.eye(nalpha)]).T
            tjac[:, 0] = 1.0
            alpha_names = ["central"] + [f"spacing.{i}" for i in range(1, nalpha)]
        else:
            nalpha = (ntheta + 2) // 2
            h = ntheta // 2
            col1 = np.concatenate([np.ones(h), np.zeros(h)])
            b = np.vstack([-np.eye(h)[::-1, :], np.eye(h)])
            tjac = np.hstack([col1[:, None], b])
            tjac[:, 1] = np.concatenate([np.zeros(h), np.ones(h)])
            alpha_names = ["central.1", "central.2"] + [f"spacing.{i}" for i in range(1, nalpha - 1)]
    elif threshold == "symmetric2":
        if not ntheta >= 2:
            raise ValueError("symmetric thresholds are only meaningful for responses with 3 or more levels")
        if ntheta % 2:
            nalpha = (ntheta - 1) // 2
            m = (-np.eye(nalpha))[:, ::-1].T
            tjac = np.vstack([m, np.zeros((1, nalpha)), np.eye(nalpha)])
        else:
            nalpha = ntheta // 2
            m = (-np.eye(nalpha))[:, ::-1].T
            tjac = np.vstack([m, np.eye(nalpha)])
        alpha_names = [f"spacing.{i}" for i in range(1, nalpha + 1)]
    elif threshold == "equidistant":
        if not ntheta >= 2:
            raise ValueError("equidistant thresholds are only meaningful for responses with 3 or more levels")
        tjac = np.column_stack([np.ones(ntheta), np.arange(ntheta, dtype=float)])
        nalpha = 2
        alpha_names = ["threshold.1", "spacing"]
    else:
        raise ValueError(f"unknown threshold structure: {threshold}")
    return {"tJac": tjac, "nalpha": nalpha, "alpha.names": alpha_names}


def start_threshold(y_levels: Sequence[str], threshold: str = "flexible") -> np.ndarray:
    """start.threshold: default starting values for the thresholds."""
    ny = len(y_levels)
    ntheta = ny - 1
    if threshold in ("symmetric", "symmetric2", "equidistant") and ny < 3:
        raise ValueError("symmetric and equidistant thresholds are only meaningful for responses with 3 or more levels")
    p = np.arange(1, ntheta + 1, dtype=float) / (ntheta + 1)
    start = np.log(p / (1.0 - p))  # qlogis
    if threshold == "symmetric" and ntheta % 2:
        nalpha = (ntheta + 1) // 2
        start = np.concatenate([[start[nalpha - 1]], np.diff(start[nalpha - 1 : ntheta])])
    if threshold == "symmetric" and not ntheta % 2:
        nalpha = (ntheta + 2) // 2
        start = np.concatenate(
            [[start[nalpha - 2], start[nalpha - 1]], np.diff(start[nalpha - 1 : ntheta])]
        )
    if threshold == "symmetric2" and ntheta % 2:
        nalpha = (ntheta + 3) // 2
        start = start[nalpha - 1 : ntheta]
    if threshold == "symmetric2" and not ntheta % 2:
        nalpha = (ntheta + 2) // 2
        start = start[nalpha - 1 : ntheta]
    if threshold == "equidistant":
        start = np.array([start[0], np.mean(np.diff(start))])
    return np.asarray(start, dtype=float).reshape(-1)


def clm_start(
    y_levels: Sequence[str],
    threshold: str,
    X: np.ndarray,
    NOM: np.ndarray | None = None,
) -> np.ndarray:
    """clm.start: starting values for thresholds, nominal and location effects."""
    st = start_threshold(y_levels, threshold)
    if NOM is not None and NOM.shape[1] > 1:
        st = np.concatenate([st, np.zeros(len(st) * (NOM.shape[1] - 1))])
    return np.concatenate([st, np.zeros(X.shape[1] - 1)])


# ---------------------------------------------------------------- rho model


def _set_link(rho: ClmRho, link: str) -> None:
    rho.link = link


def clm_newrho(
    y_codes: np.ndarray,
    X: np.ndarray,
    *,
    NOM: np.ndarray | None,
    S: np.ndarray | None,
    weights: np.ndarray,
    offset: np.ndarray,
    S_offset: np.ndarray | None,
    tJac: np.ndarray,
    sign_location: str,
    sign_nominal: str,
    link: str,
) -> ClmRho:
    """clm.newRho: model environment with B1, B2, o1, o2 and scale arrays.

    y_codes: 1-based level codes of the response, 0 for NA. Levels not present
    among rows with weights > 0 are dropped (droplevels).
    """
    keep = weights > 0
    y = np.where(keep, y_codes, 0).astype(int)
    present = sorted(set(int(v) for v in y[keep] if v > 0))
    remap = {old: new for new, old in enumerate(present, start=1)}
    y = np.array([remap.get(int(v), 0) for v in y], dtype=int)
    ntheta = len(present) - 1
    cols = np.arange(1, ntheta + 2)
    B = (y[:, None] == cols[None, :]).astype(float)
    o1 = 1e5 * B[keep, ntheta] - offset[keep]
    o2 = -1e5 * B[keep, 0] - offset[keep]
    B1 = B[keep][:, :ntheta] @ tJac
    B2 = B[keep][:, 1:] @ tJac
    if NOM is not None and NOM.shape[1] > 1:
        NOM = NOM.astype(float).copy()
        if sign_nominal == "negative":
            NOM[:, 1:] = -NOM[:, 1:]
        B1 = np.hstack([B1 * NOM[keep][:, [x]] for x in range(NOM.shape[1])])
        B2 = np.hstack([B2 * NOM[keep][:, [x]] for x in range(NOM.shape[1])])
    nbeta = X.shape[1] - 1
    if nbeta > 0:
        Xs = -X if sign_location == "negative" else X
        B1 = np.hstack([B1, Xs[keep][:, 1:]])
        B2 = np.hstack([B2, Xs[keep][:, 1:]])
    n = int(np.sum(keep))
    n_psi = B1.shape[1]
    if S_offset is None:
        soff = np.ones(n)
    else:
        soff = np.exp(np.asarray(S_offset, dtype=float)[keep])
    k = 0
    S_keep = None
    if S is not None:
        S_keep = np.asarray(S, dtype=float)[keep][:, 1:]
        k = S_keep.shape[1]
    return rho_from_arrays(
        b1=B1,
        b2=B2,
        o1=o1,
        o2=o2,
        wts=np.asarray(weights, dtype=float)[keep],
        n_psi=n_psi,
        k=k,
        soff=soff,
        s=S_keep,
        link=link,
        lambda_=1.0,
        nlambda=False,
    )


# ---------------------------------------------------------------- fitting


def _solve_chol(U: np.ndarray, g: np.ndarray) -> np.ndarray:
    """R's solve: backsolve(U, backsolve(U, g, transpose=TRUE)).

    R takes chol(hessian) = U'U (upper) and solves through BLAS dtrsm twice, so
    keeping the upper factor and dtrsm reproduces the last bit; numpy's lower
    cholesky plus linalg.solve does not.
    """
    y = dtrsm(1.0, np.asfortranarray(U), np.asarray(g, dtype=float), trans_a=1, lower=0)
    return dtrsm(1.0, np.asfortranarray(U), y, trans_a=0, lower=0)


def _try_chol(H: np.ndarray):
    """chol(H) as R returns it: LAPACK dpotrf with uplo='U'."""
    try:
        c, info = dpotrf(np.asfortranarray(np.asarray(H, dtype=float)), lower=0, clean=0, overwrite_a=1)
    except (ValueError, np.linalg.LinAlgError):
        return None
    if info != 0:
        return None
    return np.triu(c)[: H.shape[0], : H.shape[0]]


def clm_fit_nr(rho: ClmRho, control: dict[str, Any] | None = None) -> dict[str, Any]:
    """clm_fit_NR: modified Newton-Raphson with step halving."""
    control = clm_control() if control is None else control
    max_iter = int(control["maxIter"])
    grad_tol = float(control["gradTol"])
    rel_tol = float(control["relTol"])
    max_line_iter = int(control["maxLineIter"])
    max_mod_iter = int(control["maxModIter"])

    step_factor = 1.0
    inner_iter = 0
    modif_iter = 0
    abs_iter = 0
    conv = 2
    nll = clm_nll(rho)
    if not np.isfinite(nll):
        raise ValueError("Non-finite log-likelihood at starting value")
    i = 1
    for i in range(1, max_iter + 2):
        gradient = clm_grad(rho)
        max_grad = float(np.max(np.abs(gradient)))
        abs_conv = max_grad < grad_tol
        if abs_conv:
            abs_iter += 1
        hessian = clm_hess(rho)
        ch = _try_chol(hessian)
        if ch is None:
            if abs_conv:
                conv = 1
                break
            min_ev = float(np.min(np.linalg.eigvalsh(hessian)))
            inflate = abs(min_ev) + 1.0
            hessian = hessian + inflate * np.eye(hessian.shape[0])
            ch = _try_chol(hessian)
            if ch is None:
                raise ValueError(f"Cannot compute Newton step at iteration {i - 1}")
            modif_iter += 1
        else:
            modif_iter = 0
        if modif_iter >= max_mod_iter:
            conv = 4
            break
        step = _solve_chol(ch, gradient)
        rel_conv = float(np.max(np.abs(step))) < rel_tol
        if abs_conv and rel_conv:
            conv = 0
            break
        rho.par = rho.par - step_factor * step
        nll_try = clm_nll(rho)
        stephalf = nll_try > nll
        if stephalf and abs(nll - nll_try) < 1e-10:
            stephalf = max_grad < float(np.max(np.abs(clm_grad(rho))))
        if abs_conv and stephalf:
            conv = 1
            rho.par = rho.par + step_factor * step
            clm_nll(rho)
            break
        if abs_conv and abs_iter >= 5:
            conv = 1
            break
        line_iter = 0
        while stephalf:
            step_factor /= 2.0
            rho.par = rho.par + step_factor * step
            nll_try = clm_nll(rho)
            line_iter += 1
            if line_iter > max_line_iter:
                conv = 3
                break
            inner_iter += 1
            stephalf = nll_try > nll
            if stephalf and abs(nll - nll_try) < 1e-10:
                stephalf = max_grad < float(np.max(np.abs(clm_grad(rho))))
        if conv == 3:
            break
        nll = nll_try
        step_factor = min(1.0, 2.0 * step_factor)
    outer = i - 1
    gradient = clm_grad(rho)
    return {
        "par": rho.par.copy(),
        "gradient": np.asarray(gradient, dtype=float).reshape(-1),
        "Hessian": np.asarray(clm_hess(rho), dtype=float),
        "logLik": -float(nll),
        "convergence": conv,
        "message": MESSAGES[conv],
        "maxGradient": float(np.max(np.abs(gradient))),
        "niter": (outer, inner_iter),
        "fitted": rho.fitted.copy(),
    }


# ---------------------------------------------------------------- drop.cols


def drop_coef2(X: np.ndarray, tol: float = 1e-7) -> tuple[np.ndarray, np.ndarray]:
    """drop.coef2: full-rank columns of X and the aliased indicator (LINPACK pivots)."""
    X = np.asarray(X, dtype=float)
    aliased = np.zeros(X.shape[1], dtype=int)
    pivot, rank = _linpack_qr(X, tol=tol)
    if rank == X.shape[1]:
        return X.copy(), aliased
    sel = pivot[:rank] - 1
    dropped = pivot[rank:] - 1
    aliased[dropped] = 1
    return X[:, sel].copy(), aliased


def _has_intercept(names: Sequence[str]) -> bool:
    return "(Intercept)" in list(names)


def drop_cols(y: dict[str, Any]) -> dict[str, Any]:
    """drop.cols with drop.scale = FALSE, as called from clm.fit.default.

    y carries X, X_names, alpha.names and optionally S, S_names, NOM, NOM_names.
    Returns a copy with X, S, NOM reduced to full column rank, plus coef.names
    and aliased. coef.names keep every original name, as R does.
    """
    nalpha = len(y["alpha.names"])
    X = np.asarray(y["X"], dtype=float)
    X_names = list(y["X_names"])
    if not _has_intercept(X_names):
        X = np.column_stack([np.ones(X.shape[0]), X])
        X_names = ["(Intercept)"] + X_names
        warnings.warn("an intercept is needed and assumed", stacklevel=2)
    y = dict(y)
    coef_names: dict[str, Any] = {"beta": X_names[1:]}
    if y.get("NOM") is not None:
        NOM = np.asarray(y["NOM"], dtype=float)
        NOM_names = list(y["NOM_names"])
        coef_names["alpha"] = [f"{a}.{b}" for b in NOM_names for a in y["alpha.names"]]
        NOM_d, al_nom = drop_coef2(NOM)
        nnom = NOM_d.shape[1]
        NOMX, al_nomx = drop_coef2(np.hstack([NOM_d, X[:, 1:]]))
        X_new = np.hstack([np.ones((X.shape[0], 1)), NOMX[:, nnom:]])
        aliased = {
            "alpha": np.repeat(al_nom, nalpha),
            "beta": al_nomx[nnom:],
        }
        y["NOM"] = NOM_d
    else:
        coef_names["alpha"] = list(y["alpha.names"])
        X_new, al_x = drop_coef2(X)
        aliased = {"alpha": np.zeros(nalpha, dtype=int), "beta": al_x[1:]}
    y["X"] = X_new
    y["X_names"] = X_names
    if y.get("S") is not None:
        S = np.asarray(y["S"], dtype=float)
        S_names = list(y["S_names"])
        if not _has_intercept(S_names):
            S = np.column_stack([np.ones(S.shape[0]), S])
            S_names = ["(Intercept)"] + S_names
            warnings.warn("an intercept is needed and assumed in 'scale'", stacklevel=2)
        coef_names["zeta"] = S_names[1:]
        S_d, al_s = drop_coef2(S)
        aliased["zeta"] = al_s[1:]
        y["S"] = S_d
    else:
        aliased["zeta"] = np.zeros(0, dtype=int)
        coef_names["zeta"] = []
    y["coef.names"] = coef_names
    y["aliased"] = aliased
    return y


# ---------------------------------------------------------------- finalize


def clm_finalize(fit: dict[str, Any], weights: np.ndarray, coef_names: dict[str, Any], aliased: dict[str, Any]) -> dict[str, Any]:
    """clm.finalize: full coefficient vector, alpha, beta, zeta and summary fields."""
    nalpha = len(aliased["alpha"])
    nbeta = len(aliased["beta"])
    nzeta = len(aliased["zeta"])
    ncoef = nalpha + nbeta + nzeta
    al_all = np.concatenate(
        [np.asarray(aliased["alpha"], dtype=bool), np.asarray(aliased["beta"], dtype=bool), np.asarray(aliased["zeta"], dtype=bool)]
    )
    npar = int(np.sum(~al_all))
    par = np.asarray(fit["par"], dtype=float)
    if par.size != npar:
        raise ValueError("length of par does not match the number of free coefficients")
    names = list(coef_names["alpha"]) + list(coef_names["beta"]) + list(coef_names["zeta"])
    coefficients = np.full(ncoef, np.nan)
    coefficients[~al_all] = par
    par_names = [nm for nm, a in zip(names, al_all) if not a]
    out = dict(fit)
    out["coefficients"] = coefficients
    out["coef.names"] = names
    out["alpha"] = coefficients[:nalpha]
    out["beta"] = coefficients[nalpha : nalpha + nbeta]
    out["zeta"] = coefficients[nalpha + nbeta : ncoef]
    out["par.names"] = par_names
    out["edf"] = npar
    out["nobs"] = float(np.sum(weights))
    out["n"] = int(len(weights))
    out["fitted.values"] = np.asarray(fit["fitted"], dtype=float)
    out["df.residual"] = out["nobs"] - npar
    out["aliased"] = {k: np.asarray(v, dtype=bool) for k, v in aliased.items()}
    for key in ("fitted", "par"):
        out.pop(key, None)
    return out


# ---------------------------------------------------------------- theta and conv


def format_tjac(tjac: np.ndarray, y_levels: Sequence[str], alpha_names: Sequence[str]) -> dict[str, Any]:
    lev = [str(x) for x in y_levels]
    return {
        "matrix": np.asarray(tjac, dtype=float),
        "rownames": [f"{a}|{b}" for a, b in zip(lev[:-1], lev[1:])],
        "colnames": list(alpha_names),
    }


def format_theta(
    alpha: np.ndarray,
    tjac: dict[str, Any],
    NOM: np.ndarray | None = None,
    sign_nominal: str = "positive",
    nom_info: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """formatTheta: thresholds per combination of nominal factor levels.

    Without nominal effects Theta = alpha tJac'. With nominal factors (nom_info from
    clm), thresholds are built from the nominal model matrix on the grid of factor
    levels (getThetamat). Numeric nominal variables are not ported yet.
    """
    if NOM is None:
        T = np.asarray(alpha, dtype=float).reshape(1, -1) @ tjac["matrix"].T
        return {"Theta": T, "Theta.ok": True, "rownames": tjac["rownames"]}
    if nom_info is None:
        warnings.warn("Cannot assess if all thresholds are increasing", stacklevel=2)
        return {"Theta": None, "Theta.ok": True, "rownames": tjac["rownames"]}
    if nom_info.get("numeric"):
        raise NotImplementedError("getThetamat with numeric nominal variables is not ported yet")
    from ordinal.clm_frames import nominal_grid_matrix

    nalpha = tjac["matrix"].shape[1]
    alpha_mat = np.asarray(alpha, dtype=float).reshape(-1, nalpha)
    Xg = nominal_grid_matrix(nom_info, sign_nominal)
    keep = ~np.any(np.isnan(alpha_mat), axis=1)
    theta_alpha = Xg[:, keep] @ alpha_mat[keep, :]
    theta = theta_alpha @ tjac["matrix"].T
    ok = True
    if np.all(np.isfinite(theta)):
        ok = bool(np.all(np.all(np.diff(theta, axis=1) >= 0, axis=1)))
    return {"Theta": theta, "Theta.ok": ok, "rownames": tjac["rownames"]}


def conv_check(
    fit: dict[str, Any],
    control: dict[str, Any],
    theta_ok: bool | None = None,
    tol: float | None = None,
) -> dict[str, Any]:
    """conv.check: variance-covariance matrix and convergence codes."""
    if control.get("tol") is not None:
        tol = float(control["tol"])
    if tol is None:
        tol = math.sqrt(sys.float_info.epsilon)
    if tol < 0:
        raise ValueError(f"numerical tolerance is {tol:g}, expecting non-negative value")
    H = np.asarray(fit["Hessian"], dtype=float)
    g = np.asarray(fit["gradient"], dtype=float)
    max_grad = float(np.max(np.abs(g)))
    code_raw = fit["convergence"]
    if isinstance(code_raw, dict):
        code_raw = code_raw["code"]
    code0 = int(code_raw)
    alg_message = MESSAGES.get(code0) if control.get("method") == "Newton" else None
    res: dict[str, Any] = {
        "vcov": np.full(H.shape, np.nan),
        "code": [],
        "cond.H": np.nan,
        "messages": [],
        "alg.message": alg_message,
    }
    evd = np.sort(np.linalg.eigvalsh(H))[::-1]
    negative = int(np.sum(evd < -tol))
    if negative:
        res["code"] = [-2]
        res["messages"] = [
            f"Model failed to converge: degenerate Hessian with {negative} negative eigenvalues"
        ]
        return res
    res["cond.H"] = float(max(evd) / min(evd))
    ch = _try_chol(H)
    if max_grad > float(control["gradTol"]):
        res["code"] = [-1]
        res["messages"] = [
            f"Model failed to converge with max|grad| = {max_grad:g} (tol = {float(control['gradTol']):g})"
        ]
        if ch is not None:
            res["vcov"] = _chol2inv(ch)
        return res
    if theta_ok is not None and not theta_ok:
        res["code"] = [-3]
        res["messages"] = ["not all thresholds are increasing: fit is invalid"]
        if ch is not None:
            res["vcov"] = _chol2inv(ch)
        return res
    zero = int(np.sum(np.abs(evd) < tol))
    if zero or ch is None:
        res["code"] = [1]
        res["messages"] = ["Hessian is numerically singular: parameters are not uniquely determined"]
        return res
    step = _solve_chol(ch, g)
    res["vcov"] = _chol2inv(ch)
    codes: list[int] = []
    messages: list[str] = []
    if float(np.max(np.abs(step))) > float(control["relTol"]):
        codes.append(1)
        cor_dec_min = int(np.min(cor_dec(step)))
        messages.append(f"some parameters may have only {cor_dec_min} correct decimals")
    if max(evd) * tol > 1:
        codes.append(2)
        messages.append(
            "Model is nearly unidentifiable: very large eigenvalue\n - Rescale variables?"
        )
    if (min(evd) / max(evd)) < tol:
        codes.append(3)
        if 5 not in codes:
            messages.append("Model is nearly unidentifiable: large eigenvalue ratio\n - Rescale variables?")
    if not codes:
        codes = [0]
        messages = ["successful convergence"]
    res["code"] = codes
    res["messages"] = messages
    return res


def _chol2inv(ch: np.ndarray) -> np.ndarray:
    """chol2inv: (U'U)^-1 from chol's upper factor, via LAPACK dpotri."""
    c, info = dpotri(np.asfortranarray(ch), lower=0)
    if info != 0:
        H = ch.T @ ch
        return np.linalg.inv(H)
    n = ch.shape[0]
    upper = np.triu(c)[:n, :n]
    return upper + np.triu(upper, 1).T


def print_conv_check(conv: dict[str, Any], action: str = "warn") -> None:
    """print.conv.check: report a non-zero convergence code."""
    if action not in ("warn", "silent", "stop", "message"):
        raise ValueError(f"unknown convergence action {action}")
    if conv["code"][0] == 0 or action == "silent":
        return
    text = f"({conv['code'][0]}) {conv['messages'][0]}"
    if conv.get("alg.message") is not None:
        text += f"\nIn addition: {conv['alg.message']}"
    if action == "stop":
        raise RuntimeError(text)
    if action == "warn":
        warnings.warn(text, stacklevel=2)
    else:
        print(text, file=sys.stderr)


# ---------------------------------------------------------------- set.start and clm.fit


def set_start(
    rho: ClmRho,
    start: np.ndarray | None,
    *,
    get_start: bool,
    threshold: str,
    link: str,
    y_levels: Sequence[str],
    X: np.ndarray,
    NOM: np.ndarray | None,
    S: np.ndarray | None,
) -> tuple[np.ndarray, tuple[int, int] | None]:
    """set.start: starting parameter vector and the iterations used to find it."""
    n_scol = 0 if S is None else S.shape[1]
    n_spar = max(0, n_scol - 1)
    start_iter = None
    if get_start:
        start = clm_start(y_levels, threshold, X, NOM)
        if n_spar > 0 or link == "cauchit":
            rho.par = np.asarray(start, dtype=float).copy()
            _set_link(rho, _LINK_FOR_START.get(link, link))
            tempk = rho.k
            rho.k = 0
            try:
                fit = clm_fit_nr(rho, clm_control(grad_tol=1e-3, rel_tol=1e-3))
            except ValueError as exc:
                raise ValueError(
                    "Failed to find suitable starting values: please supply some"
                ) from exc
            start = np.concatenate([fit["par"], np.zeros(n_spar)])
            start_iter = fit["niter"]
            rho.k = tempk
            _set_link(rho, link)
    start = np.asarray(start, dtype=float).reshape(-1)
    length_start = rho.b1.shape[1] + n_spar
    if start.size != length_start:
        raise ValueError(f"length of start is {start.size} should equal {length_start}")
    return start, start_iter


def clm_fit(
    y: Sequence[Any],
    X: np.ndarray,
    *,
    levels: Sequence[str] | None = None,
    X_names: Sequence[str] | None = None,
    S: np.ndarray | None = None,
    S_names: Sequence[str] | None = None,
    N: np.ndarray | None = None,
    N_names: Sequence[str] | None = None,
    weights: np.ndarray | None = None,
    offset: np.ndarray | None = None,
    S_offset: np.ndarray | None = None,
    control: dict[str, Any] | None = None,
    start: np.ndarray | None = None,
    do_fit: bool = True,
    link: str = "logit",
    threshold: str = "flexible",
) -> dict[str, Any] | ClmRho:
    """clm.fit (clm.fit.factor and clm.fit.default) for a response factor.

    y: sequence of response labels; None or NaN marks NA. levels gives the factor
    levels in order (default: sorted unique labels). control is a dict from
    clm_control (missing keys take the clm.control defaults). Only the Newton
    method and the links logit, probit, cloglog, loglog and cauchit are ported.
    """
    n = len(y)
    X = np.asarray(X, dtype=float)
    if X.ndim != 2:
        raise TypeError("X must be a matrix")
    if X.shape[0] != n:
        raise ValueError("length(y) == nrow(X) is not true")
    weights = np.ones(n) if weights is None else np.asarray(weights, dtype=float)
    if levels is None:
        levels = sorted({str(v) for v in y if v is not None and not _is_nan(v)})
    levels = [str(v) for v in levels]
    labels = [
        None if (v is None or _is_nan(v) or weights[i] <= 0) else str(v)
        for i, v in enumerate(y)
    ]
    used = [lev for lev in levels if any(lab == lev for lab in labels)]
    code_of = {lev: j + 1 for j, lev in enumerate(used)}
    y_codes = np.array([code_of[lab] if lab is not None else 0 for lab in labels], dtype=int)
    if X_names is None:
        X_names = ["(Intercept)"] + [f"x{i}" for i in range(1, X.shape[1])]
    return clm_fit_core(
        y_codes=y_codes,
        y_levels=used,
        X=X,
        X_names=list(X_names),
        S=None if S is None else np.asarray(S, dtype=float),
        S_names=None if S is None else list(S_names or ["(Intercept)"] + [f"z{i}" for i in range(1, np.shape(S)[1])]),
        N=None if N is None else np.asarray(N, dtype=float),
        N_names=None if N is None else list(N_names or ["(Intercept)"] + [f"n{i}" for i in range(1, np.shape(N)[1])]),
        weights=weights,
        offset=np.zeros(n) if offset is None else np.asarray(offset, dtype=float),
        S_offset=None if S_offset is None else np.asarray(S_offset, dtype=float),
        control=control,
        start=start,
        do_fit=do_fit,
        link=link,
        threshold=threshold,
        nom_info=None,
    )


def clm_fit_core(
    *,
    y_codes: np.ndarray,
    y_levels: Sequence[str],
    X: np.ndarray,
    X_names: Sequence[str],
    S: np.ndarray | None,
    S_names: Sequence[str] | None,
    N: np.ndarray | None,
    N_names: Sequence[str] | None,
    weights: np.ndarray,
    offset: np.ndarray,
    S_offset: np.ndarray | None,
    control: dict[str, Any] | None,
    start: np.ndarray | None,
    do_fit: bool,
    link: str,
    threshold: str,
    nom_info: dict[str, Any] | None,
) -> dict[str, Any] | ClmRho:
    """clm.fit.default on a prepared design (y codes 1-based, 0 for NA)."""
    if link in ("Aranda-Ordaz", "log-gamma"):
        raise NotImplementedError("flexible links need nlminb, which is not ported yet")
    ctrl = {**clm_control(), **(control or {})}
    if ctrl["method"] != "Newton":
        raise NotImplementedError(f"method {ctrl['method']} is not ported yet")
    thr = make_thresholds(y_levels, threshold)
    tjac = thr["tJac"]
    struct = drop_cols(
        {
            "alpha.names": thr["alpha.names"],
            "X": X,
            "X_names": list(X_names),
            "S": S,
            "S_names": S_names,
            "NOM": N,
            "NOM_names": N_names,
        }
    )
    rho = clm_newrho(
        y_codes,
        struct["X"],
        NOM=struct.get("NOM"),
        S=struct.get("S"),
        weights=weights,
        offset=offset,
        S_offset=S_offset,
        tJac=tjac,
        sign_location=ctrl["sign.location"],
        sign_nominal=ctrl["sign.nominal"],
        link=link,
    )
    par_start, start_iter = set_start(
        rho,
        start,
        get_start=start is None,
        threshold=threshold,
        link=link,
        y_levels=y_levels,
        X=struct["X"],
        NOM=struct.get("NOM"),
        S=struct.get("S"),
    )
    rho.par = np.asarray(par_start, dtype=float).copy()
    if not do_fit:
        return rho
    fit = clm_fit_nr(rho, ctrl)
    if start_iter is not None:
        fit["niter"] = (fit["niter"][0] + start_iter[0], fit["niter"][1] + start_iter[1])
    fit = clm_finalize(fit, weights, struct["coef.names"], struct["aliased"])
    fit["tJac"] = format_tjac(tjac, y_levels, thr["alpha.names"])
    th = format_theta(
        fit["alpha"], fit["tJac"], struct.get("NOM") if N is not None else None,
        ctrl["sign.nominal"], nom_info,
    )
    conv = conv_check(fit, ctrl, theta_ok=th["Theta.ok"], tol=ctrl["tol"])
    print_conv_check(conv, action=ctrl["convergence"])
    fit["vcov"] = conv["vcov"]
    fit["cond.H"] = conv["cond.H"]
    fit["Theta"] = th["Theta"]
    fit["convergence"] = {
        "code": conv["code"],
        "messages": conv["messages"],
        "alg.message": conv["alg.message"],
    }
    fit["y.levels"] = list(y_levels)
    fit["link"] = link
    fit["threshold"] = threshold
    fit["control"] = ctrl
    return fit


def _is_nan(value: Any) -> bool:
    try:
        return bool(math.isnan(float(value)))
    except (TypeError, ValueError):
        return False
