"""Control lists for coxph and survreg."""

import math


_EPS = 2.220446049250313e-16


def coxph_control(eps=1e-9, toler_chol=None, iter_max=20, toler_inf=None, outer_max=10, timefix=True, survcheckallow="gap"):
    """Gather the Cox model control parameters."""
    if toler_chol is None:
        toler_chol = _EPS ** 0.75
    if toler_inf is None:
        toler_inf = math.sqrt(eps)
    if not isinstance(iter_max, (int, float)) or iter_max < 0:
        raise ValueError("Invalid value for iterations")
    if not isinstance(eps, (int, float)) or eps <= 0:
        raise ValueError("Invalid convergence criteria")
    if not isinstance(toler_chol, (int, float)) or toler_chol <= 0:
        raise ValueError("invalid value for toler.chol")
    if eps <= toler_chol:
        import warnings
        warnings.warn("For numerical accuracy, tolerance should be < eps", stacklevel=2)
    if not isinstance(toler_inf, (int, float)) or toler_inf <= 0:
        raise ValueError("The toler.inf setting must be >0")
    if not isinstance(timefix, bool):
        raise ValueError("timefix must be TRUE or FALSE")
    if not isinstance(outer_max, (int, float)) or outer_max <= 0:
        raise ValueError("invalid value for outer.max")
    return {
        "eps": float(eps),
        "toler.chol": float(toler_chol),
        "iter.max": int(iter_max),
        "toler.inf": float(toler_inf),
        "outer.max": int(outer_max),
        "timefix": bool(timefix),
        "survcheckallow": survcheckallow,
    }


def survreg_control(maxiter=30, rel_tolerance=1e-9, toler_chol=1e-10, iter_max=None, debug=0, outer_max=10):
    """Control parameters for survreg. iter.max replaces maxiter when it is set."""
    if iter_max is None:
        iter_max = maxiter
    else:
        maxiter = iter_max
    return {
        "iter.max": iter_max,
        "rel.tolerance": rel_tolerance,
        "toler.chol": toler_chol,
        "debug": debug,
        "maxiter": maxiter,
        "outer.max": outer_max,
    }
