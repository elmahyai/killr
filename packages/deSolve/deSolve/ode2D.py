"""Multicomponent 2-D ODE driver (deSolve ``ode.2D``)."""

from __future__ import annotations

import sys
import warnings

import numpy as np

from deSolve.rk4 import DeSolveMatrix, State, _as_y, _as_times, _call_model, _globals_of, _split_return
from deSolve.rkMethod import RkMethod, rkMethod


def _attach_2d_attrs(out: DeSolveMatrix, dimens, nspec: int, names) -> DeSolveMatrix:
    out.dimens = list(dimens)
    out.nspec = int(nspec)
    out.ynames = None if names is None else list(names)
    return out


def _cyclic_bnd_vector(cyclic_bnd) -> list[int]:
    bnd = [0, 0]
    if cyclic_bnd is None:
        return bnd
    values = np.atleast_1d(cyclic_bnd).astype(int).reshape(-1)
    if values.size and int(np.max(values)) > 2:
        raise ValueError("cannot run ode.2D: cyclicBnd should be a vector or number not exceeding 2")
    for item in values:
        if int(item) > 0:
            bnd[int(item) - 1] = 1
    return bnd


def _nnz_count_2d(n: int, nspec: int, dimens, bnd, bandwidth: int = 1) -> int:
    rev_dimens = list(reversed(dimens))
    rev_bnd = list(reversed(bnd))
    nnz_val = n * (4 + nspec * bandwidth) - 2 * nspec * sum(rev_dimens)
    maxdim = max(rev_dimens)
    if rev_bnd[0] == 1:
        nnz_val += 2 * maxdim * nspec * bandwidth
    if rev_bnd[1] == 1:
        nnz_val += 2 * maxdim * nspec * bandwidth
    return int(nnz_val)


def _sparsity_2d(type_vec, iwork: np.ndarray, neq: int, liw: int) -> None:
    """Port of deSolve ``sparsity2D`` (``deSolve_utils.c``)."""
    nspec = int(type_vec[1])
    nx = int(type_vec[2])
    ny = int(type_vec[3])
    bndx = int(type_vec[4])
    bndy = int(type_vec[5])
    nt = nx * ny
    ij = 31 + neq
    iwork[30] = 1
    m = 1
    for i in range(nspec):
        isp = i * nt
        for j in range(nx):
            for k in range(ny):
                if ij > liw - 8 - nspec:
                    raise ValueError(f"not enough memory allocated in iwork - increase liw {liw}")
                iwork[ij] = m
                ij += 1
                if k < ny - 1:
                    iwork[ij] = m + 1
                    ij += 1
                if j < nx - 1:
                    iwork[ij] = m + ny
                    ij += 1
                if j > 0:
                    iwork[ij] = m - ny
                    ij += 1
                if k > 0:
                    iwork[ij] = m - 1
                    ij += 1
                if bndx == 1:
                    if j == 0:
                        iwork[ij] = isp + (nx - 1) * ny + k + 1
                        ij += 1
                    if j == nx - 1:
                        iwork[ij] = isp + k + 1
                        ij += 1
                if bndy == 1:
                    if k == 0:
                        iwork[ij] = isp + (j + 1) * ny
                        ij += 1
                    if k == ny - 1:
                        iwork[ij] = isp + j * ny + 1
                        ij += 1
                for l in range(nspec):
                    if l != i:
                        iwork[ij] = l * nt + j * ny + k + 1
                        ij += 1
                iwork[30 + m] = ij - 30 - neq
                m += 1


def _integrate_lsodes_2d(y, times, func, parms, nspec, dimens, bnd, ynames, names, **kwargs):
    from deSolve.lsodes import (
        _check_func,
        _check_input,
        _lsodes_kernel,
        _save_out,
    )

    integrate_lsodes = _lsodes_kernel()
    values, state_names = _as_y(y)
    grid = _as_times(times) if times is not None else np.array([0.0, 1e8], dtype=np.float64)
    n = len(values)
    rtol = kwargs.pop("rtol", 1e-6)
    atol = kwargs.pop("atol", 1e-6)
    jacvec = kwargs.pop("jacvec", None)
    tcrit = kwargs.pop("tcrit", None)
    hmin = kwargs.pop("hmin", 0)
    hmax = kwargs.pop("hmax", None)
    hini = kwargs.pop("hini", 0)
    dllname = kwargs.pop("dllname", None)
    maxord = kwargs.pop("maxord", None)
    maxsteps = kwargs.pop("maxsteps", 5000)
    lrw = kwargs.pop("lrw", None)
    liw = kwargs.pop("liw", None)
    verbose = kwargs.pop("verbose", False)

    if jacvec is not None:
        raise ValueError("cannot combine 'sparsetype=2D' and 'jacvec'")

    hmax = _check_input(y, times, func, rtol, atol, jacvec, tcrit, hmin, hmax, hini, dllname)
    if maxord is None:
        maxord = 5
    if maxord > 5:
        raise ValueError("'maxord' too large: should be <= 5")
    if maxord < 1:
        raise ValueError("`maxord' must be >1")

    bandwidth = 1
    rev_dimens = list(reversed(dimens))
    rev_bnd = list(reversed(bnd))
    nnz_meta = [nspec, *rev_dimens, *rev_bnd, bandwidth]
    nnz_val = _nnz_count_2d(n, nspec, dimens, bnd, bandwidth)
    type_vec = [3, *nnz_meta]

    liw_use = liw if liw is not None else max(31 + n + nnz_val + 30, 30)
    iwork_extra = np.zeros(int(liw_use), dtype=np.int32)
    _sparsity_2d(type_vec, iwork_extra, n, int(liw_use))

    imp = 22

    def func2(time, state):
        return _call_model(func, time, state, names, ynames, parms, kwargs)

    nglobal, nmtot, _components = _check_func(func2, grid, values, ynames, names)

    rtol_scalar = float(np.asarray(rtol, dtype=np.float64).reshape(-1)[0])
    atol_scalar = float(np.asarray(atol, dtype=np.float64).reshape(-1)[0])

    def deriv_for_rust(t, y_arr):
        state = y_arr if not ynames or names is None else State(np.asarray(y_arr), names)
        out = _split_return(_call_model(func, float(t), state, names, ynames, parms, kwargs))[1][0][0]
        return list(out)

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
        liw=int(liw_use),
        iwork=iwork_extra.tolist(),
        jacvec=None,
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
        from deSolve.rk4 import _ISTATE_TEXT

        for index, text in enumerate(_ISTATE_TEXT):
            value = result.istate[index] if index < len(result.istate) else None
            if value is not None:
                sys.stdout.write(f"{text} {value}\n")
    return result


