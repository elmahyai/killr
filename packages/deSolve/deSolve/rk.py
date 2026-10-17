"""General Runge-Kutta integrator (deSolve ``rk``)."""

from __future__ import annotations

import sys
import warnings

import numpy as np
import rksolv

from deSolve.rk4 import (
    DeSolveMatrix,
    _ISTATE_TEXT,
    _as_times,
    _as_y,
    _call_model,
    _derivative_error,
    _globals_of,
    _lengthvar,
    _dimvar,
    _numeric_vector,
    _reject_compiled,
    _split_return,
    _unpack_model,
    _unlist_names,
)
from deSolve.rkMethod import RkMethod, rkMethod
from deSolve.timestep import _advance_timestep, _reset_timesteps

_MISSING = object()
_DBL_MAX = sys.float_info.max

_WARN_JAC = (
    "Euler and Runge-Kutta solvers make no use of a Jacobian,\n"
    "  ('jacfunc', 'jactype', 'mf', 'bandup' and 'banddown' are ignored).\n"
)
_WARN_LAGS = (
    "lags are not yet implemented for Euler and Runge-Kutta solvers,\n"
    "  (argument 'lags' is ignored).\n"
)


def _warn_rk_dots(kwargs):
    names = set(kwargs)
    if names.intersection(("jacfunc", "jactype", "mf", "bandup", "banddown")):
        warnings.warn(_WARN_JAC, stacklevel=3)
    if "lags" in names:
        warnings.warn(_WARN_LAGS, stacklevel=3)


def _check_input(y, times, func, rtol, atol, tcrit, hmin, hmax, hini, dllname):
    values, _names = _as_y(y)
    n = len(values)
    if times is not None:
        _as_times(times)
    if not callable(func) and not isinstance(func, str):
        raise ValueError("`func' must be a function or character vector")
    if isinstance(func, str) and (dllname is None or not isinstance(dllname, str)):
        raise ValueError(
            "specify the name of the dll or shared library where func can be found (without extension)"
        )
    _numeric_vector(rtol, "`rtol' must be numeric")
    _numeric_vector(atol, "`atol' must be numeric")
    if tcrit is not None:
        _numeric_vector(tcrit, "`tcrit' must be numeric")
    if not isinstance(hmin, (int, float, np.floating)):
        raise ValueError("`hmin' must be numeric")
    if hmin < 0:
        raise ValueError("`hmin' must be a non-negative value")
    if hmax is _MISSING or hmax is None:
        grid = _as_times(times)
        hmax = float(np.max(np.abs(np.diff(grid)))) if len(grid) > 1 else 0.0
    if not isinstance(hmax, (int, float, np.floating)):
        raise ValueError("`hmax' must be numeric")
    if hmax < 0:
        raise ValueError("`hmax' must be a non-negative value")
    if hmax == float("inf"):
        hmax = 0.0
    if hini is not None and hini < 0:
        raise ValueError("`hini' must be a non-negative value")
    atol_arr = np.ravel(np.asarray(atol, dtype=np.float64))
    rtol_arr = np.ravel(np.asarray(rtol, dtype=np.float64))
    if len(atol_arr) > 1 and len(atol_arr) != n:
        raise ValueError("`atol' must either be a scalar, or as long as `y'")
    if len(rtol_arr) > 1 and len(rtol_arr) != n:
        raise ValueError("`rtol' must either be a scalar, or as long as `y'")
    return float(hmax)


def _set_istate_rk(raw: np.ndarray) -> list:
    """Map C ``istate`` to the 21-element R vector (``saveOutrk`` / ``setIstate``)."""
    out = [None] * 21
    iin = (0, 11, 12, 13, 14)
    iout = (0, 1, 2, 12, 17)
    for src, dst in zip(iin, iout):
        out[dst] = int(raw[src])
    return out


