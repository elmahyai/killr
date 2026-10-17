"""Stiff/nonstiff ODE integrator with root finding (deSolve ``lsodar``)."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

from deSolve.rk4 import (
    DeSolveMatrix,
    State,
    _as_times,
    _as_y,
    _call_model,
    _derivative_error,
    _globals_of,
    _lengthvar,
    _reject_compiled,
    _split_return,
    _unlist_names,
    _unpack_model,
    _WARN_EVENTS,
    _WARN_LAGS,
)

try:
    from lsodar import integrate_lsodar
except ImportError:  # pragma: no cover
    integrate_lsodar = None

_ISTATE_IN = (0, *range(11, 23))
_ISTATE_OUT = tuple(range(13))


def _lsodar_kernel():
    if integrate_lsodar is not None:
        return integrate_lsodar
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "lsodar"))
    from lsodar import integrate_lsodar as _integrate_lsodar

    return _integrate_lsodar


def _check_input(y, times, func, rtol, atol, jacfunc, tcrit, hmin, hmax, hini, dllname):
    if not isinstance(y, (dict, State, list, tuple, np.ndarray)):
        raise ValueError("`y' must be numeric")
    values, _ = _as_y(y)
    n = len(values)
    if times is not None:
        _as_times(times)
    if not callable(func) and not isinstance(func, str):
        raise ValueError("`func' must be a function or character vector")
    if isinstance(func, str) and (dllname is None or not isinstance(dllname, str)):
        raise ValueError(
            "specify the name of the dll or shared library where func can be found (without extension)"
        )
    rtol = np.asarray(rtol, dtype=np.float64)
    atol = np.asarray(atol, dtype=np.float64)
    if rtol.ndim == 0:
        rtol = rtol.reshape(1)
    if atol.ndim == 0:
        atol = atol.reshape(1)
    if len(atol) > 1 and len(atol) != n:
        raise ValueError("`atol' must either be a scalar, or as long as `y'")
    if len(rtol) > 1 and len(rtol) != n:
        raise ValueError("`rtol' must either be a scalar, or as long as `y'")
    if tcrit is not None and not np.isscalar(tcrit):
        raise ValueError("`tcrit' must be numeric")
    if jacfunc is not None and not (callable(jacfunc) or isinstance(jacfunc, str)):
        raise ValueError("jacfunc  must be a function or character vector")
    if not np.isscalar(hmin):
        raise ValueError("`hmin' must be numeric")
    if float(hmin) < 0:
        raise ValueError("`hmin' must be a non-negative value")
    if hmax is None:
        if times is None:
            hmax = 0.0
        else:
            grid = _as_times(times)
            hmax = float(np.max(np.abs(np.diff(grid)))) if len(grid) > 1 else 0.0
    if not np.isscalar(hmax):
        raise ValueError("`hmax' must be numeric")
    if float(hmax) < 0:
        raise ValueError("`hmax' must be a non-negative value")
    if np.isinf(hmax):
        hmax = 0.0
    if hini is not None and float(hini) < 0:
        raise ValueError("`hini' must be a non-negative value")
    return float(hmax)


def _check_func(func2, times, y, ynames, names):
    state = State(y, names) if ynames and names is not None else y
    returned = _split_return(func2(times[0], state))
    parents, components = returned
    got = len(components[0][0])
    neq = len(y)
    if got != neq:
        _derivative_error(got, neq)
    nglobal = int(sum(len(data) for data, _inner, _shape in components[1:]))
    lengthvar, _ = _lengthvar(components, parents)
    extra_parents = None if parents is None else parents[1:]
    colnames = _unlist_names(components[1:], extra_parents)
    nmtot = {
        "colnames": colnames,
        "lengthvar": lengthvar,
        "dimvar": None if len(components) >= nglobal + 1 else None,
    }
    return nglobal, nmtot, components


def _set_istate(raw: list[int]) -> list:
    out = [None] * 21
    for iout, iin in zip(_ISTATE_OUT, _ISTATE_IN):
        out[iout] = raw[iin] if iin < len(raw) else None
    return out


def _save_out(table, y_names, n, nglobal, nmtot, istate_raw, rstate, iroot=None):
    istate = _set_istate(istate_raw)
    state_names = [str(i + 1) for i in range(n)] if y_names is None else list(y_names)
    global_names = (
        [str(n + 1 + i) for i in range(nglobal)]
        if nmtot.get("colnames") is None
        else list(nmtot["colnames"])
    )
    colnames = ["time", *state_names, *global_names]
    lengthvar = nmtot.get("lengthvar")
    if lengthvar and lengthvar[0] is None:
        lengthvar = [n, *lengthvar[1:]]
    result = DeSolveMatrix(table, colnames, istate, lengthvar, None, nmtot.get("dimvar"))
    result.type = "lsodar"
    result.rstate = list(rstate)
    if iroot is not None:
        result.iroot = list(iroot)
    return result


def lsodar(
    y,
    times,
    func,
    parms,
    rtol=1e-6,
    atol=1e-6,
    jacfunc=None,
    jactype="fullint",
    rootfunc=None,
    verbose=False,
    nroot=0,
    tcrit=None,
    hmin=0,
    hmax=None,
    hini=0,
    ynames=True,
    maxordn=12,
    maxords=5,
    bandup=None,
    banddown=None,
    maxsteps=5000,
    dllname=None,
    initfunc=None,
    initpar=None,
    rpar=None,
    ipar=None,
    nout=0,
    outnames=None,
    forcings=None,
    initforc=None,
    fcontrol=None,
    events=None,
    lags=None,
    **kwargs,
):
    """Integrate ``y' = func(t, y, parms)`` with LSODAR (stiff/nonstiff switch and roots)."""
    kernel = _lsodar_kernel()

    if isinstance(func, dict):
        if jacfunc is not None and "jacfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains jacfunc, argument 'jacfunc' should be NULL"
            )
        if rootfunc is not None and "rootfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains rootfunc, argument 'rootfunc' should be NULL"
            )
        if initfunc is not None and "initfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains initfunc, argument 'initfunc' should be NULL"
            )
        if dllname is not None and "dllname" in func:
            raise ValueError(
                "If 'func' is a list that contains dllname, argument 'dllname' should be NULL"
            )
        if initforc is not None and "initforc" in func:
            raise ValueError(
                "If 'func' is a list that contains initforc, argument 'initforc' should be NULL"
            )
        if events is not None and isinstance(events, dict) and events.get("func") and "eventfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains eventfunc, argument 'events$func' should be NULL"
            )
        if "eventfunc" in func:
            if events is None:
                events = {"func": func["eventfunc"]}
            else:
                events = {**events, "func": func["eventfunc"]}
        if func.get("jacfunc") is not None:
            jacfunc = func["jacfunc"]
        if func.get("rootfunc") is not None:
            rootfunc = func["rootfunc"]
        if func.get("initfunc") is not None:
            initfunc = func["initfunc"]
        if func.get("dllname") is not None:
            dllname = func["dllname"]
        if func.get("initforc") is not None:
            initforc = func["initforc"]
        func = func.get("func")

    if initfunc is None:
        initfunc = dllname
    if initpar is None:
        initpar = parms

    func, initfunc, dllname, initforc = _unpack_model(func, initfunc, dllname, initforc)
    _reject_compiled(func, dllname)

    if events is not None or lags is not None:
        if events is not None:
            warnings.warn(_WARN_EVENTS, stacklevel=2)
        if lags is not None:
            warnings.warn(_WARN_LAGS, stacklevel=2)

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
        events,
        lags,
    )

    values, names = _as_y(y)
    grid = _as_times(times)
    if len(grid) == 0:
        raise ValueError("`times' must be NULL or numeric")
    n = len(values)

    hmax = _check_input(y, times, func, rtol, atol, jacfunc, tcrit, hmin, hmax, hini, dllname)

    if not np.issubdtype(np.asarray(maxordn).dtype, np.number):
        raise ValueError("`maxordn' must be numeric")
    maxordn = int(maxordn)
    if maxordn < 1 or maxordn > 12:
        raise ValueError("`maxord' must be >1 and <=12")
    if not np.issubdtype(np.asarray(maxords).dtype, np.number):
        raise ValueError("`maxords' must be numeric")
    maxords = int(maxords)
    if maxords < 1 or maxords > 5:
        raise ValueError("`maxords' must be >1 and <=5")

    if jactype == "fullint":
        jt = 2
    elif jactype == "fullusr":
        jt = 1
    elif jactype == "bandusr":
        jt = 4
    elif jactype == "bandint":
        jt = 5
    else:
        raise ValueError("'jactype' must be one of 'fullint', 'fullusr', 'bandusr' or 'bandint'")

    if jt in (4, 5) and bandup is None:
        raise ValueError("'bandup' must be specified if banded Jacobian")
    if jt in (4, 5) and banddown is None:
        raise ValueError("'banddown' must be specified if banded Jacobian")
    if banddown is None:
        banddown = 1
    if bandup is None:
        bandup = 1
    if jt in (1, 4) and jacfunc is None:
        raise ValueError("'jacfunc' NOT specified; either specify 'jacfunc' or change 'jactype'")

    def func2(time, state):
        return _call_model(func, time, state, names, ynames, parms, kwargs)

    nglobal, nmtot, _components = _check_func(func2, grid, values, ynames, names)

    state0 = State(values, names) if ynames and names is not None else values
    if rootfunc is not None:
        tmp2 = rootfunc(grid[0], state0, parms, **kwargs)
        if isinstance(tmp2, dict):
            tmp2 = next(iter(tmp2.values()))
        tmp2 = np.asarray(tmp2, dtype=np.float64).reshape(-1)
        if tmp2.ndim != 1:
            raise ValueError("root function 'rootfunc' must return a vector\n")
        nroot = len(tmp2)
    else:
        nroot = 0

    jac_py = None
    if jt in (1, 4):
        if jacfunc is None:
            raise ValueError("Jacobian function must return a matrix\n")

        def jac_wrapped(time, state):
            mat = jacfunc(float(time), state, parms, **kwargs)
            if jt == 4 and banddown > 0:
                erow = np.zeros((banddown, n), dtype=np.float64)
                return np.vstack([np.asarray(mat, dtype=np.float64), erow])
            return np.asarray(mat, dtype=np.float64)

        jac_test = jac_wrapped(grid[0], state0)
        if jac_test.ndim != 2:
            raise ValueError("Jacobian function must return a matrix\n")
        dd = jac_test.shape
        if (jt == 4 and dd != (bandup + banddown + 1, n)) or (jt == 1 and dd != (n, n)):
            raise ValueError("Jacobian dimension not ok")
        jac_py = jac_wrapped

    rtol_scalar = float(np.asarray(rtol, dtype=np.float64).reshape(-1)[0])
    atol_scalar = float(np.asarray(atol, dtype=np.float64).reshape(-1)[0])

    def deriv_for_rust(t, y_arr):
        state = y_arr if not ynames or names is None else State(np.asarray(y_arr), names)
        out = _split_return(_call_model(func, float(t), state, names, ynames, parms, kwargs))[1][0][0]
        return list(out)

    root_py = None
    if rootfunc is not None and nroot > 0:

        def root_for_rust(t, y_arr):
            state = y_arr if not ynames or names is None else State(np.asarray(y_arr), names)
            raw = rootfunc(float(t), state, parms, **kwargs)
            if isinstance(raw, dict):
                raw = next(iter(raw.values()))
            return list(np.asarray(raw, dtype=np.float64).reshape(-1))

        root_py = root_for_rust

    table, istate_raw, rstate, iroot = kernel(
        np.asarray(values, dtype=np.float64),
        np.asarray(grid, dtype=np.float64),
        deriv_for_rust,
        jt=jt,
        rtol=rtol_scalar,
        atol=atol_scalar,
        maxordn=maxordn,
        maxords=maxords,
        maxsteps=int(maxsteps),
        banddown=int(banddown),
        bandup=int(bandup),
        hini=float(hini or 0.0),
        hmax=float(hmax),
        hmin=float(hmin),
        tcrit=float(tcrit) if tcrit is not None else None,
        jacfunc=jac_py,
        rootfunc=root_py,
        nroot=int(nroot),
    )

    table = np.asarray(table, dtype=np.float64)
    table[0, 0] = grid[0]

    if nglobal > 0:
        for row in range(table.shape[0]):
            t = table[row, 0]
            st = table[row, 1 : 1 + n]
            state = State(st, names) if ynames and names else st
            comps = _split_return(_call_model(func, t, state, names, ynames, parms, kwargs))[1]
            table[row, 1 + n :] = _globals_of(comps)

    result = _save_out(table, names, n, nglobal, nmtot, istate_raw, rstate, iroot)
    if verbose:
        sys.stdout.write(f"lsodar completed with istate[0] = {istate_raw[0]}\n")
    return result
