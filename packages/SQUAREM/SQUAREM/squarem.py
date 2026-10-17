import numpy as np


_DEFAULTS = {
    "K": 1, "method": 3, "minimize": True, "square": True,
    "step.min0": 1, "step.max0": 1, "mstep": 4, "kr": 1,
    "objfn.inc": 1, "tol": 1e-7, "maxiter": 1500,
    "trace": False, "intermed": False,
}


def _control(control, defaults=None):
    d = _DEFAULTS if defaults is None else defaults
    control = {} if control is None else dict(control)
    unknown = set(control) - set(d)
    if unknown:
        raise ValueError("unknown names in control: " + ", ".join(sorted(unknown)))
    return {**d, **control}


def _step(method, sr2, sv2, srv):
    if method == 1:
        return -srv / sv2
    if method == 2:
        return -sr2 / srv
    return np.sqrt(sr2 / sv2)


def _result(par, value, iteration, fpevals, objfevals, convergence, intermediate=None):
    out = {"par": par, "value.objfn": value, "iter": iteration,
           "fpevals": fpevals, "objfevals": objfevals,
           "convergence": convergence}
    if intermediate is not None:
        out["p.intermed"] = np.asarray(intermediate)
    return out


def _squarem1(par, fixptfn, objfn, ctrl, kwargs):
    method, maxiter = ctrl["method"], ctrl["maxiter"]
    minimize, tol = ctrl["minimize"], ctrl["tol"]
    step_min, step_max0 = ctrl["step.min0"], ctrl["step.max0"]
    step_max, mstep, inc = step_max0, ctrl["mstep"], ctrl["objfn.inc"]
    intermed = ctrl["intermed"]
    par = np.asarray(par, dtype=float).copy()
    iteration, fpevals, objfevals = 1, 0, 1
    old = objfn(par, **kwargs)
    intermediate = [np.r_[par, old]] if intermed else None
    convergence = True
    while fpevals < maxiter:
        extrap = True
        p1 = np.asarray(fixptfn(par, **kwargs), dtype=float); fpevals += 1
        q1 = p1 - par; sr2 = float(np.dot(q1, q1))
        if np.sqrt(sr2) < tol:
            par = p1
            break
        p2 = np.asarray(fixptfn(p1, **kwargs), dtype=float); fpevals += 1
        q2 = p2 - p1; sq2 = float(np.linalg.norm(q2))
        if sq2 < tol:
            par = p2
            break
        d = q2 - q1
        sv2, srv = float(np.dot(d, d)), float(np.dot(q1, d))
        alpha = np.clip(_step(method, sr2, sv2, srv), step_min, step_max)
        pnew = par + 2 * alpha * q1 + alpha * alpha * d
        if abs(alpha - 1) > 0.01:
            pnew = np.asarray(fixptfn(pnew, **kwargs), dtype=float); fpevals += 1
        if not np.all(np.isfinite(pnew)):
            pnew, new = p2, objfn(p2, **kwargs); objfevals += 1
            if alpha == step_max: step_max = max(step_max0, step_max / mstep)
            alpha, extrap = 1, False
        else:
            if np.isfinite(inc):
                new = objfn(pnew, **kwargs); objfevals += 1
            else:
                new = old
            bad = (new > old + inc) if minimize else (new < old - inc)
            if not np.isfinite(new) or bad:
                pnew, new = p2, objfn(p2, **kwargs); objfevals += 1
                if alpha == step_max: step_max = max(step_max0, step_max / mstep)
                alpha, extrap = 1, False
        if alpha == step_max: step_max *= mstep
        if step_min < 0 and alpha == step_min: step_min *= mstep
        par, old = pnew, new
        if intermed: intermediate.append(np.r_[par, new])
        iteration += 1
    if fpevals >= maxiter: convergence = False
    if not np.isfinite(inc):
        old = objfn(par, **kwargs); objfevals += 1
    return _result(par, old, iteration, fpevals, objfevals, convergence, intermediate)