def _method_arrays(method: RkMethod):
    stage = int(method["stage"])
    a = np.asarray(method["A"], dtype=np.float64)
    if a.ndim == 2:
        a_flat = np.ravel(a, order="F")
    else:
        a_flat = np.ravel(a, order="F")
    b1 = np.ravel(np.asarray(method["b1"], dtype=np.float64), order="F")
    b2_val = method.get("b2")
    b2 = None if b2_val is None else np.ravel(np.asarray(b2_val, dtype=np.float64), order="F")
    c = np.ravel(np.asarray(method["c"], dtype=np.float64), order="F")
    d_val = method.get("d")
    d = None if d_val is None else np.ravel(np.asarray(d_val, dtype=np.float64), order="F")
    fsal = int(method.get("FSAL") or 0)
    qerr = int(method["Qerr"])
    densetype = method.get("densetype")
    densetype = 0 if densetype is None else int(densetype)
    nknots = method.get("nknots")
    nknots = 0 if nknots is None else int(nknots)
    beta = method.get("beta")
    beta = 0.0 if beta is None else float(beta)
    alpha_val = method.get("alpha")
    alpha = float(alpha_val) if alpha_val is not None else (1.0 / qerr - 0.75 * beta)
    varstep = bool(method.get("varstep"))
    implicit = method.get("implicit")
    implicit = 0 if implicit is None else int(implicit)
    return {
        "stage": stage,
        "a": a_flat,
        "b1": b1,
        "b2": b2,
        "c": c,
        "d": d,
        "fsal": fsal,
        "qerr": qerr,
        "densetype": densetype,
        "nknots": nknots,
        "alpha": alpha,
        "beta": beta,
        "varstep": varstep,
        "implicit": implicit,
    }


def _print_diagnostics(istate):
    sys.stdout.write("\n--------------------\n")
    sys.stdout.write("rk return code")
    sys.stdout.write("\n--------------------\n")
    sys.stdout.write(f"\n  return code (idid) =  {istate[0]} \n")
    if istate[0] == 0:
        sys.stdout.write("  Integration was successful.\n")
    sys.stdout.write("\n--------------------\n")
    sys.stdout.write("INTEGER values\n")
    sys.stdout.write("--------------------\n")
    parts = []
    for index, value in enumerate(istate):
        if value is None:
            continue
        parts.append(f"{index + 1:2d} {_ISTATE_TEXT[index]} {value} \n")
    sys.stdout.write("\n " + " ".join(parts) + " \n")


