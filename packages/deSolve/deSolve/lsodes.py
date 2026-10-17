"""Sparse Jacobian ODE integrator (deSolve ``lsodes`` / DLSODES)."""

from __future__ import annotations

import sys
import warnings

import numpy as np

from deSolve.rk4 import (
    DeSolveMatrix,
    State,
    _ISTATE_TEXT,
    _as_times,
    _as_y,
    _call_model,
    _derivative_error,
    _globals_of,
    _reject_compiled,
    _split_return,
    _unpack_model,
    _unlist_names,
    _lengthvar,
)

_WARN_EXTRAS = (
    "events, roots, lags, forcings, and PDE sparsetype 1D/2D/3D are not yet implemented for lsodes;\n"
    "  those arguments are ignored or rejected.\n"
)


def _lsodes_kernel():
    try:
        from lsodes import integrate_lsodes as _integrate_lsodes
    except ImportError:
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "lsodes"))
        from lsodes import integrate_lsodes as _integrate_lsodes
    return _integrate_lsodes


def _check_input(y, times, func, rtol, atol, jacvec, tcrit, hmin, hmax, hini, dllname):
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
    if jacvec is not None and not (callable(jacvec) or isinstance(jacvec, str)):
        raise ValueError("jacvec  must be a function or character vector")
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


def _set_istate(raw21: list[int]) -> list:
    """``setIstate(istate, iin=c(1,12:20), iout=c(1:3,14,5:9,17))``."""
    iin = [0, 11, 12, 13, 14, 15, 16, 17, 18, 19]
    iout = [0, 1, 2, 13, 4, 5, 6, 7, 8, 16]
    istate = [None] * 21
    for src, dst in zip(iin, iout, strict=True):
        istate[dst] = raw21[src] if src < len(raw21) else None
    return istate


def _save_out(table, y_names, n, nglobal, nmtot, istate_raw, rstate):
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
    result.type = "lsodes"
    result.rstate = list(rstate[:4])
    return result


def _build_iwork_sparseusr(inz: np.ndarray, n: int, liw: int) -> tuple[int, np.ndarray]:
    nnz = inz.shape[0]
    iwork = np.zeros(liw, dtype=np.int32)
    iwork[30] = 32 + n
    rr = inz[:, 1]
    if np.any(np.diff(rr[1:]) < 0):
        raise ValueError("cannot proceed: column indices (2nd column of inz) should be sorted")
    for i in range(1, n + 1):
        ii = np.where(rr == i)[0]
        il = len(ii)
        i1 = iwork[i + 29]
        i2 = iwork[i + 29] + il - 1
        iwork[i + 30] = i2 + 1
        if il > 0:
            iwork[i1:i2 + 1] = inz[ii, 0]
    iwork[31 : 31 + n] = iwork[31 : 31 + n] - (31 + n)
    return nnz, iwork