def _squarem2(par, fixptfn, ctrl, kwargs):
    method, maxiter, tol = ctrl["method"], ctrl["maxiter"], ctrl["tol"]
    step_min, step_max0 = ctrl["step.min0"], ctrl["step.max0"]
    step_max, mstep, kr = step_max0, ctrl["mstep"], ctrl["kr"]
    par = np.asarray(par, dtype=float).copy()
    iteration, fpevals = 1, 0
    intermediate = []
    convergence = True
    while fpevals < maxiter:
        p1 = np.asarray(fixptfn(par, **kwargs), dtype=float); fpevals += 1
        q1, sr2 = p1 - par, float(np.dot(p1 - par, p1 - par))
        if ctrl["intermed"]: intermediate.append(np.r_[par, np.sqrt(sr2)])
        if np.sqrt(sr2) < tol: par = p1; break
        p2 = np.asarray(fixptfn(p1, **kwargs), dtype=float); fpevals += 1
        q2, sq2 = p2 - p1, float(np.linalg.norm(p2 - p1))
        if sq2 < tol: par = p2; break
        d = q2 - q1
        alpha = np.clip(_step(method, sr2, np.dot(d, d), np.dot(q1, d)), step_min, step_max)
        pnew = par + 2 * alpha * q1 + alpha * alpha * d
        if abs(alpha - 1) > 0.01:
            ptmp = np.asarray(fixptfn(pnew, **kwargs), dtype=float); fpevals += 1
            res = np.linalg.norm(ptmp - pnew)
            parnorm = np.linalg.norm(p2) / np.sqrt(len(p2))
            if res <= kr * (1 + parnorm) + sq2:
                pnew = ptmp
            else:
                pnew, alpha = p2, 1
        if alpha == step_max: step_max *= mstep
        if step_min < 0 and alpha == step_min: step_min *= mstep
        par = pnew; iteration += 1
    if fpevals >= maxiter: convergence = False
    return _result(par, np.nan, iteration, fpevals, 0, convergence,
                   intermediate if ctrl["intermed"] else None)


def _cycle(par, fixptfn, objfn, ctrl, kwargs):
    has_obj = objfn is not None
    K, method, square = ctrl["K"], str(ctrl["method"]).lower(), ctrl["square"]
    tol, maxiter = ctrl["tol"], ctrl["maxiter"]
    par = np.asarray(par, dtype=float).copy()
    iteration, fpevals = 0 if has_obj else 1, 0
    old = objfn(par, **kwargs) if has_obj else np.nan
    objfevals = 1 if has_obj else 0
    ptmp = np.asarray(fixptfn(par, **kwargs), dtype=float); fpevals = 1
    res = np.linalg.norm(ptmp - par); par = ptmp
    convergence = True
    while fpevals < maxiter and res > tol:
        iteration += 1
        p = [par]
        for _ in range(K + 1):
            p.append(np.asarray(fixptfn(p[-1], **kwargs), dtype=float))
        fpevals += K + 1
        u = np.column_stack([p[i + 1] - p[i] for i in range(K + 1)])
        if method == "rre":
            coef = np.linalg.solve(u.T @ u, np.ones(K + 1))
        else:
            coef = np.r_[np.linalg.lstsq(u[:, :K], -u[:, K], rcond=1e-14)[0], 1.]
        if abs(np.sum(coef)) < 1e-7:
            par, res = p[-1], np.linalg.norm(u[:, -1]); continue
        coef = coef / np.sum(coef)
        if not square:
            pnew = sum(coef[i] * p[i] for i in range(K + 1))
        else:
            if K > 1:
                for i in range(K - 1):
                    p.append(np.asarray(fixptfn(p[i + K + 1], **kwargs), dtype=float))
                fpevals += K - 1
            pnew = np.zeros_like(par)
            for i in range(K + 1):
                for j in range(K + 1):
                    pnew += coef[i] * coef[j] * p[i + j]
        ptest = np.asarray(fixptfn(pnew, **kwargs), dtype=float); fpevals += 1
        sq = np.linalg.norm(p[-1] - p[-2])
        if has_obj:
            new = objfn(ptest, **kwargs); objfevals += 1
            bad = new > old + ctrl["objfn.inc"] if ctrl["minimize"] else new < old - ctrl["objfn.inc"]
            if not np.isfinite(new) or bad:
                par, res = p[-1], sq
                continue
            old = new
        res = np.linalg.norm(ptest - pnew)
        if not has_obj and res > ctrl["kr"] * (1 + np.linalg.norm(p[-1]) / np.sqrt(len(par))) + sq:
            par, res = p[-1], sq
        else:
            par = ptest
    if fpevals >= maxiter: convergence = False
    return _result(par, old, iteration, fpevals, objfevals, convergence)


def squarem(par, fixptfn, objfn=None, control=None, **kwargs):
    """Squared extrapolation acceleration for a fixed-point mapping."""
    ctrl = _control(control)
    if ctrl["K"] == 1 and ctrl["method"] not in (1, 2, 3):
        ctrl["method"] = 3
    if ctrl["K"] > 1 and str(ctrl["method"]).lower() not in ("rre", "mpe"):
        ctrl["method"] = "rre"
    if ctrl["K"] == 1:
        return (_squarem1 if objfn is not None else _squarem2)(
            par, fixptfn, objfn, ctrl, kwargs) if objfn is not None else _squarem2(par, fixptfn, ctrl, kwargs)
    return _cycle(par, fixptfn, objfn, ctrl, kwargs)