def rk(
    y,
    times,
    func,
    parms,
    rtol=1e-6,
    atol=1e-6,
    verbose=False,
    tcrit=None,
    hmin=0.0,
    hmax=_MISSING,
    hini=_MISSING,
    ynames=True,
    method=_MISSING,
    maxsteps=5000,
    dllname=None,
    initfunc=_MISSING,
    initpar=_MISSING,
    rpar=None,
    ipar=None,
    nout=0,
    outnames=None,
    forcings=None,
    initforc=None,
    fcontrol=None,
    events=None,
    **kwargs,
):
    """Integrate ODEs with an explicit or implicit Runge-Kutta method table."""
    if initfunc is _MISSING:
        initfunc = dllname
    if initpar is _MISSING:
        initpar = parms
    if method is _MISSING:
        method = rkMethod("rk45dp7")
    elif isinstance(method, str):
        method = rkMethod(method)
    elif not isinstance(method, RkMethod):
        raise TypeError("method must be a character string or rkMethod object")

    func, initfunc, dllname, initforc = _unpack_model(func, initfunc, dllname, initforc)
    _warn_rk_dots(kwargs)

    varstep = bool(method["varstep"])
    if not varstep and (hmin != 0 or (hmax is not _MISSING and hmax is not None)):
        sys.stdout.write(
            "'hmin' and 'hmax' are ignored (fixed step Runge-Kutta method).\n"
        )

    if hini is _MISSING:
        hini_arg = None
    else:
        hini_arg = float(hini)

    hmax_val = _check_input(y, times, func, rtol, atol, tcrit, hmin, hmax, hini_arg, dllname)
    if hmax_val == 0:
        hmax_val = _DBL_MAX

    if maxsteps < 0:
        raise ValueError("maxsteps must be positive")
    if not np.isfinite(maxsteps):
        maxsteps = 2**31 - 2

    if tcrit is None:
        tcrit_val = float(np.max(_as_times(times)))
    else:
        tcrit_val = float(np.ravel(np.asarray(tcrit, dtype=np.float64))[0])

    spec = _method_arrays(method)
    if spec["implicit"]:
        raise ValueError("implicit Runge-Kutta methods are not supported in this port")

    if events is not None:
        warnings.warn(
            "events are not supported by this rk port; argument 'events' is ignored.",
            stacklevel=2,
        )

    _reject_compiled(func, dllname)
    del (
        initfunc,
        initpar,
        initforc,
        rpar,
        ipar,
        nout,
        outnames,
        forcings,
        fcontrol,
    )

    values, names = _as_y(y)
    grid = _as_times(times)
    if len(grid) == 0:
        raise ValueError("`times' must be NULL or numeric")
    neq = len(values)

    parents, components = _split_return(
        _call_model(func, grid[0], values, names, ynames, parms, kwargs)
    )
    got = len(components[0][0])
    if got != neq:
        _derivative_error(got, neq)
    lengthvar, lengthvar_names = _lengthvar(components, parents)
    extra_parents = None if parents is None else parents[1:]
    global_names = _unlist_names(components[1:], extra_parents)
    nglobal = int(sum(len(data) for data, _inner, _shape in components[1:]))
    if global_names is None:
        global_names = [str(neq + 1 + index) for index in range(nglobal)]
    dimvar = _dimvar(components, nglobal)

    if neq % len(np.ravel(atol)):
        warnings.warn("length of atol does not match number of states", stacklevel=2)
    if neq % len(np.ravel(rtol)):
        warnings.warn("length of rtol does not match number of states", stacklevel=2)
    atol_vec = np.resize(np.asarray(atol, dtype=np.float64), neq)
    rtol_vec = np.resize(np.asarray(rtol, dtype=np.float64), neq)

    if hini_arg is None:
        hini_val = hmax_val if varstep else 0.0
    else:
        hini_val = hini_arg

    nsteps = min(
        2**31 - 2,
        max(int(maxsteps) * len(grid), int(np.max(np.diff(grid)) / hini_val + 1) if hini_val else len(grid)),
    )

    def deriv_fn(time, state):
        returned = _split_return(
            _call_model(func, time, state, names, ynames, parms, kwargs)
        )[1]
        derivative = returned[0][0]
        if len(derivative) != neq:
            _derivative_error(len(derivative), neq)
        return np.asarray(derivative, dtype=np.float64)

    _reset_timesteps()
    data, istate_raw, ts_pair = rksolv.rk_integrate(
        deriv_fn,
        values,
        grid,
        varstep=varstep,
        stage=spec["stage"],
        fsal=spec["fsal"],
        qerr=spec["qerr"],
        a=spec["a"],
        b1=spec["b1"],
        b2=spec["b2"],
        c=spec["c"],
        d=spec["d"],
        densetype=spec["densetype"],
        nknots=spec["nknots"],
        alpha=spec["alpha"],
        beta=spec["beta"],
        atol=atol_vec,
        rtol=rtol_vec,
        tcrit=tcrit_val,
        hmin=float(hmin),
        hmax=float(hmax_val),
        hini=float(hini_val),
        maxsteps=int(nsteps),
    )

    table = np.asarray(data, dtype=np.float64)
    if nglobal:
        extra = np.empty((table.shape[0], nglobal), dtype=np.float64)
        for row in range(table.shape[0]):
            returned = _split_return(
                _call_model(
                    func,
                    table[row, 0],
                    table[row, 1 : 1 + neq],
                    names,
                    ynames,
                    parms,
                    kwargs,
                )
            )[1]
            extra[row] = _globals_of(returned)
        table = np.hstack([table, extra])

    istate = _set_istate_rk(np.asarray(istate_raw, dtype=np.int32))
    state_names = [str(index + 1) for index in range(neq)] if names is None else list(names)
    result = DeSolveMatrix(
        table,
        ["time", *state_names, *global_names],
        istate,
        lengthvar,
        lengthvar_names,
        dimvar,
    )
    if verbose:
        _print_diagnostics(istate)
    _reset_timesteps()
    if ts_pair[1]:
        _advance_timestep(ts_pair[1])
    return result
