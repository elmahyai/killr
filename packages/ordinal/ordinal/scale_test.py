"""Likelihood ratio tests of scale effects (ordinal scale_test.clm)."""

from __future__ import annotations

from typing import Any

import numpy as np
from scipy.stats import chi2

from ordinal._clm_nll import _link_gfun, clm_grad, clm_nll
from ordinal._clm_rho import ClmLike, ClmRho, clm_like_from_npz, rho_from_arrays
from ordinal.control import clm_control
from ordinal.nominal_test import NominalTestAnova


def _aic(loglik: float, edf: float) -> float:
    return -2.0 * loglik + 2.0 * edf


def _term_labels(object) -> list[str]:
    if hasattr(object, "term_labels"):
        return list(object.term_labels)
    terms = getattr(object, "terms", None)
    if terms is not None and hasattr(terms, "term_labels"):
        return list(terms.term_labels)
    raise TypeError("object has no term labels for scale_test")


def _scale_term_labels(object) -> list[str]:
    if hasattr(object, "S_term_labels") and object.S_term_labels:
        return list(object.S_term_labels)
    s_terms = getattr(object, "S_terms", None)
    if s_terms is not None and hasattr(s_terms, "term_labels"):
        return list(s_terms.term_labels)
    return []


def _resolve_scope(object, scope) -> list[str]:
    termsnm = list(_term_labels(object))
    if scope is not None:
        if not isinstance(scope, (list, tuple)):
            raise TypeError("scope must be a character vector of term names")
        scope = [str(s) for s in scope]
        missing = [s for s in scope if s not in termsnm]
        if missing:
            raise ValueError("scope is not a subset of term labels")
    else:
        scope = termsnm
    scale_labels = _scale_term_labels(object)
    if scale_labels:
        scope = [s for s in scope if s not in scale_labels]
    return scope


def _formula_location(object) -> str:
    if hasattr(object, "formula_location"):
        return str(object.formula_location)
    return ""


def _has_call_nominal(object) -> bool:
    call = getattr(object, "call", None)
    if call is None:
        return bool(getattr(object, "call_nominal", None))
    return getattr(call, "nominal", None) is not None or bool(getattr(object, "call_nominal", None))


def _has_call_scale(object) -> bool:
    call = getattr(object, "call", None)
    if call is None:
        return bool(getattr(object, "call_scale", None))
    return getattr(call, "scale", None) is not None or bool(getattr(object, "call_scale", None))


def _nom_formula_deparse(object) -> str:
    if getattr(object, "nom_formula", None):
        return str(object.nom_formula)
    return ""


def _scale_formula_deparse(object) -> str:
    if getattr(object, "scale_formula", None):
        return str(object.scale_formula)
    return ""


def _location_column_for_term(object, term: str) -> int | None:
    names = getattr(object, "_coef_names", None) or getattr(object, "coef_names", None)
    if names is None and hasattr(object, "coef"):
        names = [f"beta{i}" for i in range(int(np.asarray(object.coef).size))]
    if names is None:
        return None
    term = str(term)
    for idx, name in enumerate(names):
        if name.startswith("|"):
            continue
        if str(name).startswith(term):
            return idx
    return None


def _copy_rho(rho: ClmRho) -> ClmRho:
    s = None if rho.s is None else np.asarray(rho.s, dtype=float).copy()
    return rho_from_arrays(
        b1=rho.b1,
        b2=rho.b2,
        o1=rho.o1,
        o2=rho.o2,
        wts=rho.wts,
        n_psi=rho.n_psi,
        k=rho.k,
        soff=rho.soff,
        s=s,
        link=rho.link,
        lambda_=rho.lambda_,
        nlambda=rho.nlambda,
        par=rho.par.copy(),
    )


