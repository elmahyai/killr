"""Delay differential equation driver (deSolve ``dede``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from deSolve.lagvalue import init_hist, update_hist, update_hist_ini
from deSolve.lsodar import _check_func, _check_input, _save_out
from deSolve.rk4 import (
    State,
    _as_times,
    _as_y,
    _call_model,
    _globals_of,
    _reject_compiled,
    _split_return,
    _unpack_model,
)

try:
    from dede import integrate_dlsoda_lags
except ImportError:  # pragma: no cover
    integrate_dlsoda_lags = None

_METHODS = (
    "lsoda",
    "lsode",
    "lsodes",
    "lsodar",
    "vode",
    "daspk",
    "bdf",
    "adams",
    "impAdams",
    "radau",
)


def _dede_kernel():
    if integrate_dlsoda_lags is not None:
        return integrate_dlsoda_lags
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "dede"))
    from dede import integrate_dlsoda_lags as _integrate_dlsoda_lags

    return _integrate_dlsoda_lags


def _prepare_lags(control):
    if control is None:
        control = {}
    else:
        control = dict(control)
    control.setdefault("mxhist", int(1e4))
    if control["mxhist"] < 1:
        control["mxhist"] = int(1e4)
    control["mxhist"] = int(control["mxhist"])
    control.setdefault("interpol", 1)
    control["interpol"] = int(control["interpol"])
    control["islag"] = 1
    control["isfun"] = 0
    return control


def _lsoda_dede(
    y,
    times,
    func,
    parms,
    lags,
    rtol=1e-6,
    atol=1e-6,
    jacfunc=None,
    jactype="fullint",
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
    verbose=False,
    **kwargs,
):
    del verbose
    func, _, dllname, _ = _unpack_model(func, None, dllname, None)
    _reject_compiled(func, dllname)

    values, names = _as_y(y)
    grid = _as_times(times)
    if len(grid) == 0:
        raise ValueError("`times' must be NULL or numeric")
    n = len(values)

    hmax = _check_input(y, times, func, rtol, atol, jacfunc, tcrit, hmin, hmax, hini, dllname)

    if jactype == "fullint":
        jt = 2
    elif jactype == "fullusr":
        jt = 1
    elif jactype == "bandusr":
        jt = 4
    elif jactype == "bandint":
        jt = 5
    else:
        raise ValueError(
            "'jactype' must be one of 'fullint', 'fullusr', 'bandusr' or 'bandint'"
        )
    if jt in (4, 5) and bandup is None:
        raise ValueError("'bandup' must be specified if banded Jacobian")
    if jt in (4, 5) and banddown is None:
        raise ValueError("'banddown' must be specified if banded Jacobian")
    if banddown is None:
        banddown = 1
    if bandup is None:
        bandup = 1
    if jt in (1, 4) and jacfunc is None:
        raise ValueError(
            "'jacfunc' NOT specified; either specify 'jacfunc' or change 'jactype'"
        )

    def func2(time, state):
        return _call_model(func, time, state, names, ynames, parms, kwargs)

    nglobal, nmtot, components = _check_func(func2, grid, values, ynames, names)
    del components

    state0 = State(values, names) if ynames and names is not None else values
    if jt in (1, 4):
        jac_test = np.asarray(jacfunc(float(grid[0]), state0, parms, **kwargs), dtype=np.float64)
        if jac_test.ndim != 2:
            raise ValueError("Jacobian function must return a matrix\n")
        dd = jac_test.shape
        if (jt == 4 and dd != (bandup + banddown + banddown + 1, n)) or (
            jt == 1 and dd != (n, n)
        ):
            raise ValueError("Jacobian dimension not ok")

        def jac_wrapped(time, state):
            return np.asarray(jacfunc(float(time), state, parms, **kwargs), dtype=np.float64)

        jac_py = jac_wrapped
    else:
        jac_py = None

    rtol_scalar = float(np.asarray(rtol, dtype=np.float64).reshape(-1)[0])
    atol_scalar = float(np.asarray(atol, dtype=np.float64).reshape(-1)[0])

    init_hist(int(lags["mxhist"]), n)

    def deriv_for_rust(t, y_arr):
        state = y_arr if not ynames or names is None else State(np.asarray(y_arr), names)
        out = _split_return(_call_model(func, float(t), state, names, ynames, parms, kwargs))[1][0][0]
        return list(out)

    t0 = float(grid[0])
    dy0 = np.asarray(deriv_for_rust(t0, values), dtype=np.float64)
    update_hist_ini(t0, np.asarray(values, dtype=np.float64), dy0)

    def post_step(t, y_arr):
        dy = np.asarray(deriv_for_rust(float(t), y_arr), dtype=np.float64)
        update_hist(float(t), np.asarray(y_arr, dtype=np.float64), dy)

    kernel = _dede_kernel()
    table, istate_raw, rstate = kernel(
        np.asarray(values, dtype=np.float64),
        np.asarray(grid, dtype=np.float64),
        deriv_for_rust,
        post_step,
        jt=jt,
        rtol=rtol_scalar,
        atol=atol_scalar,
        maxordn=int(maxordn),
        maxords=int(maxords),
        maxsteps=int(maxsteps),
        banddown=int(banddown),
        bandup=int(bandup),
        hini=float(hini or 0.0),
        hmax=float(hmax),
        hmin=float(hmin),
        tcrit=float(tcrit) if tcrit is not None else None,
        jacfunc=jac_py,
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

    result = _save_out(table, names, n, nglobal, nmtot, istate_raw, rstate)
    result.type = "lsoda"
    return result


def dede(
    y,
    times,
    func=None,
    parms=None,
    method="lsoda",
    control=None,
    **kwargs,
):
    """Integrate a delay differential equation system (R ``dede``)."""
    if control is None:
        control = {"mxhist": int(1e4)}
    lags = _prepare_lags(control)

    if method is None:
        method = "lsoda"
    if callable(method):
        return method(y, times, func, parms, lags=lags, **kwargs)

    if np.iscomplexobj(y):
        raise ValueError("cannot run dede with complex y")

    if isinstance(method, str):
        method = method.lower()
    if method not in _METHODS:
        raise ValueError(
            f"'arg' should be one of {', '.join(repr(m) for m in _METHODS)}"
        )

    common = dict(
        y=y,
        times=times,
        func=func,
        parms=parms,
        lags=lags,
        **kwargs,
    )

    if method == "lsoda":
        return _lsoda_dede(**common)
    if method == "vode":
        from deSolve.vode import vode

        return vode(**common)
    if method == "lsode":
        from deSolve.lsode import lsode

        return lsode(**common)
    if method == "lsodes":
        from deSolve.lsodes import lsodes

        return lsodes(**common)
    if method == "lsodar":
        from deSolve.lsodar import lsodar

        return lsodar(**common)
    if method == "daspk":
        from deSolve.daspk import daspk

        return daspk(**common)
    if method == "radau":
        from deSolve.radau import radau

        return radau(**common)
    if method == "bdf":
        from deSolve.lsode import lsode

        return lsode(**common, mf=22)
    if method == "adams":
        from deSolve.lsode import lsode

        return lsode(**common, mf=10)
    if method == "impAdams":
        from deSolve.lsode import lsode

        return lsode(**common, mf=12)

    raise ValueError(f"unsupported method {method!r}")
