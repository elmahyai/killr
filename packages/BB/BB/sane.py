"""DF-SANE and SANE, from BB::dfsane and BB::sane."""

import math
import warnings

import numpy as np

from BB.nelder import nelder_mead
from BB.spg import _as_float_vector, _call, _unknown


def _sign(value):
    if value > 0:
        return 1.0
    if value < 0:
        return -1.0
    return 0.0


def _merit(fn, kwargs):
    def objective(point, **extra):
        merged = dict(kwargs)
        merged.update(extra)
        residual = np.asarray(fn(point, **merged), dtype=float).reshape(-1)
        return float(np.dot(residual, residual))

    return objective


def dfsane(par, fn, method=2, control=None, quiet=False, alertConvergence=True, **kwargs):
    """Solve fn(x) = 0 with the derivative-free spectral residual method."""
    allowed = ["maxit", "M", "tol", "trace", "triter", "noimp", "NM", "BFGS"]
    _unknown(control, allowed)
    ctrl = {
        "maxit": 1500, "M": 10, "tol": 1e-7, "trace": not quiet, "triter": 10,
        "noimp": 100, "NM": False, "BFGS": False,
    }
    if control:
        ctrl.update(control)
    maxit = ctrl["maxit"]
    memory = int(ctrl["M"])
    tol = ctrl["tol"]
    trace = bool(ctrl["trace"])
    triter = ctrl["triter"]
    noimp = ctrl["noimp"]
    use_nm = bool(ctrl["NM"])
    use_bfgs = bool(ctrl["BFGS"])
    par = _as_float_vector(par)

    def lsm(x, residual, fval, alfa, lastfv, eta, fcnt, bl):
        maxbl = 100
        gamma = 1e-4
        sigma1 = 0.1
        sigma2 = 0.5
        lam1 = lam2 = 1.0
        cbl = 0
        fmax = max(lastfv)
        fune = None
        xnew = x
        new_residual = residual
        while cbl < maxbl:
            direction = -alfa * residual
            xnew = x + lam1 * direction
            new_residual = _call(fn, xnew, kwargs)
            fcnt += 1
            if isinstance(new_residual, Exception) or np.any(np.isnan(np.asarray(new_residual, dtype=float))):
                return {"xnew": None, "Fnew": None, "fcnt": fcnt, "bl": bl, "lsflag": 1, "fune": None}
            new_residual = np.asarray(new_residual, dtype=float).reshape(-1)
            fune1 = float(np.dot(new_residual, new_residual))
            if fune1 <= (fmax + eta - (lam1 ** 2 * gamma * fval)):
                if cbl >= 1:
                    bl += 1
                return {"xnew": xnew, "Fnew": new_residual, "fcnt": fcnt, "bl": bl, "lsflag": 0, "fune": fune1}
            xnew = x - lam2 * direction
            new_residual = _call(fn, xnew, kwargs)
            fcnt += 1
            if isinstance(new_residual, Exception) or np.any(np.isnan(np.asarray(new_residual, dtype=float))):
                return {"xnew": None, "Fnew": None, "fcnt": fcnt, "bl": bl, "lsflag": 1, "fune": None}
            new_residual = np.asarray(new_residual, dtype=float).reshape(-1)
            fune2 = float(np.dot(new_residual, new_residual))
            fune = fune2
            if fune2 <= (fmax + eta - (lam2 ** 2 * gamma * fval)):
                if cbl >= 1:
                    bl += 1
                return {"xnew": xnew, "Fnew": new_residual, "fcnt": fcnt, "bl": bl, "lsflag": 0, "fune": fune2}
            lamc = (2 * fval * lam1 ** 2) / (2 * (fune1 + (2 * lam1 - 1) * fval))
            c1 = sigma1 * lam1
            c2 = sigma2 * lam1
            lam1 = c1 if lamc < c1 else c2 if lamc > c2 else lamc
            lamc = (2 * fval * lam2 ** 2) / (2 * (fune2 + (2 * lam2 - 1) * fval))
            c1 = sigma1 * lam2
            c2 = sigma2 * lam2
            lam2 = c1 if lamc < c1 else c2 if lamc > c2 else lamc
            cbl += 1
        return {"xnew": xnew, "Fnew": new_residual, "fcnt": fcnt, "bl": bl, "lsflag": 2, "fune": fune}

    n = par.size
    fcnt = iteration = bl = 0
    alfa = eta = 1.0
    eps = 1e-10
    lastfv = np.zeros(memory)
    if use_nm:
        objective = _merit(fn, kwargs)
        try:
            started = nelder_mead(par, objective, maxit=100)
        except Exception as exc:
            print(exc)
            raise ValueError("\nFailure in Nelder-Mead Start.  Try another starting value \n") from exc
        if np.any(np.isnan(started["par"])):
            raise ValueError("Failure in Nelder-Mead Start (NaN value).  Try another starting value \n")
        par = np.asarray(started["par"], dtype=float)
        fcnt = int(started["counts"])
    residual = _call(fn, par, kwargs)
    fcnt += 1
    if isinstance(residual, Exception):
        raise ValueError("Failure in initial functional evaluation. \n")
    try:
        residual = np.asarray(residual, dtype=float)
    except (TypeError, ValueError):
        raise ValueError("Function must return a vector numeric value.") from None
    if residual.ndim != 1:
        raise ValueError("Function must return a vector numeric value.")
    if not np.all(np.isfinite(residual)):
        raise ValueError("Failure in initial functional evaluation. \n")
    if residual.size == 1 and not quiet:
        warnings.warn("Function returns a scalar. Function BBoptim or spg is better.", stacklevel=2)
    norm_f = float(np.sqrt(np.dot(residual, residual)))
    f0 = norm_f
    if trace:
        print("Iteration: ", 0, " ||F(x0)||: ", f0 / math.sqrt(n))
    pbest = np.array(par, copy=True)
    best = norm_f
    lastfv[0] = norm_f ** 2
    flag = 0
    knoimp = 0
    alfa1 = alfa2 = alfa
    while norm_f / math.sqrt(n) > tol and iteration <= maxit:
        if abs(alfa) <= eps or abs(alfa) >= 1 / eps:
            if norm_f > 1:
                alfa = 1.0
            elif 1e-5 <= norm_f <= 1:
                alfa = 1 / norm_f
            elif norm_f < 1e-5:
                alfa = 1e5
        if iteration == 0:
            alfa = min(1 / norm_f, 1)
            alfa1 = alfa2 = alfa
        temp = alfa2
        alfa2 = alfa
        if norm_f <= 0.01:
            alfa = alfa1
        alfa1 = temp
        step = lsm(par, residual, norm_f ** 2, alfa, lastfv, eta, fcnt, bl)
        fcnt = step["fcnt"]
        bl = step["bl"]
        flag = step["lsflag"]
        if flag > 0:
            break
        new_residual = step["Fnew"]
        pnew = np.asarray(step["xnew"], dtype=float)
        fun = step["fune"]
        delta_p = pnew - par
        delta_f = new_residual - residual
        pf = float(np.dot(delta_p, delta_f))
        pp = float(np.dot(delta_p, delta_p))
        ff = float(np.dot(delta_f, delta_f))
        if method == 1:
            alfa = pp / pf
        elif method == 2:
            alfa = pf / ff
        elif method == 3:
            alfa = _sign(pf) * math.sqrt(pp / ff)
        if isinstance(alfa, float) and math.isnan(alfa):
            alfa = eps
        par = pnew
        residual = new_residual
        norm_f = math.sqrt(fun)
        if norm_f < best:
            pbest = np.array(par, copy=True)
            best = norm_f
            knoimp = 0
        else:
            knoimp += 1
        iteration += 1
        lastfv[iteration % memory] = fun
        eta = f0 / (iteration + 1) ** 2
        if trace and iteration % triter == 0:
            print("iteration: ", iteration, " ||F(xn)|| =  ", norm_f)
        if knoimp == noimp:
            flag = 3
            break
    if flag == 0:
        if best / math.sqrt(n) <= tol:
            conv = (0, "Successful convergence")
        elif iteration > maxit:
            conv = (1, "Maximum limit for iterations exceeded")
        else:
            conv = (2, "Method stagnated")
    elif flag == 1:
        conv = (3, "Failure: Error in function evaluation")
    elif flag == 2:
        conv = (4, "Failure: Maximum limit on steplength reductions exceeded")
    else:
        conv = (5, "Lack of improvement in objective function")
    if use_bfgs and conv[0] in (2, 5):
        raise NotImplementedError("L-BFGS-B in optim is not available")
    if alertConvergence and conv[0] != 0:
        warnings.warn("Unsuccessful convergence.", stacklevel=2)
    return {
        "par": np.asarray(pbest, dtype=float),
        "residual": float(best / math.sqrt(pbest.size)),
        "fn.reduction": float(f0 - best),
        "feval": int(fcnt),
        "iter": int(iteration),
        "convergence": int(conv[0]),
        "message": conv[1],
    }