def _clm_hess_with_scale(rho: ClmRho) -> np.ndarray:
    """Hessian when k > 0; matches R crossprod(B1, wt * S) row weighting."""
    if not hasattr(rho, "_C2"):
        clm_grad(rho)
    p1 = rho._p1
    p2 = rho._p2
    wtpr = rho._wtpr
    c2 = rho._C2
    c3 = rho._C3
    scale = rho.sigma
    g1 = _link_gfun(rho, rho.eta1)
    g2 = _link_gfun(rho, rho.eta2)
    wtprpr = wtpr / rho.fitted
    dg_psi = (rho.b1 * (g1 * wtpr / scale**2)[:, None]).T @ rho.b1
    dg_psi -= (rho.b2 * (g2 * wtpr / scale**2)[:, None]).T @ rho.b2
    d_block = dg_psi - c2.T @ (c2 * wtprpr[:, None])
    k = int(rho.k)
    if k <= 0:
        return -d_block
    wtprsig = wtpr / scale
    epg1 = p1 + g1 * rho.eta1
    epg2 = p2 + g2 * rho.eta2
    v1 = (-wtprsig * epg1)[:, None] * rho.s
    v2 = (-wtprsig * epg2)[:, None] * rho.s
    et = rho.b1.T @ v1 - rho.b2.T @ v2 - c2.T @ (wtprpr[:, None] * c3)
    mid = wtpr * (
        (rho.eta1 * p1 - rho.eta2 * p2) ** 2 / rho.fitted - (rho.eta1 * epg1 - rho.eta2 * epg2)
    )
    f_block = -(rho.s * mid[:, None]).T @ rho.s
    upper = np.hstack([d_block, et])
    lower = np.hstack([et.T, f_block])
    return -np.vstack([upper, lower])


def _clm_fit_nr_scale(rho: ClmRho, control=None) -> dict[str, Any]:
    control = clm_control() if control is None else control
    step_factor = 1.0
    inner_iter = 0
    modif_iter = 0
    abs_iter = 0
    conv = 2
    nll = clm_nll(rho)
    if not np.isfinite(nll):
        raise ValueError("Non-finite log-likelihood at starting value")
    max_iter = int(control["maxIter"])
    grad_tol = float(control["gradTol"])
    rel_tol = float(control["relTol"])
    max_line_iter = int(control["maxLineIter"])
    max_mod_iter = int(control["maxModIter"])
    outer_i = 0
    for outer_i in range(1, max_iter + 2):
        gradient = np.asarray(clm_grad(rho), dtype=float).reshape(-1)
        max_grad = float(np.max(np.abs(gradient)))
        abs_conv = max_grad < grad_tol
        if abs_conv:
            abs_iter += 1
        hessian = np.asarray(_clm_hess_with_scale(rho), dtype=float)
        try:
            ch = np.linalg.cholesky(hessian)
        except np.linalg.LinAlgError:
            if abs_conv:
                conv = 1
                break
            min_ev = float(np.min(np.linalg.eigvalsh(hessian)))
            hessian = hessian + np.diag(abs(min_ev) + 1.0, k=0)
            modif_iter += 1
            try:
                ch = np.linalg.cholesky(hessian)
            except np.linalg.LinAlgError as exc:
                raise ValueError(f"Cannot compute Newton step at iteration {outer_i - 1}") from exc
        else:
            modif_iter = 0
        if modif_iter >= max_mod_iter:
            conv = 4
            break
        step = np.linalg.solve(ch.T, np.linalg.solve(ch, gradient))
        rel_conv = float(np.max(np.abs(step))) < rel_tol
        if abs_conv and rel_conv:
            conv = 0
            break
        par = rho.par.copy()
        rho.par = par - step_factor * step
        nll_try = clm_nll(rho)
        line_iter = 0
        stephalf = nll_try > nll
        if stephalf and abs(nll - nll_try) < 1e-10:
            stephalf = max_grad < float(np.max(np.abs(clm_grad(rho))))
        if abs_conv and stephalf:
            conv = 1
            rho.par = par
            clm_nll(rho)
            break
        if abs_conv and abs_iter >= 5:
            conv = 1
            break
        while stephalf:
            step_factor /= 2.0
            rho.par = par - step_factor * step
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
    gradient = np.asarray(clm_grad(rho), dtype=float).reshape(-1)
    return {
        "par": rho.par.copy(),
        "gradient": gradient,
        "Hessian": np.asarray(_clm_hess_with_scale(rho), dtype=float),
        "logLik": -float(nll),
        "convergence": {"code": conv},
        "maxGradient": float(np.max(np.abs(gradient))),
        "edf": int(rho.par.size),
        "nobs": int(rho.wts.size),
    }


