"""Algorithm wrappers. Each one fills an algorithm name and calls nloptr."""

from __future__ import annotations

import warnings

import numpy as np

from nloptr._core import nloptr
from nloptr._finite import nl_grad, nl_jacobian
from nloptr._options import nl_opts
from nloptr._print import print_nloptr

_HIN_WARNING = (
    "The old behavior for hin >= 0 has been deprecated. Please "
    "restate the inequality to be <=0. The ability to use the old "
    "behavior will be removed in a future release."
)
_HINJAC_WARNING = (
    "The old behavior for hinjac >= 0 has been deprecated. Please "
    "restate the inequality to be <=0. The ability to use the old "
    "behavior will be removed in a future release."
)


def _bind(fn, kwargs):
    if kwargs:
        return lambda x: fn(x, **kwargs)
    return fn


def _negate(fn, kwargs):
    def wrapped(x):
        value = fn(x, **kwargs) if kwargs else fn(x)
        return -np.asarray(value, dtype=float)
    return wrapped


def _box(result, nl_info, **extra):
    if nl_info:
        print_nloptr(result)
    out = {
        "par": np.asarray(result["solution"], dtype=float).copy(),
        "value": float(result["objective"]),
        "iter": int(result["iterations"]),
    }
    out.update(extra)
    out["convergence"] = int(result["status"])
    out["message"] = result["message"]
    return out


def _gradient(fn, gr, kwargs):
    if gr is None:
        return lambda x: nl_grad(x, fn)
    bound = _bind(gr, kwargs)
    return lambda x: bound(x)


def lbfgs(x0, fn, gr=None, lower=None, upper=None, nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LD_LBFGS"
    objective = _bind(fn, kwargs)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, opts=opts,
    )
    return _box(result, nl_info)


def tnewton(x0, fn, gr=None, lower=None, upper=None, precond=True, restart=True,
            nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    if precond:
        opts["algorithm"] = "NLOPT_LD_TNEWTON_PRECOND_RESTART" if restart else "NLOPT_LD_TNEWTON_PRECOND"
    else:
        opts["algorithm"] = "NLOPT_LD_TNEWTON_RESTART" if restart else "NLOPT_LD_TNEWTON"
    objective = _bind(fn, kwargs)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, opts=opts,
    )
    return _box(result, nl_info)


def varmetric(x0, fn, gr=None, rank2=True, lower=None, upper=None,
              nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LD_VAR2" if rank2 else "NLOPT_LD_VAR1"
    objective = _bind(fn, kwargs)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, opts=opts,
    )
    return _box(result, nl_info)


