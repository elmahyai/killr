"""Implicit Runge-Kutta RADAU IIA (deSolve ``radau`` / RADAU5)."""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import numpy as np

from deSolve.rk4 import (
    DeSolveMatrix,
    State,
    _ISTATE_TEXT,
    _as_times,
    _as_y,
    _call_model,
    _derivative_error,
    _dimvar,
    _globals_of,
    _lengthvar,
    _reject_compiled,
    _split_return,
    _unpack_model,
    _unlist_names,
)

_MISSING = object()
_DOUBLE_NEG_EPS = np.nextafter(0.0, -1.0)

_WARN_EVENTS = (
    "events, roots, lags, and forcings are not yet implemented for radau;\n"
    "  those arguments are ignored.\n"
)


def _radau_kernel():
    try:
        from radau5 import integrate_radau as _integrate_radau
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "radau5"))
        from radau5 import integrate_radau as _integrate_radau
    return _integrate_radau


def _check_input(y, times, func, rtol, atol, jacfunc, hmax, hini, dllname, jacname="jacfunc"):
    if not isinstance(func, str):
        _reject_compiled(func, dllname)
    values, _names = _as_y(y)
    n = len(values)
    grid = _as_times(times) if times is not None else np.array([0.0, 1e8], dtype=np.float64)
    if not np.issubdtype(np.asarray(rtol).dtype, np.number):
        raise ValueError("`rtol' must be numeric")
    if not np.issubdtype(np.asarray(atol).dtype, np.number):
        raise ValueError("`atol' must be numeric")
    if jacfunc is not None and not callable(jacfunc):
        raise ValueError(f"{jacname} must be a function or character vector")
    atol_arr = np.asarray(atol, dtype=np.float64).reshape(-1)
    rtol_arr = np.asarray(rtol, dtype=np.float64).reshape(-1)
    if atol_arr.size > 1 and atol_arr.size != n:
        raise ValueError("`atol' must either be a scalar, or as long as `y'")
    if rtol_arr.size > 1 and rtol_arr.size != n:
        raise ValueError("`rtol' must either be a scalar, or as long as `y'")
    if hmax is None:
        hmax = float(np.max(np.abs(np.diff(grid)))) if len(grid) > 1 else 0.0
    hmax = float(hmax)
    if hmax < 0:
        raise ValueError("`hmax' must be a non-negative value")
    if hmax == np.inf:
        hmax = 0.0
    if hini is not None and float(hini) < 0:
        raise ValueError("`hini' must be a non-negative value")
    return hmax


def _set_istate(raw7):
    """Map RADAU5 ``istate`` like ``setIstate(..., iin=1:7, iout=c(1,3,4,2,13,13,10))``."""
    iout = [1, 3, 4, 2, 13, 13, 10]
    istate = [None] * 21
    for src, dst in zip(raw7, iout, strict=True):
        istate[dst - 1] = int(src)
    return istate


def _print_diagnostics(istate):
    for index, text in enumerate(_ISTATE_TEXT):
        value = istate[index] if index < len(istate) else None
        if value is None:
            continue
        print(f"{text} {value}")


