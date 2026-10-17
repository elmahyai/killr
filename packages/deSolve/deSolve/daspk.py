"""Differential-algebraic solver (deSolve ``daspk`` / DDASPK)."""

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

_WARN_EXTRAS = (
    "events, roots, lags, forcings, mass, estini, and tcrit are not yet implemented for daspk;\n"
    "  those arguments are ignored.\n"
)


def _daspk_kernel():
    try:
        from daspk import integrate_daspk as _integrate_daspk
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "daspk"))
        from daspk import integrate_daspk as _integrate_daspk
    return _integrate_daspk


def _set_istate(raw23: list[int]) -> list:
    """``setIstate(istate, iin=c(1,8:9,12:20), iout=c(1,6,5,2:4,13,12,19,9,8,11))``."""
    iin = [1, 8, 9, 12, 13, 14, 15, 16, 17, 18, 19, 20]
    iout = [1, 6, 5, 2, 3, 4, 13, 12, 19, 9, 8, 11]
    istate = [None] * 21
    for src, dst in zip(iin, iout, strict=True):
        istate[dst - 1] = int(raw23[src - 1])
    return istate


def _print_diagnostics(istate):
    for index, text in enumerate(_ISTATE_TEXT):
        value = istate[index] if index < len(istate) else None
        if value is None:
            continue
        print(f"{text} {value}")