def ode_2D(
    y,
    times,
    func,
    parms,
    nspec=None,
    dimens=None,
    method="lsodes",
    names=None,
    cyclic_bnd=None,
    **kwargs,
):
    """Solve 2-D method-of-lines ODE systems (deSolve ``ode.2D``)."""
    if any(key == "jacfunc" for key in kwargs):
        raise ValueError(
            "cannot run ode.2D with jacfunc specified - remove jacfunc from call list"
        )

    if dimens is None:
        raise ValueError("cannot run ode.2D: dimens should be specified")
    dimens = list(np.atleast_1d(dimens).astype(int).reshape(-1))
    if len(dimens) != 2:
        raise ValueError("cannot run ode.2D: dimens should contain 2 values")

    values, state_names = _as_y(y)
    n = len(values)
    prod_dimens = int(dimens[0]) * int(dimens[1])
    if n % prod_dimens != 0:
        raise ValueError(
            "cannot run ode.2D: dimensions are not an integer fraction of number of state variables"
        )

    if nspec is None:
        nspec = n // prod_dimens
    nspec = int(nspec)
    if nspec * prod_dimens != n:
        raise ValueError(
            "cannot run ode.2D: dimens[1]*dimens[2]*nspec is not equal to number of state variables"
        )

    if names is not None and len(names) != nspec:
        raise ValueError("length of 'names' should equal 'nspec'")

    allowed = ("lsodes", "euler", "rk4", "ode23", "ode45", "adams", "iteration")
    method_str = method if isinstance(method, str) else None
    if isinstance(method, str) and method not in allowed:
        raise ValueError(f"'{method}' is not a valid method; choose from {', '.join(allowed)}")

    if method is None:
        method = "lsodes"
    islsodes = method_str == "lsodes"
    bnd = _cyclic_bnd_vector(cyclic_bnd)

    if isinstance(func, str) or islsodes:
        if isinstance(method, str) and method != "lsodes":
            warnings.warn(
                "ode.2D: R-function specified in a DLL-> integrating with lsodes",
                stacklevel=2,
            )
        if isinstance(func, str):
            from deSolve.lsodes import lsodes

            rev_dimens = list(reversed(dimens))
            rev_bnd = list(reversed(bnd))
            out = lsodes(
                y=y,
                times=times,
                func=func,
                parms=parms,
                sparsetype="2D",
                nnz=[nspec, *rev_dimens, *rev_bnd, 1],
                **kwargs,
            )
        else:
            out = _integrate_lsodes_2d(
                y,
                times,
                func,
                parms,
                nspec,
                dimens,
                bnd,
                ynames=True,
                names=state_names,
                **kwargs,
            )
    elif isinstance(method, (list, dict)) or isinstance(method, RkMethod):
        from deSolve.rk import rk

        if isinstance(method, dict):
            method = rkMethod(method)
        elif isinstance(method, str):
            method = rkMethod(method)
        elif not isinstance(method, RkMethod):
            raise TypeError("'method' should be given as string or as a list of class 'rkMethod'")
        out = rk(y, times, func, parms, method=method, **kwargs)
    elif callable(method):
        out = method(y, times, func, parms, **kwargs)
    elif method_str in ("euler", "rk4", "ode23", "ode45", "adams", "iteration"):
        if method_str == "euler":
            from deSolve.rk import rk

            out = rk(y, times, func, parms, method="euler", **kwargs)
        elif method_str == "rk4":
            from deSolve.rk import rk

            out = rk(y, times, func, parms, method="rk4", **kwargs)
        elif method_str == "ode23":
            from deSolve.rk import rk

            out = rk(y, times, func, parms, method="ode23", **kwargs)
        elif method_str == "ode45":
            from deSolve.rk import rk

            out = rk(y, times, func, parms, method="ode45", **kwargs)
        elif method_str == "adams":
            from deSolve.lsode import lsode

            out = lsode(y, times, func, parms, mf=10, **kwargs)
        elif method_str == "iteration":
            raise NotImplementedError("iteration is not yet translated for deSolve")
    else:
        raise ValueError("cannot run ode.2D: not a valid 'method'")

    return _attach_2d_attrs(out, dimens, nspec, names)