def lsodes(
    y,
    times,
    func,
    parms,
    rtol=1e-6,
    atol=1e-6,
    jacvec=None,
    sparsetype="sparseint",
    nnz=None,
    inz=None,
    rootfunc=None,
    verbose=False,
    nroot=0,
    tcrit=None,
    hmin=0,
    hmax=None,
    hini=0,
    ynames=True,
    maxord=None,
    maxsteps=5000,
    lrw=None,
    liw=None,
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
    integrate_lsodes = _lsodes_kernel()

    if isinstance(func, dict):
        if jacvec is not None and "jacvec" in func:
            raise ValueError(
                "If 'func' is a list that contains jacvec, argument 'jacvec' should be NULL"
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
        jacvec = func.get("jacvec", jacvec)
        rootfunc = func.get("rootfunc", rootfunc)
        initfunc = func.get("initfunc", initfunc)
        dllname = func.get("dllname", dllname)
        initforc = func.get("initforc", initforc)
        func = func.get("func")

    if initfunc is None:
        initfunc = dllname
    if initpar is None:
        initpar = parms

    func, initfunc, dllname, initforc = _unpack_model(func, initfunc, dllname, initforc)
    _reject_compiled(func, dllname)

    if any(x is not None for x in (rootfunc, events, lags, forcings)) or nroot > 0:
        warnings.warn(_WARN_EXTRAS, stacklevel=2)

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
        rootfunc,
    )

    values, names = _as_y(y)
    grid = _as_times(times) if times is not None else np.array([0.0, 1e8], dtype=np.float64)
    if len(grid) == 0:
        raise ValueError("`times' must be NULL or numeric")
    n = len(values)

    hmax = _check_input(y, times, func, rtol, atol, jacvec, tcrit, hmin, hmax, hini, dllname)

    if maxord is None:
        maxord = 5
    if maxord > 5:
        raise ValueError("'maxord' too large: should be <= 5")
    if maxord < 1:
        raise ValueError("`maxord' must be >1")

    if sparsetype == "sparseusr" and inz is None:
        raise ValueError("'inz' must be specified if 'sparsetype' = 'sparseusr'")
    if sparsetype == "sparsejan" and inz is None:
        raise ValueError("'inz' must be specified if 'sparsetype' = 'sparsejan'")
    if sparsetype == "1D" and jacvec is not None:
        raise ValueError("cannot combine 'sparsetype=1D' and 'jacvec'")
    if sparsetype in ("2D", "2Dmap") and jacvec is not None:
        raise ValueError("cannot combine 'sparsetype=2D' and 'jacvec'")
    if sparsetype in ("3D", "3Dmap") and jacvec is not None:
        raise ValueError("cannot combine 'sparsetype=3D' and 'jacvec'")

    if jacvec is not None and sparsetype in ("sparseusr", "sparsejan"):
        imp = 21
    elif jacvec is not None:
        imp = 121
    elif sparsetype in ("sparseusr", "sparsejan", "1D", "2D", "2Dmap", "3D", "3Dmap"):
        imp = 22
    else:
        imp = 222

    type_code = 1
    nnz_val = int(n * n) if nnz is None else int(nnz)
    iwork_extra = None

    if sparsetype == "1D":
        raise NotImplementedError("sparsetype '1D' requires deSolve sparsity helpers not yet ported")
    if sparsetype in ("2D", "2Dmap", "3D", "3Dmap"):
        raise NotImplementedError(
            f"sparsetype '{sparsetype}' requires deSolve sparsity helpers not yet ported"
        )
    if sparsetype == "sparseusr":
        type_code = 0
        inz_arr = np.asarray(inz, dtype=np.int32)
        nnz_val = inz_arr.shape[0]
        liw_use = max(liw or 0, 31 + n + nnz_val + 30)
        _, iwork_extra = _build_iwork_sparseusr(inz_arr, n, liw_use)
    elif sparsetype == "sparsejan":
        type_code = 0
        inz_vec = np.asarray(inz, dtype=np.int32).reshape(-1)
        nnz_val = len(inz_vec) - n
        liw_use = max(liw or 0, len(inz_vec) + 30)
        iwork_extra = np.zeros(liw_use, dtype=np.int32)
        linz = 30 + len(inz_vec)
        iwork_extra[30:linz] = inz_vec
    else:
        type_code = 1
        if nnz is None:
            nnz_val = n * n

    if nnz_val < 1:
        raise ValueError("Jacobian should at least contain one non-zero value")

    _ = type_code

    miter = imp % 10
    if miter in (1, 4) and jacvec is None and imp not in (22, 222):
        raise ValueError(
            "'jacvec' NOT specified; either specify 'jacvec' or change 'sparsetype'"
        )

    def func2(time, state):
        return _call_model(func, time, state, names, ynames, parms, kwargs)

    nglobal, nmtot, _components = _check_func(func2, grid, values, ynames, names)

    jac_py = None
    if jacvec is not None:
        if not callable(jacvec):
            raise ValueError("jacvec must be a function")

        def jac_wrapped(time, state, col):
            out = jacvec(float(time), state, int(col), parms, **kwargs)
            return np.asarray(out, dtype=np.float64).reshape(-1)

        jac_test = jac_wrapped(grid[0], State(values, names) if ynames and names else values, 1)
        if jac_test.size != n:
            raise ValueError("jacvec must return a vector of length n")
        jac_py = jac_wrapped

    rtol_scalar = float(np.asarray(rtol, dtype=np.float64).reshape(-1)[0])
    atol_scalar = float(np.asarray(atol, dtype=np.float64).reshape(-1)[0])

    def deriv_for_rust(t, y_arr):
        state = y_arr if not ynames or names is None else State(np.asarray(y_arr), names)
        out = _split_return(_call_model(func, float(t), state, names, ynames, parms, kwargs))[1][0][0]
        return list(out)

    def jac_for_rust(t, y_arr, col):
        state = y_arr if not ynames or names is None else State(np.asarray(y_arr), names)
        return list(jac_wrapped(float(t), state, int(col)))

    jac_cb = jac_for_rust if jac_py is not None else None

    table, istate_raw, rstate = integrate_lsodes(
        np.asarray(values, dtype=np.float64),
        np.asarray(grid, dtype=np.float64),
        deriv_for_rust,
        imp=int(imp),
        maxord=int(maxord),
        maxsteps=int(maxsteps),
        nnz=int(nnz_val),
        rtol=rtol_scalar,
        atol=atol_scalar,
        hini=float(hini or 0.0),
        hmax=float(hmax),
        hmin=float(hmin),
        tcrit=float(tcrit) if tcrit is not None else None,
        lrw=int(lrw) if lrw is not None else None,
        liw=int(liw) if liw is not None else None,
        iwork=iwork_extra.tolist() if iwork_extra is not None else None,
        jacvec=jac_cb,
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
    if verbose:
        for index, text in enumerate(_ISTATE_TEXT):
            value = result.istate[index] if index < len(result.istate) else None
            if value is not None:
                sys.stdout.write(f"{text} {value}\n")
    return result