def daspk(
    y,
    times,
    parms,
    func=None,
    nind=None,
    dy=None,
    res=None,
    nalg=0,
    rtol=1e-6,
    atol=1e-6,
    jacfunc=None,
    jacres=None,
    jactype="fullint",
    mass=_MISSING,
    estini=None,
    verbose=False,
    tcrit=None,
    hmin=0,
    hmax=None,
    hini=0,
    ynames=True,
    maxord=5,
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

    if res is None and func is None:
        raise ValueError("either `func' or 'res' must be specified")
    if res is not None and func is not None:
        raise ValueError("either `func' OR 'res' must be specified, not both")
    if jacfunc is not None and jacres is not None:
        raise ValueError("either `jacfunc' OR 'jacres' must be specified, not both")

    if isinstance(func, dict):
        if jacfunc is not None and "jacfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains jacfunc, argument 'jacfunc' should be NULL"
            )
        if initfunc is not None and initfunc is not dllname and "initfunc" in func:
            raise ValueError(
                "If 'func' is a list that contains initfunc, argument 'initfunc' should be NULL"
            )
        if dllname is not None and "dllname" in func:
            raise ValueError(
                "If 'func' is a list that contains dllname, argument 'dllname' should be NULL"
            )
        jacfunc = func.get("jacfunc", jacfunc)
        initfunc = func.get("initfunc", initfunc)
        dllname = func.get("dllname", dllname)
        func = func.get("func")

    if isinstance(res, dict):
        if jacres is not None and "jacres" in res:
            raise ValueError(
                "If 'res' is a list that contains jacres, argument 'jacres' should be NULL"
            )
        jacres = res.get("jacres", jacres)
        initfunc = res.get("initfunc", initfunc)
        dllname = res.get("dllname", dllname)
        res = res.get("res")

    values, names = _as_y(y)
    n = len(values)
    if times is not None:
        _as_times(times)
    if jacfunc is not None and not callable(jacfunc):
        raise ValueError("`jacfunc' must be a function or NULL")
    if jacres is not None and not callable(jacres):
        raise ValueError("`jacres' must be a function or character vector or of class 'CFunc'")
    if isinstance(res, str) or isinstance(func, str) or dllname is not None:
        _reject_compiled(func if res is None else res, dllname)

    rtol_arr = np.asarray(rtol, dtype=np.float64).reshape(-1)
    atol_arr = np.asarray(atol, dtype=np.float64).reshape(-1)
    if atol_arr.size > 1 and atol_arr.size != n:
        raise ValueError("`atol' must either be a scalar, or as long as `y'")
    if rtol_arr.size > 1 and rtol_arr.size != n:
        raise ValueError("`rtol' must either be a scalar, or as long as `y'")
    if not np.isscalar(hmin):
        raise ValueError("`hmin' must be numeric")
    if float(hmin) < 0:
        raise ValueError("`hmin' must be a non-negative value")
    if hmax is None:
        hmax = 0.0 if times is None else float(np.max(np.abs(np.diff(_as_times(times)))))
    if not np.isscalar(hmax):
        raise ValueError("`hmax' must be numeric")
    if float(hmax) < 0:
        raise ValueError("`hmax' must be a non-negative value")
    if float(hini) < 0:
        raise ValueError("`hini' must be a non-negative value")
    if not np.isscalar(maxord):
        raise ValueError("`maxord' must be numeric")
    if maxord < 1 or maxord > 5:
        raise ValueError("`maxord' must be >1 and <=5")
    if mass is not _MISSING and mass is not None and res is not None:
        raise ValueError("cannot combine `res' with 'mass' - use 'func' instead, or set 'mass' = NULL")

    if any(
        x is not None
        for x in (
            events,
            lags,
            forcings,
            tcrit,
            estini,
            mass if mass is not _MISSING else None,
        )
    ):
        warnings.warn(_WARN_EXTRAS, stacklevel=2)

    if jactype == "fullint":
        imp = 22
    elif jactype == "fullusr":
        imp = 21
    elif jactype == "bandusr":
        imp = 24
    elif jactype == "bandint":
        imp = 25
    else:
        raise ValueError("'jactype' must be one of 'fullint', 'fullusr', 'bandusr' or 'bandint'")

    if imp in (24, 25) and bandup is None:
        raise ValueError("'bandup' must be specified if banded Jacobian")
    if imp in (24, 25) and banddown is None:
        raise ValueError("'banddown' must be specified if banded Jacobian")

    erow = None
    if imp == 24:
        erow = np.zeros((banddown, n), dtype=np.float64)
    if banddown is None:
        banddown = 1
    if bandup is None:
        bandup = 1

    if dy is None:
        dy_vec = np.zeros(n, dtype=np.float64)
    else:
        dy_vec = np.asarray(dy, dtype=np.float64).reshape(-1)
        if dy_vec.size != n:
            raise ValueError("`dy' must be numeric")

    if nind is None:
        nind3 = [n, 0, 0]
    else:
        nind3 = [int(x) for x in np.asarray(nind, dtype=int).reshape(-1)]
        if len(nind3) != 3:
            raise ValueError("length of `nind' must be = 3")
        if sum(nind3) != n:
            raise ValueError("sum of of `nind' must equal n, the number of equations")

    grid = _as_times(times) if times is not None else np.array([0.0, 1e8], dtype=np.float64)

    if imp in (22, 25):
        info5 = 0
    else:
        info5 = 1
    if imp in (22, 21):
        info6 = 0
    else:
        info6 = 1
    if info5 == 1 and jacfunc is None and jacres is None:
        raise ValueError(
            "daspk: cannot perform integration: *jacfunc* or *jacres* NOT specified; "
            "either specify *jacfunc* or *jacres* or change *jactype*"
        )

    if len(atol_arr) == n and len(rtol_arr) != n:
        rtol_arr = np.resize(rtol_arr, n)
    elif len(rtol_arr) == n and len(atol_arr) != n:
        atol_arr = np.resize(atol_arr, n)

    info = [0] * 25
    info[1] = 1 if len(atol_arr) == n else 0
    info[2] = 1 if times is None else 0
    info[4] = info5
    info[5] = info6
    info[6] = 1 if hmax != np.inf else 0
    info[7] = 1 if hini != 0 else 0
    info[8] = 1 if maxord != 5 else 0
    info[19] = 1
    info[20], info[21], info[22] = nind3

    nrowpd = n if info6 == 0 else 2 * banddown + bandup + 1
    lrw = 50 + max(maxord + 4, 7) * n
    if info6 == 0:
        lrw += n * n
    elif info5 == 0:
        lrw += (2 * banddown + bandup + 1) * n + 2 * (n // (bandup + banddown + 1) + 1)
    else:
        lrw += (2 * banddown + bandup + 1) * n
    liw = 40 + n

    iwork = [0] * liw
    rwork = [0.0] * lrw
    if info6 == 1:
        iwork[0] = int(banddown)
        iwork[1] = int(bandup)
    if info[6]:
        rwork[1] = float(hmax)
    if info[7]:
        rwork[2] = float(hini)
    if info[8]:
        iwork[2] = int(maxord)

    max_it = max(1, (maxsteps + 499) // 500)

    mass_mat = None
    if mass is not _MISSING and mass is not None:
        mass_mat = np.asarray(mass, dtype=np.float64)
        if mass_mat.shape != (n, n):
            raise ValueError("mass must be an n by n matrix")

    if res is not None:

        def res2(time, state, yprime):
            if ynames and names is not None:
                state = State(np.asarray(state, dtype=np.float64), names)
            else:
                state = np.asarray(state, dtype=np.float64)
            yp = np.asarray(yprime, dtype=np.float64)
            return res(float(time), state, yp, parms, **kwargs)

        tmp = _split_return(res2(grid[0], values, dy_vec))
        parents, components = tmp
        got = len(components[0][0])
        if got != n:
            _derivative_error(got, n)
        lengthvar, lengthvar_names = _lengthvar(components, parents)
        extra_parents = None if parents is None else parents[1:]
        global_names = _unlist_names(components[1:], extra_parents)
        nglobal = int(sum(len(data) for data, _inner, _shape in components[1:]))
        dimvar = _dimvar(components, nglobal)

        if jacres is not None:
            jac_sample = jacres(grid[0], values, dy_vec, parms, 1.0, **kwargs)
            jac_arr = np.asarray(jac_sample, dtype=np.float64)
            if jac_arr.ndim != 2:
                raise ValueError("jacres must return a matrix\n")
            dd = jac_arr.shape
            if (imp == 24 and dd != (bandup + banddown + 1, n)) or (
                imp == 21 and dd != (n, n)
            ):
                raise ValueError("Jacobian dimension not ok")

        def py_res(t, state, yprime, _cj):
            if ynames and names is not None:
                st = State(np.asarray(state, dtype=np.float64), names)
                yp = State(np.asarray(yprime, dtype=np.float64), None)
            else:
                st = np.asarray(state, dtype=np.float64)
                yp = np.asarray(yprime, dtype=np.float64)
            delta = np.asarray(_split_return(res2(t, st, yp))[1][0][0], dtype=np.float64).reshape(
                -1
            )
            return delta.tolist()

        py_jac = None
        if jacres is not None:

            def py_jac(t, state, yprime, cj):
                if ynames and names is not None:
                    st = State(np.asarray(state, dtype=np.float64), names)
                    yp = State(np.asarray(yprime, dtype=np.float64), None)
                else:
                    st = np.asarray(state, dtype=np.float64)
                    yp = np.asarray(yprime, dtype=np.float64)
                mat = np.asarray(jacres(t, st, yp, parms, cj, **kwargs), dtype=np.float64)
                if erow is not None:
                    mat = np.vstack([erow, mat])
                return np.asfortranarray(mat)

    else:

        def func2(time, state):
            return _call_model(func, time, state, names, ynames, parms, kwargs)

        tmp = _split_return(func2(grid[0], values))
        parents, components = tmp
        got = len(components[0][0])
        if got != n:
            _derivative_error(got, n)
        lengthvar, lengthvar_names = _lengthvar(components, parents)
        extra_parents = None if parents is None else parents[1:]
        global_names = _unlist_names(components[1:], extra_parents)
        nglobal = int(sum(len(data) for data, _inner, _shape in components[1:]))
        dimvar = _dimvar(components, nglobal)

        if jacfunc is not None:
            state0 = State(values, names) if ynames and names is not None else values
            jac_sample = jacfunc(grid[0], state0, parms, **kwargs)
            jac_arr = np.asarray(jac_sample, dtype=np.float64)
            if jac_arr.ndim != 2:
                raise ValueError("jacfunc must return a matrix\n")
            if imp in (24, 25) and mass_mat is not None:
                raise ValueError("cannot combine banded jacobian with mass")

        def py_res(t, state, yprime, _cj):
            if ynames and names is not None:
                st = State(np.asarray(state, dtype=np.float64), names)
            else:
                st = np.asarray(state, dtype=np.float64)
            yp = np.asarray(yprime, dtype=np.float64).reshape(-1)
            deriv = np.asarray(_split_return(func2(t, st))[1][0][0], dtype=np.float64).reshape(-1)
            if mass_mat is None:
                return (yp - deriv).tolist()
            return list(mass_mat @ yp - deriv)

        py_jac = None
        if jacfunc is not None:

            def py_jac(t, state, yprime, cj):
                if ynames and names is not None:
                    st = State(np.asarray(state, dtype=np.float64), names)
                else:
                    st = np.asarray(state, dtype=np.float64)
                jf = -1.0 * np.asarray(jacfunc(t, st, parms, **kwargs), dtype=np.float64)
                if mass_mat is None:
                    if imp in (24, 25):
                        jf[int(bandup), :] += cj
                        if erow is not None:
                            jf = np.vstack([erow, jf])
                    else:
                        jf += np.diag(np.full(n, cj))
                else:
                    jf += cj * mass_mat
                return np.asfortranarray(jf)

    integrate = _daspk_kernel()
    yout_flat, idid, istate_raw, rstate = integrate(
        values.tolist(),
        dy_vec.tolist(),
        grid.tolist(),
        py_res,
        rtol_arr.tolist(),
        atol_arr.tolist(),
        info,
        iwork,
        rwork,
        int(max_it),
        int(nrowpd),
        py_jac,
    )

    if idid == -2:
        warnings.warn(
            "Excessive precision requested.  scale up `rtol' and `atol' e.g. by the factor 10",
            stacklevel=2,
        )

    nt = len(grid)
    table = np.asarray(yout_flat, dtype=np.float64).reshape(nt, n + 1)
    table[0, 0] = grid[0]

    if nglobal > 0:
        extra = np.empty((nt, nglobal), dtype=np.float64)
        for row in range(nt):
            t = table[row, 0]
            st = table[row, 1 : 1 + n]
            if res is not None:
                if ynames and names is not None:
                    state = State(st, names)
                    yp = State(dy_vec, None)
                else:
                    state = st
                    yp = dy_vec
                extra[row] = _globals_of(_split_return(res2(t, state, yp))[1])
            else:
                if ynames and names is not None:
                    state = State(st, names)
                else:
                    state = st
                extra[row] = _globals_of(_split_return(func2(t, state))[1])
        table = np.hstack([table, extra])

    istate = _set_istate(istate_raw)
    state_names = [str(i + 1) for i in range(n)] if names is None else list(names)
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
    result.type = "daspk"
    result.rstate = list(rstate)
    if verbose:
        _print_diagnostics(istate)
    return result