def _build_scale_rho(object, term: str) -> ClmRho | None:
    refits = getattr(object, "_refit_scale_rhos", None)
    if refits is not None and term in refits:
        rho, start = refits[term]
        rho = _copy_rho(rho)
        rho.par = np.asarray(start, dtype=float).reshape(-1).copy()
        return rho
    base = object.get_clm_rho() if hasattr(object, "get_clm_rho") else getattr(object, "_rho", None)
    if base is None:
        return None
    col = _location_column_for_term(object, term)
    if col is None:
        return None
    b1 = np.asarray(base.b1, dtype=float)
    s = b1[:, col : col + 1].copy()
    start = np.concatenate([np.asarray(base.par, dtype=float).reshape(-1), [0.0]])
    return rho_from_arrays(
        b1=base.b1,
        b2=base.b2,
        o1=base.o1,
        o2=base.o2,
        wts=base.wts,
        n_psi=int(base.n_psi),
        k=1,
        soff=base.soff,
        s=s,
        link=base.link,
        lambda_=base.lambda_,
        nlambda=base.nlambda,
        par=start,
    )


def _refit_scale(object, term: str) -> dict[str, Any] | None:
    rho = _build_scale_rho(object, term)
    if rho is None:
        return None
    try:
        return _clm_fit_nr_scale(rho)
    except ValueError:
        return None


def scale_test(object, scope=None, trace=False, **kwargs):
    if isinstance(object, ClmLike) or (
        hasattr(object, "logLik") and hasattr(object, "edf") and _term_labels(object)
    ):
        return scale_test_clm(object, scope=scope, trace=trace, **kwargs)
    raise TypeError(f"no scale_test method for object of type {type(object).__name__}")


def scale_test_clm(object, scope=None, trace=False, **_kwargs):
    del _kwargs
    scope = _resolve_scope(object, scope)
    if not scope:
        print("\nno relevant terms to add to scale\n")
    ns = len(scope)
    rownames = ["<none>"] + scope
    ans = np.full((ns + 1, 3), np.nan, dtype=float)
    edf0 = float(getattr(object, "edf", np.nan))
    if np.isnan(edf0) and hasattr(object, "coef"):
        edf0 = float(np.asarray(object.coef, dtype=float).size)
    loglik0 = float(object.logLik)
    ans[0, :] = [edf0, loglik0, _aic(loglik0, edf0)]
    n0 = int(getattr(object, "nobs", getattr(object, "n", np.nan)))
    for i, term in enumerate(scope):
        if trace:
            print(f"trying + {term} ")
        nfit = _refit_scale(object, term)
        if nfit is not None and int(nfit["convergence"]["code"]) >= 0:
            ans[i + 1, :] = [nfit["edf"], nfit["logLik"], _aic(nfit["logLik"], nfit["edf"])]
            nnew = int(nfit["nobs"])
            if np.isfinite(n0) and np.isfinite(nnew) and nnew != n0:
                raise ValueError("number of rows in use has changed: remove missing values?")
    dfs = ans[:, 0] - ans[0, 0]
    dfs[0] = np.nan
    lr = 2.0 * (ans[:, 1] - ans[0, 1])
    lr[0] = np.nan
    pvals = lr.copy()
    mask = np.isfinite(lr) & np.isfinite(dfs)
    pvals[mask] = chi2.sf(lr[mask], dfs[mask])
    pvals[~mask] = np.nan
    frame = {
        "Df": dfs,
        "logLik": ans[:, 1],
        "AIC": ans[:, 2],
        "LRT": lr,
        "Pr(>Chi)": pvals,
    }
    head = ["Tests of scale effects", f"\nformula: {_formula_location(object)}"]
    if _has_call_scale(object):
        head.append(f"scale:   {_scale_formula_deparse(object)}")
    if _has_call_nominal(object):
        head.append(f"nominal: {_nom_formula_deparse(object)}")
    return NominalTestAnova(frame=frame, rownames=rownames, heading=head)


def scale_test_values(result: NominalTestAnova) -> np.ndarray:
    """Flatten anova columns in R column order."""
    return result.values()


def clm_like_for_scale_test(path: str) -> ClmLike:
    """Load a saved clm fit for scale_test proofs."""
    return clm_like_from_npz(path)
