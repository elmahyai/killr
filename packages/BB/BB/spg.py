"""Spectral projected gradient, from BB::spg."""

import time
import warnings

import numpy as np

from BB.project import project_linear


def _names(control):
    if control is None:
        return []
    return list(control)


def _unknown(control, allowed):
    names = _names(control)
    bad = [name for name in names if name not in allowed]
    if bad:
        raise ValueError("unknown names in control: " + " ".join(bad))


def _as_float_vector(par):
    array = np.asarray(par, dtype=float)
    if array.ndim == 0:
        array = array.reshape(1)
    return array.astype(float, copy=True)


def _call(fn, par, kwargs):
    try:
        return fn(par, **kwargs)
    except Exception as exc:
        return exc


def _bad_number(value):
    array = np.asarray(value, dtype=float)
    return (not np.issubdtype(array.dtype, np.number)) or np.any(np.isnan(array))


def spg(
    par,
    fn,
    gr=None,
    method=3,
    lower=-np.inf,
    upper=np.inf,
    project=None,
    projectArgs=None,
    control=None,
    quiet=False,
    alertConvergence=True,
    **kwargs,
):
    """Minimize fn with the spectral projected gradient method."""
    par = _as_float_vector(par)
    lower_value = np.asarray(lower, dtype=float)
    upper_value = np.asarray(upper, dtype=float)
    box = bool(np.any(np.isfinite(upper_value)) or np.any(np.isfinite(lower_value)))
    if isinstance(project, str):
        if project == "projectLinear":
            project = project_linear
        else:
            raise ValueError(f"object '{project}' of mode 'function' was not found")
    project_now = project
    args = {} if projectArgs is None else dict(projectArgs)
    if box:
        if project_now is None:
            if "lower" in args or "upper" in args:
                warnings.warn(
                    "Using lower and upper spg arguments, not using those specified in projectArgs.",
                    stacklevel=2,
                )
            args["lower"] = np.repeat(lower_value, par.size) if lower_value.size == 1 else lower_value
            args["upper"] = np.repeat(upper_value, par.size) if upper_value.size == 1 else upper_value

            def project_now(point, lower, upper):
                point = np.array(point, dtype=float, copy=True)
                point[point < lower] = np.asarray(lower, dtype=float)[point < lower]
                point[point > upper] = np.asarray(upper, dtype=float)[point > upper]
                return point

        if project_now is project_linear:
            if "lower" in args or "upper" in args:
                warnings.warn(
                    "Using lower and upper spg arguments, not using those specified in projectArgs.",
                    stacklevel=2,
                )
            if "A" not in args or args["A"] is None:
                raise ValueError("projectLinear requires the A matrix to be specified in projectArgs.")
            if "b" not in args or args["b"] is None:
                raise ValueError("projectLinear requires the b vector to be specified in projectArgs.")
            lower_full = np.repeat(lower_value, par.size) if lower_value.size == 1 else lower_value
            finite = np.isfinite(lower_full)
            if np.any(finite):
                args["A"] = np.vstack([np.asarray(args["A"], dtype=float), np.eye(par.size)[finite]])
                args["b"] = np.concatenate([np.asarray(args["b"], dtype=float).reshape(-1), lower_full[finite]])
            upper_full = np.repeat(upper_value, par.size) if upper_value.size == 1 else upper_value
            finite = np.isfinite(upper_full)
            if np.any(finite):
                args["A"] = np.vstack([np.asarray(args["A"], dtype=float), (-np.eye(par.size))[finite]])
                args["b"] = np.concatenate([np.asarray(args["b"], dtype=float).reshape(-1), -upper_full[finite]])
    projecting = box or project_now is not None
    allowed = [
        "M", "maxit", "ftol", "gtol", "maxfeval", "maximize", "trace", "triter",
        "eps", "checkGrad", "checkGrad.tol",
    ]
    _unknown(control, allowed)
    ctrl = {
        "M": 10, "maxit": 1500, "ftol": 1e-10, "gtol": 1e-5, "maxfeval": 10000,
        "maximize": False, "trace": not quiet, "triter": 10, "eps": 1e-7,
        "checkGrad": None, "checkGrad.tol": 1e-6,
    }
    if control:
        ctrl.update(control)
    memory = int(ctrl["M"])
    maxit = ctrl["maxit"]
    ftol = ctrl["ftol"]
    gtol = ctrl["gtol"]
    maxfeval = ctrl["maxfeval"]
    maximize = bool(ctrl["maximize"])
    trace = bool(ctrl["trace"])
    triter = ctrl["triter"]
    eps = ctrl["eps"]
    check_grad = ctrl["checkGrad"]
    check_tol = ctrl["checkGrad.tol"]
    sign = -1.0 if maximize else 1.0

    def func(point, **extra):
        value = fn(point, **extra)
        return np.array([-value] if maximize else [value], dtype=float)

    started = time.process_time()
    current = _call(func, par, kwargs)
    elapsed = time.process_time() - started
    feval = 1
    if check_grad is None:
        if (elapsed * 6 * par.size) < 10:
            check_grad = True
        else:
            check_grad = False
            if gr is not None:
                warnings.warn(
                    "Default checking of gradient turned off because of time require."
                    "See the help for spg to enable this.",
                    stacklevel=2,
                )
    if isinstance(current, Exception):
        raise ValueError("Failure in initial function evaluation!" + str(current))
    current = np.asarray(current, dtype=float).reshape(-1)
    if current.size != 1 or not np.isfinite(current[0]):
        if current.size != 1:
            raise ValueError("function must return a scalar numeric value!")
        raise ValueError("Failure in initial function evaluation!")
    f_value = float(current[0])
    f0 = f_value
    state = {"f": f_value}

    def nmls(point, value, direction, gtd, lastfv, count):
        gamma = 1e-4
        fmax = max(lastfv)
        alpha = 1.0
        trial = point + alpha * direction
        new_value = _call(func, trial, kwargs)
        count += 1
        if isinstance(new_value, Exception) or _bad_number(new_value):
            return {"p": None, "f": None, "feval": None, "lsflag": 1}
        new_value = float(np.asarray(new_value, dtype=float).reshape(-1)[0])
        while new_value > fmax + gamma * alpha * gtd:
            if alpha <= 0.1:
                alpha = alpha / 2
            else:
                atemp = -(gtd * alpha ** 2) / (2 * (new_value - value - alpha * gtd))
                if atemp < 0.1 or atemp > 0.9 * alpha:
                    atemp = alpha / 2
                alpha = atemp
            trial = point + alpha * direction
            new_value = _call(func, trial, kwargs)
            count += 1
            if isinstance(new_value, Exception) or _bad_number(new_value):
                return {"p": None, "f": None, "feval": None, "lsflag": 1}
            new_value = float(np.asarray(new_value, dtype=float).reshape(-1)[0])
            if count > maxfeval:
                return {"p": None, "f": None, "feval": None, "lsflag": 2}
        return {"p": trial, "f": new_value, "feval": count, "lsflag": 0}

    if gr is not None and check_grad:
        from numderiv import grad

        grad_num = np.asarray(grad(func=fn, x=par, **kwargs), dtype=float)
        grad_analytic = np.asarray(gr(par, **kwargs), dtype=float)
        scale = 1 + np.abs(np.asarray(fn(par, **kwargs), dtype=float))
        max_diff = float(np.max(np.abs((grad_analytic - grad_num) / scale)))
        if not max_diff < check_tol:
            print(
                "Gradient check details:  max. relative difference in gradients= ",
                max_diff,
                "\n\n  analytic gradient:",
                grad_analytic,
                "\n\n  numerical gradient:",
                grad_num,
            )
            raise ValueError(
                "Analytic gradient does not seem correct! See comparison above. "
                "Fix it, remove it, or increase checkGrad.tol."
            )
    user_gradient = gr

    def numerical(point, **_extra):
        slopes = np.empty(point.size)
        for i in range(point.size):
            moved = np.array(point, dtype=float, copy=True)
            moved[i] = moved[i] + eps
            slopes[i] = (float(np.asarray(func(moved, **kwargs), dtype=float).reshape(-1)[0]) - state["f"]) / eps
        return slopes

    if user_gradient is None:
        gradient_fn = numerical
    elif maximize:
        def gradient_fn(point, **extra):
            return -np.asarray(user_gradient(point, **extra), dtype=float)
    else:
        def gradient_fn(point, **extra):
            return np.asarray(user_gradient(point, **extra), dtype=float)

    lmin = 1e-30
    lmax = 1e30
    iteration = 0
    lastfv = np.full(memory, -1e99)
    f_change = np.inf
    if projecting:
        projected = _call(project_now, par, args)
        if isinstance(projected, Exception):
            raise ValueError("Failure in projecting initial guess!" + str(projected))
        par = np.asarray(projected, dtype=float)
    if np.any(~np.isfinite(par)):
        raise ValueError("Failure in initial guess!")
    pbest = np.array(par, copy=True)
    slope = _call(gradient_fn, par, kwargs)
    if isinstance(slope, Exception):
        raise ValueError("Failure in initial gradient evaluation!" + str(slope))
    slope = np.asarray(slope, dtype=float).reshape(-1)
    if np.any(np.isnan(slope)):
        raise ValueError("Failure in initial gradient evaluation!")
    lastfv[0] = f_value
    fbest = f_value
    pg = par - slope
    if projecting:
        pg = _call(project_now, pg, args)
        if isinstance(pg, Exception):
            raise ValueError("Failure in initial projection!" + str(pg))
        pg = np.asarray(pg, dtype=float)
    if np.any(np.isnan(pg)):
        raise ValueError("Failure in initial projection!")
    pg = pg - par
    pginfn = float(np.max(np.abs(pg)))
    gbest = float(np.sqrt(np.dot(pg, pg)))
    lam = None
    if pginfn != 0:
        lam = min(lmax, max(lmin, 1 / pginfn))
    if trace:
        print("iter: ", 0, " f-value: ", f0 * sign, " pgrad: ", pginfn, sep="")
    lsflag = None
    while pginfn > gtol and iteration <= maxit and f_change > ftol:
        iteration += 1
        direction = par - lam * slope
        if projecting:
            direction = _call(project_now, direction, args)
            if isinstance(direction, Exception) or np.any(np.isnan(np.asarray(direction, dtype=float))):
                lsflag = 4
                break
            direction = np.asarray(direction, dtype=float)
        direction = direction - par
        gtd = float(np.dot(slope, direction))
        if np.isinf(gtd):
            lsflag = 4
            break
        step = nmls(par, f_value, direction, gtd, lastfv, feval)
        lsflag = step["lsflag"]
        if lsflag != 0:
            break
        f_change = abs(f_value - step["f"])
        f_value = step["f"]
        state["f"] = f_value
        pnew = np.asarray(step["p"], dtype=float)
        feval = step["feval"]
        lastfv[iteration % memory] = f_value
        gnew = _call(gradient_fn, pnew, kwargs)
        if isinstance(gnew, Exception) or np.any(np.isnan(np.asarray(gnew, dtype=float))):
            lsflag = 3
            break
        gnew = np.asarray(gnew, dtype=float).reshape(-1)
        delta = pnew - par
        change = gnew - slope
        sts = float(np.dot(delta, delta))
        yty = float(np.dot(change, change))
        sty = float(np.dot(delta, change))
        if method == 1:
            lam = lmax if sts == 0 or sty < 0 else min(lmax, max(lmin, sts / sty))
        elif method == 2:
            lam = lmax if sty < 0 or yty == 0 else min(lmax, max(lmin, sty / yty))
        elif method == 3:
            lam = lmax if sts == 0 or yty == 0 else min(lmax, max(lmin, math_sqrt(sts / yty)))
        par = pnew
        slope = gnew
        pg = par - slope
        if projecting:
            pg = _call(project_now, pg, args)
            if isinstance(pg, Exception) or np.any(np.isnan(np.asarray(pg, dtype=float))):
                lsflag = 4
                break
            pg = np.asarray(pg, dtype=float)
        pg = pg - par
        pginfn = float(np.max(np.abs(pg)))
        if trace and iteration % triter == 0:
            print("iter: ", iteration, " f-value: ", sign * f_value, " pgrad: ", pginfn, sep="")
        if f_value < fbest:
            fbest = f_value
            pbest = np.array(pnew, copy=True)
            gbest = pginfn
    if lsflag is None:
        if not quiet:
            warnings.warn("convergence tolerance satisified at intial parameter values.", stacklevel=2)
        lsflag = 0
    if lsflag == 0:
        conv = None
        if pginfn <= gtol or f_change <= ftol:
            conv = (0, "Successful convergence")
        if iteration >= maxit:
            conv = (1, "Maximum number of iterations exceeded")
        reported = sign * fbest
        par = pbest
    else:
        par = pbest
        reported = sign * fbest
        f_value = reported
        pginfn = gbest
        messages = {
            1: (3, "Failure:  Error in function evaluation"),
            2: (2, "Maximum function evals exceeded"),
            3: (4, "Failure:  Error in gradient evaluation"),
            4: (5, "Failure:  Error in projection"),
        }
        conv = messages[lsflag]
    if alertConvergence and conv[0] != 0:
        warnings.warn("Unsuccessful convergence.", stacklevel=2)
    return {
        "par": np.asarray(par, dtype=float),
        "value": float(reported),
        "gradient": float(pginfn),
        "fn.reduction": float(sign * (f0 - f_value)),
        "iter": int(iteration),
        "feval": int(feval),
        "convergence": int(conv[0]),
        "message": conv[1],
    }


def math_sqrt(value):
    return value ** 0.5
