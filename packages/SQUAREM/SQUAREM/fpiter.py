import numpy as np


def fpiter(par, fixptfn, objfn=None, control=None, **kwargs):
    """Fixed-point iteration, matching SQUAREM::fpiter."""
    control = {} if control is None else dict(control)
    defaults = {"tol": 1e-7, "maxiter": 5000, "trace": False, "intermed": False}
    unknown = set(control) - set(defaults)
    if unknown:
        raise ValueError("unknown names in control: " + ", ".join(sorted(unknown)))
    ctrl = {**defaults, **control}
    tol, maxiter = ctrl["tol"], ctrl["maxiter"]
    trace, intermed = ctrl["trace"], ctrl["intermed"]
    par = np.asarray(par, dtype=float).copy()
    iteration = 1
    objeval = 0
    converged = False
    if intermed:
        intermediate = [np.r_[par, np.nan]]
    while iteration < maxiter:
        pnew = np.asarray(fixptfn(par, **kwargs), dtype=float)
        residual = float(np.linalg.norm(pnew - par))
        if intermed:
            intermediate.append(np.r_[par, residual])
        if residual < tol:
            converged = True
            break
        if trace and objfn is not None:
            objfn(par, **kwargs)
            objeval += 1
        par = pnew
        iteration += 1
    value = np.nan if objfn is None else objfn(par, **kwargs)
    if intermed:
        intermediate = np.asarray(intermediate[1:])
        return {"par": par, "value.objfn": value, "fpevals": iteration,
                "objfevals": objeval, "p.intermed": intermediate,
                "convergence": converged}
    return {"par": par, "value.objfn": value, "fpevals": iteration,
            "objfevals": objeval, "convergence": converged}
