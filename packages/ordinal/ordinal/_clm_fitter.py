"""Newton fitter for cumulative link models (ordinal clm_fit_NR)."""

from __future__ import annotations

import numpy as np

from ordinal._clm_nll import clm_grad, clm_hess, clm_nll
from ordinal.clm_fit import _solve_chol, _try_chol
from ordinal.control import clm_control


def clm_fit_nr(rho, control=None):
    """Fit a clm rho environment with modified Newton-Raphson."""
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
        hessian = np.asarray(clm_hess(rho), dtype=float)
        ch = _try_chol(hessian)
        if ch is None:
            if abs_conv:
                conv = 1
                break
            min_ev = float(np.min(np.linalg.eigvalsh(hessian)))
            inflate = abs(min_ev) + 1.0
            hessian = hessian + np.diag(inflate, k=0)
            modif_iter += 1
            ch = _try_chol(hessian)
            if ch is None:
                raise ValueError(f"Cannot compute Newton step at iteration {outer_i - 1}")
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
    messages = {
        0: "Absolute and relative convergence criteria were met",
        1: "Absolute convergence criterion was met, but relative criterion was not met",
        2: "iteration limit reached",
        3: "step factor reduced below minimum",
        4: "maximum number of consecutive Newton modifications reached",
    }
    gradient = np.asarray(clm_grad(rho), dtype=float).reshape(-1)
    return {
        "par": rho.par.copy(),
        "gradient": gradient,
        "Hessian": np.asarray(clm_hess(rho), dtype=float),
        "logLik": -float(nll),
        "convergence": {"code": conv, "messages": messages.get(conv, ""), "alg.message": messages.get(conv, "")},
        "maxGradient": float(np.max(np.abs(gradient))),
        "edf": int(rho.par.size),
        "nobs": int(rho.wts.size),
    }