def neldermead(x0, fn, lower=None, upper=None, nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LN_NELDERMEAD"
    result = nloptr(x0, _bind(fn, kwargs), lb=lower, ub=upper, opts=opts)
    return _box(result, nl_info)


def sbplx(x0, fn, lower=None, upper=None, nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LN_SBPLX"
    result = nloptr(x0, _bind(fn, kwargs), lb=lower, ub=upper, opts=opts)
    return _box(result, nl_info)


def bobyqa(x0, fn, lower=None, upper=None, nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LN_BOBYQA"
    result = nloptr(x0, _bind(fn, kwargs), lb=lower, ub=upper, opts=opts)
    return _box(result, nl_info)


def newuoa(x0, fn, nl_info=False, control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LN_NEWUOA"
    result = nloptr(x0, _bind(fn, kwargs), opts=opts)
    return _box(result, nl_info)


def _inequality(hin, hinjac, deprecated, kwargs, need_jacobian):
    if hin is None:
        return None, None
    if deprecated:
        warnings.warn(_HIN_WARNING)
        hin_fn = _negate(hin, kwargs)
    else:
        hin_fn = hin if kwargs else hin
        if kwargs and not deprecated:
            hin_fn = _bind(hin, kwargs)
    jac = None
    if need_jacobian:
        if hinjac is None:
            jac = lambda x: nl_jacobian(x, hin_fn)
        elif deprecated:
            warnings.warn(_HINJAC_WARNING)
            original = hinjac
            jac = lambda x: -np.asarray(original(x), dtype=float)
        else:
            jac = _bind(hinjac, kwargs) if kwargs else hinjac
    return hin_fn, jac


def cobyla(x0, fn, lower=None, upper=None, hin=None, nl_info=False,
           control=None, deprecated_behavior=True, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LN_COBYLA"
    hin_fn, _jac = _inequality(hin, None, deprecated_behavior, kwargs, False)
    result = nloptr(
        x0, _bind(fn, kwargs), lb=lower, ub=upper, eval_g_ineq=hin_fn, opts=opts,
    )
    return _box(result, nl_info)


def mma(x0, fn, gr=None, lower=None, upper=None, hin=None, hinjac=None,
        nl_info=False, control=None, deprecated_behavior=True, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LD_MMA"
    objective = _bind(fn, kwargs)
    hin_fn, jac = _inequality(hin, hinjac, deprecated_behavior, kwargs, True)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, eval_g_ineq=hin_fn, eval_jac_g_ineq=jac, opts=opts,
    )
    return _box(result, nl_info)


def ccsaq(x0, fn, gr=None, lower=None, upper=None, hin=None, hinjac=None,
          nl_info=False, control=None, deprecated_behavior=True, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LD_CCSAQ"
    objective = _bind(fn, kwargs)
    hin_fn, jac = _inequality(hin, hinjac, deprecated_behavior, kwargs, True)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, eval_g_ineq=hin_fn, eval_jac_g_ineq=jac, opts=opts,
    )
    return _box(result, nl_info)


def slsqp(x0, fn, gr=None, lower=None, upper=None, hin=None, hinjac=None,
          heq=None, heqjac=None, nl_info=False, control=None,
          deprecated_behavior=True, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_LD_SLSQP"
    objective = _bind(fn, kwargs)
    hin_fn, hin_jac = _inequality(hin, hinjac, deprecated_behavior, kwargs, True)
    heq_fn, heq_jac = _equality(heq, heqjac)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, eval_g_ineq=hin_fn, eval_jac_g_ineq=hin_jac,
        eval_g_eq=heq_fn, eval_jac_g_eq=heq_jac, opts=opts,
    )
    return _box(result, nl_info)


def _equality(heq, heqjac):
    if heq is None:
        return None, None
    heq_fn = lambda x: heq(x)
    if heqjac is None:
        heq_jac = lambda x: nl_jacobian(x, heq_fn)
    else:
        heq_jac = lambda x: heqjac(x)
    return heq_fn, heq_jac


def auglag(x0, fn, gr=None, lower=None, upper=None, hin=None, hinjac=None,
           heq=None, heqjac=None, localsolver="COBYLA", localtol=1e-6,
           ineq2local=False, nl_info=False, control=None,
           deprecated_behavior=True, **kwargs):
    if ineq2local:
        raise ValueError("Inequalities to local solver: feature not yet implemented.")
    solver = localsolver.upper()
    if solver in ("COBYLA", "BOBYQA"):
        derivative_free = True
        gsolver = "NLOPT_LN_AUGLAG"
        lsolver = f"NLOPT_LN_{solver}"
    elif solver in ("LBFGS", "MMA", "SLSQP"):
        derivative_free = False
        gsolver = "NLOPT_LD_AUGLAG"
        lsolver = f"NLOPT_LD_{solver}"
    else:
        raise ValueError("Only local solvers allowed: BOBYQA, COBYLA, LBFGS, MMA, SLSQP.")
    objective = _bind(fn, kwargs)
    gradient = None if derivative_free else _gradient(objective, gr, kwargs)
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = gsolver
    opts["local_opts"] = {
        "algorithm": lsolver,
        "xtol_rel": localtol,
        "eval_grad_f": None if derivative_free else gradient,
    }
    if derivative_free:
        hin_fn, hin_jac = _inequality(hin, hinjac, deprecated_behavior, kwargs, False)
        heq_fn = None if heq is None else (lambda x: heq(x))
        heq_jac = None
    else:
        hin_fn, hin_jac = _inequality(hin, hinjac, deprecated_behavior, kwargs, True)
        heq_fn, heq_jac = _equality(heq, heqjac)
    result = nloptr(
        x0, objective, eval_grad_f=gradient, lb=lower, ub=upper,
        eval_g_ineq=hin_fn, eval_jac_g_ineq=hin_jac,
        eval_g_eq=heq_fn, eval_jac_g_eq=heq_jac, opts=opts,
    )
    return _box(result, nl_info, global_solver=gsolver, local_solver=lsolver)


def direct(fn, lower, upper, scaled=True, original=False, nl_info=False,
           control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_GN_DIRECT" if scaled else "NLOPT_GN_DIRECT_NOSCAL"
    if original:
        opts["algorithm"] = "NLOPT_GN_ORIG_DIRECT"
    x0 = (np.asarray(lower, dtype=float) + np.asarray(upper, dtype=float)) / 2.0
    result = nloptr(x0, _bind(fn, kwargs), lb=lower, ub=upper, opts=opts)
    return _box(result, nl_info)


def directL(fn, lower, upper, randomized=False, original=False, nl_info=False,
            control=None, **kwargs):
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_GN_DIRECT_L_RAND" if randomized else "NLOPT_GN_DIRECT_L"
    if original:
        opts["algorithm"] = "NLOPT_GN_ORIG_DIRECT_L"
    x0 = (np.asarray(lower, dtype=float) + np.asarray(upper, dtype=float)) / 2.0
    result = nloptr(x0, _bind(fn, kwargs), lb=lower, ub=upper, opts=opts)
    return _box(result, nl_info)


def stogo(x0, fn, gr=None, lower=None, upper=None, maxeval=10000, xtol_rel=1e-6,
          randomized=False, nl_info=False, **kwargs):
    opts = {
        "maxeval": maxeval,
        "xtol_rel": xtol_rel,
        "algorithm": "NLOPT_GD_STOGO_RAND" if randomized else "NLOPT_GD_STOGO",
    }
    objective = _bind(fn, kwargs)
    result = nloptr(
        x0, objective, eval_grad_f=_gradient(objective, gr, kwargs),
        lb=lower, ub=upper, opts=opts,
    )
    return _box(result, nl_info)


def isres(x0, fn, lower, upper, hin=None, heq=None, maxeval=10000,
          pop_size=None, xtol_rel=1e-6, nl_info=False,
          deprecated_behavior=True, **kwargs):
    point = np.asarray(x0, dtype=float).reshape(-1)
    if pop_size is None:
        pop_size = 20 * (len(point) + 1)
    opts = {
        "maxeval": maxeval,
        "xtol_rel": xtol_rel,
        "population": pop_size,
        "algorithm": "NLOPT_GN_ISRES",
    }
    hin_fn, _jac = _inequality(hin, None, deprecated_behavior, kwargs, False)
    heq_fn = None if heq is None else (lambda x: heq(x))
    result = nloptr(
        x0, _bind(fn, kwargs), lb=lower, ub=upper,
        eval_g_ineq=hin_fn, eval_g_eq=heq_fn, opts=opts,
    )
    return _box(result, nl_info)


def crs2lm(x0, fn, lower, upper, maxeval=10000, pop_size=None, ranseed=None,
           xtol_rel=1e-6, nl_info=False, **kwargs):
    point = np.asarray(x0, dtype=float).reshape(-1)
    if pop_size is None:
        pop_size = 10 * (len(point) + 1)
    opts = {
        "maxeval": maxeval,
        "xtol_rel": xtol_rel,
        "population": pop_size,
        "algorithm": "NLOPT_GN_CRS2_LM",
    }
    if ranseed is not None:
        opts["ranseed"] = int(ranseed)
    result = nloptr(x0, _bind(fn, kwargs), lb=lower, ub=upper, opts=opts)
    return _box(result, nl_info)


def mlsl(x0, fn, gr=None, lower=None, upper=None, local_method="LBFGS",
         low_discrepancy=True, nl_info=False, control=None, **kwargs):
    local_opts = {"algorithm": "NLOPT_LD_LBFGS", "xtol_rel": 1e-4}
    opts = nl_opts({} if control is None else control)
    opts["algorithm"] = "NLOPT_GD_MLSL_LDS" if low_discrepancy else "NLOPT_GD_MLSL"
    opts["local_opts"] = local_opts
    objective = _bind(fn, kwargs)
    if local_method == "LBFGS":
        gradient = _gradient(objective, gr, kwargs)
    else:
        warnings.warn(
            "Only gradient-based LBFGS available as local method. "
            "To use another method please use the nloptr interface."
        )
        gradient = None
    result = nloptr(
        x0, objective, eval_grad_f=gradient, lb=lower, ub=upper, opts=opts,
    )
    return _box(result, nl_info)