def radau(
    y,
    times,
    func,
    parms,
    nind=None,
    rtol=1e-6,
    atol=1e-6,
    jacfunc=None,
    jactype="fullint",
    mass=_MISSING,
    massup=None,
    massdown=None,
    rootfunc=None,
    verbose=False,
    nroot=0,
    hmax=None,
    hini=0,
    ynames=True,
    bandup=None,
    banddown=None,
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
    lags=None,
    **kwargs,
):
    if initfunc is _MISSING:
        initfunc = dllname
    if initpar is _MISSING:
        initpar = parms

    if isinstance(func, dict):
        if jacfunc is not None and "jacfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains jacfunc, argument 'jacfunc' should be NULL"
            )
        if rootfunc is not None and "rootfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains rootfunc, argument 'rootfunc' should be NULL"
            )
        if initfunc is not None and initfunc is not dllname and "initfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains initfunc, argument 'initfunc' should be NULL"
            )
        jacfunc = func.get("jacfunc", jacfunc)
        rootfunc = func.get("rootfunc", rootfunc)
        initfunc = func.get("initfunc", initfunc)
        func = func.get("func")

    if any(
        item is not None
        for item in (mass if mass is not _MISSING else None, rootfunc, events, lags, forcings)
    ):
        warnings.warn(_WARN_EVENTS, stacklevel=2)
    if mass is not _MISSING and mass is not None:
        raise NotImplementedError("mass matrix DAEs are not yet implemented for radau")
    if isinstance(func, str) or dllname is not None:
        _reject_compiled(func, dllname)

    hmax = _check_input(y, times, func, rtol, atol, jacfunc, hmax, hini, dllname)
    values, names = _as_y(y)
    n = len(values)
    grid = _as_times(times) if times is not None else np.array([0.0, 1e8], dtype=np.float64)
    if len(grid) == 0:
        raise ValueError("`times' must be NULL or numeric")

    if hini is None:
        hini = 0.0
    hini = float(hini)
    if hini <= 0:
        hini = 0.0

    rtol_arr = np.asarray(rtol, dtype=np.float64).reshape(-1)
    atol_arr = np.asarray(atol, dtype=np.float64).reshape(-1)
    if rtol_arr.size != atol_arr.size:
        if rtol_arr.size > atol_arr.size:
            atol_arr = np.resize(atol_arr, n)
        else:
            rtol_arr = np.resize(rtol_arr, n)
    if rtol_arr.size == 1:
        rtol_vec = rtol_arr
        atol_vec = atol_arr
    else:
        rtol_vec = np.resize(rtol_arr, n)
        atol_vec = np.resize(atol_arr, n)

    if nind is None:
        nind3 = [n, 0, 0]
    else:
        nind3 = [int(x) for x in np.asarray(nind, dtype=int).reshape(-1)]
        if len(nind3) != 3:
            raise ValueError("length of `nind' must be =3")
        if sum(nind3) != n:
            raise ValueError("sum of of `nind' must equal n, the number of equations")

    full = True
    if jactype == "fullint":
        ijac = 0
        banddown = n
        bandup = n
    elif jactype == "fullusr":
        ijac = 1
        banddown = n
        bandup = n
    elif jactype == "bandusr":
        ijac = 1
        full = False
        if banddown is None or bandup is None:
            raise ValueError("'bandup' and 'banddown' must be specified if banded Jacobian")
    elif jactype == "bandint":
        ijac = 0
        full = False
        if banddown is None or bandup is None:
            raise ValueError("'bandup' and 'banddown' must be specified if banded Jacobian")
    else:
        raise ValueError("'jactype' must be one of 'fullint', 'fullusr', 'bandusr' or 'bandint'")

    if ijac == 1 and jacfunc is None:
        raise ValueError("'jacfunc' NOT specified; either specify 'jacfunc' or change 'jactype'")

    def func2(time, state):
        return _call_model(func, time, state, names, ynames, parms, kwargs)

    parents, components = _split_return(func2(grid[0], values))
    got = len(components[0][0])
    if got != n:
        _derivative_error(got, n)
    lengthvar, lengthvar_names = _lengthvar(components, parents)
    extra_parents = None if parents is None else parents[1:]
    global_names = _unlist_names(components[1:], extra_parents)
    nglobal = int(sum(len(data) for data, _inner, _shape in components[1:]))
    if global_names is None and nglobal > 0:
        global_names = [str(n + 1 + index) for index in range(nglobal)]
    dimvar = _dimvar(components, nglobal)

    if ijac == 1:
        if ynames and names is not None:
            state0 = State(values, names)
        else:
            state0 = values
        jac_sample = jacfunc(grid[0], state0, parms, **kwargs)
        jac_arr = np.asarray(jac_sample, dtype=np.float64)
        if jac_arr.ndim != 2:
            raise ValueError("Jacobian function 'jacfunc' must return a matrix\n")
        dd = jac_arr.shape
        if (not full and dd != (bandup + banddown + 1, n)) or (full and dd != (n, n)):
            raise ValueError("Jacobian dimension not ok")

    def py_deriv(time, state_vec):
        if ynames and names is not None:
            state = State(np.asarray(state_vec, dtype=np.float64), names)
        else:
            state = np.asarray(state_vec, dtype=np.float64)
        deriv = _split_return(func2(time, state))[1][0][0]
        if len(deriv) != n:
            _derivative_error(len(deriv), n)
        return [float(x) for x in deriv]

    py_jac = None
    if ijac == 1:

        def py_jac(time, state_vec):
            if ynames and names is not None:
                state = State(np.asarray(state_vec, dtype=np.float64), names)
            else:
                state = np.asarray(state_vec, dtype=np.float64)
            mat = np.asarray(jacfunc(time, state, parms, **kwargs), dtype=np.float64)
            return np.asfortranarray(mat)

    imas = 0
    mlmas = n
    mumas = n
    mljac = int(banddown)
    mujac = int(bandup)

    integrate_radau = _radau_kernel()

    def kernel_deriv(t, y):
        return py_deriv(t, y)

    nt = len(grid)
    nsteps = min(2**31 - 1, int(maxsteps) * nt)
    yout_flat, idid, istate_raw, rstate = integrate_radau(
        values.tolist(),
        grid.tolist(),
        kernel_deriv,
        rtol_vec.tolist(),
        atol_vec.tolist(),
        float(hmax),
        hini,
        nsteps,
        nind3,
        int(ijac),
        mljac,
        mujac,
        imas,
        mlmas,
        mumas,
        py_jac,
        True,
    )
    table = np.asarray(yout_flat, dtype=np.float64).reshape(nt, n + 1)

    if idid == -1:
        warnings.warn("input is not consistent", stacklevel=2)
    elif idid == -2:
        warnings.warn("larger maxsteps needed", stacklevel=2)
    elif idid == -3:
        warnings.warn("step size becomes too small", stacklevel=2)
    elif idid == -4:
        warnings.warn("problem is probably stiff - interrupted", stacklevel=2)

    istate = _set_istate(istate_raw)

    if nglobal > 0:
        extra = np.empty((nt, nglobal), dtype=np.float64)
        for row in range(nt):
            if ynames and names is not None:
                state = State(table[row, 1 : 1 + n], names)
            else:
                state = table[row, 1 : 1 + n]
            extra[row] = _globals_of(_split_return(func2(table[row, 0], state))[1])
        table = np.hstack([table, extra])

    state_names = [str(index + 1) for index in range(n)] if names is None else list(names)
    colnames = ["time", *state_names]
    if nglobal > 0:
        colnames.extend(global_names or [str(n + 1 + i) for i in range(nglobal)])

    result = DeSolveMatrix(
        table,
        colnames,
        istate,
        lengthvar,
        lengthvar_names,
        dimvar,
    )
    result.type = "radau5"
    if verbose:
        _print_diagnostics(istate)
    return result