def sane(par, fn, method=2, control=None, quiet=False, alertConvergence=True, **kwargs):
    """Solve fn(x) = 0 with the older spectral residual method."""
    allowed = ["maxit", "M", "tol", "trace", "triter", "noimp", "NM", "BFGS"]
    _unknown(control, allowed)
    ctrl = {
        "maxit": 1500, "M": 10, "tol": 1e-7, "trace": not quiet, "triter": 10,
        "noimp": 100, "NM": False, "BFGS": False,
    }
    if control:
        ctrl.update(control)
    maxit = ctrl["maxit"]
    memory = int(ctrl["M"])
    tol = ctrl["tol"]
    trace = bool(ctrl["trace"])
    triter = ctrl["triter"]
    noimp = ctrl["noimp"]
    use_nm = bool(ctrl["NM"])
    use_bfgs = bool(ctrl["BFGS"])
    par = _as_float_vector(par)

    def line_search(x, residual, fval, dg, lastfv, sgn, lam, fcnt, bl):
        maxbl = 100
        gamma = 1e-4
        sigma1 = 0.1
        sigma2 = 0.5
        cbl = 0
        fmax = max(lastfv)
        gpd = -2 * abs(dg)
        while cbl < maxbl:
            xnew = x + lam * sgn * residual
            new_residual = _call(fn, xnew, kwargs)
            fcnt += 1
            if isinstance(new_residual, Exception) or np.any(np.isnan(np.asarray(new_residual, dtype=float))):
                return {"xnew": None, "Fnew": None, "fcnt": fcnt, "bl": bl, "lsflag": 1, "fune": None}
            new_residual = np.asarray(new_residual, dtype=float).reshape(-1)
            fune = float(np.dot(new_residual, new_residual))
            if fune <= (fmax + lam * gpd * gamma):
                if cbl >= 1:
                    bl += 1
                return {
                    "xnew": xnew, "Fnew": new_residual, "fcnt": fcnt, "lambda": lam,
                    "bl": bl, "lsflag": 0, "fune": fune,
                }
            lamc = -(gpd * lam ** 2) / (2 * (fune - fval - lam * gpd))
            c1 = sigma1 * lam
            c2 = sigma2 * lam
            if lamc < c1:
                lam = c1
            elif lamc > c2:
                lam = c2
            else:
                lam = lamc
            cbl += 1
        return {"xnew": None, "Fnew": None, "fcnt": fcnt, "lambda": None, "bl": bl, "lsflag": 2, "fune": None}

    n = par.size
    fcnt = iteration = bl = 0
    alfa = 1.0
    eps = 1e-10
    step_h = 1e-7
    lastfv = np.zeros(memory)
    if use_nm:
        objective = _merit(fn, kwargs)
        try:
            started = nelder_mead(par, objective, maxit=100)
        except Exception as exc:
            print(exc)
            raise ValueError("\nFailure in Nelder-Mead Start.  Try another starting value \n") from exc
        if np.any(np.isnan(started["par"])):
            raise ValueError("Failure in Nelder-Mead Start (NaN value).  Try another starting value \n")
        par = np.asarray(started["par"], dtype=float)
        fcnt = int(started["counts"])
    residual = _call(fn, par, kwargs)
    fcnt += 1
    if isinstance(residual, Exception):
        raise ValueError(" Failure in initial functional evaluation.")
    try:
        residual = np.asarray(residual, dtype=float)
    except (TypeError, ValueError):
        raise ValueError("Function must return a vector numeric value.") from None
    if residual.ndim != 1:
        raise ValueError("Function must return a vector numeric value.")
    if not np.all(np.isfinite(residual)):
        raise ValueError(" Failure in initial functional evaluation.")
    if residual.size == 1 and not quiet:
        warnings.warn("Function returns a scalar. Function BBoptim or spg is better.", stacklevel=2)
    norm_f = float(np.sqrt(np.dot(residual, residual)))
    f0 = norm_f
    if trace:
        print("Iteration: ", 0, " ||F(x0)||: ", f0 / math.sqrt(n))
    pbest = np.array(par, copy=True)
    best = norm_f
    lastfv[0] = norm_f ** 2
    flag = 0
    knoimp = 0
    alfa1 = alfa2 = alfa
    while norm_f / math.sqrt(n) > tol and iteration <= maxit:
        shifted = _call(fn, par + step_h * residual, kwargs)
        fcnt += 1
        if isinstance(shifted, Exception) or np.any(np.isnan(np.asarray(shifted, dtype=float))):
            flag = 1
            break
        shifted = np.asarray(shifted, dtype=float).reshape(-1)
        dg = (float(np.dot(residual, shifted)) - norm_f ** 2) / step_h
        if abs(dg / norm_f ** 2) < eps or not math.isfinite(dg):
            flag = 3
            break
        if alfa <= eps or alfa >= 1 / eps:
            if norm_f > 1:
                alfa = 1.0
            elif 1e-5 <= norm_f <= 1:
                alfa = norm_f
            elif norm_f < 1e-5:
                alfa = 1e-5
        sgn = -1.0 if dg > 0 else 1.0
        if iteration == 0:
            alfa = max(norm_f, 1)
            alfa1 = alfa2 = alfa
        temp = alfa2
        alfa2 = alfa
        if norm_f <= 0.01:
            alfa = alfa1
        alfa1 = temp
        step = line_search(par, residual, norm_f ** 2, dg, lastfv, sgn, 1 / alfa, fcnt, bl)
        fcnt = step["fcnt"]
        bl = step["bl"]
        flag = step["lsflag"]
        if flag > 0:
            break
        new_residual = step["Fnew"]
        pnew = np.asarray(step["xnew"], dtype=float)
        fun = step["fune"]
        lam = step["lambda"]
        if method == 1:
            alfa = float(np.dot(residual, residual - new_residual)) / (lam * float(np.dot(residual, residual)))
        elif method == 2:
            delta = residual - new_residual
            alfa = float(np.dot(delta, delta)) / (lam * float(np.dot(residual, delta)))
        elif method == 3:
            alfa = math.sqrt(float(np.dot(residual - new_residual, residual - new_residual)) / (lam ** 2 * float(np.dot(residual, residual))))
        if isinstance(alfa, float) and math.isnan(alfa):
            alfa = eps
        par = pnew
        residual = new_residual
        norm_f = math.sqrt(fun)
        if norm_f < best:
            pbest = np.array(par, copy=True)
            best = norm_f
            knoimp = 0
        else:
            knoimp += 1
        if knoimp == noimp:
            flag = 4
            break
        iteration += 1
        lastfv[iteration % memory] = fun
        if trace and iteration % triter == 0:
            print("\n iteration: ", iteration, " ||F(xn)|| =  ", norm_f)
    if flag == 0:
        conv = None
        if best / math.sqrt(n) <= tol:
            conv = (0, "Successful convergence")
        if iteration > maxit:
            conv = (1, "Maximum number of iterations exceeded")
    elif flag == 1:
        conv = (2, "Error in function evaluation")
    elif flag == 2:
        conv = (3, "Maximum limit on steplength reductions exceeded")
    elif flag == 3:
        conv = (4, "Anomalous iteration")
    else:
        conv = (5, "Lack of improvement in objective function")
    if use_bfgs and conv[0] in (4, 5):
        raise NotImplementedError("L-BFGS-B in optim is not available")
    if alertConvergence and conv[0] != 0:
        warnings.warn("Unsuccessful convergence.", stacklevel=2)
    return {
        "par": np.asarray(pbest, dtype=float),
        "residual": float(best / math.sqrt(pbest.size)),
        "fn.reduction": float(f0 - best),
        "feval": int(fcnt),
        "iter": int(iteration),
        "convergence": int(conv[0]),
        "message": conv[1],
    }
