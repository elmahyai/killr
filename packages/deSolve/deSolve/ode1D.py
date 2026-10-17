"""Multicomponent 1-D ODE driver (deSolve ``ode.1D``)."""

from __future__ import annotations

import warnings
import numpy as np

from deSolve.rk4 import (
    DeSolveMatrix,
    State,
    _as_y,
    _call_model,
    _split_return,
)
from deSolve.rkMethod import RkMethod, rkMethod


def _order_index(n: int, nspec: int, per_spec: bool) -> np.ndarray:
    """1-based reorder used by ``ode.1D`` (``ii`` or ``ij``), matching R ``matrix`` layout."""
    if per_spec:
        matrix = np.arange(1, n + 1).reshape((n // nspec, nspec), order="F")
    else:
        matrix = np.arange(1, n + 1).reshape((nspec, n // nspec), order="F")
    return matrix.T.reshape(-1, order="F").astype(int)


def _attach_1d_attrs(out: DeSolveMatrix, dimens: int, nspec: int, names) -> DeSolveMatrix:
    out.dimens = dimens
    out.nspec = nspec
    out.ynames = None if names is None else list(names)
    return out


def _restore_state_columns(out: DeSolveMatrix, ii: np.ndarray, n: int, state_names) -> DeSolveMatrix:
    """Map integrator columns (``y[ii]`` order) back to the user's ``y`` order."""
    ii0 = ii - 1
    block = out.data[:, 1 : n + 1].copy()
    restored = np.empty_like(block)
    for k in range(n):
        restored[:, ii0[k]] = block[:, k]
    out.data[:, 1 : n + 1] = restored
    if state_names is not None:
        out.colnames[1 : n + 1] = list(state_names)
    return out


def _integrate_band(
    y,
    times,
    func,
    parms,
    method: str,
    bandup: int,
    banddown: int,
    kwargs: dict,
):
    common = dict(
        y=y,
        times=times,
        func=func,
        parms=parms,
        bandup=bandup,
        banddown=banddown,
        jactype="bandint",
        **kwargs,
    )
    if method == "vode":
        from deSolve.vode import vode

        return vode(**common)
    if method == "lsode":
        from deSolve.lsode import lsode

        return lsode(**common)
    if method == "lsoda":
        from deSolve.lsoda import lsoda

        return lsoda(**common)
    if method == "lsodar":
        from deSolve.lsodar import lsodar

        return lsodar(**common)
    if method == "daspk":
        from deSolve.daspk import daspk

        return daspk(**common)
    if method == "radau":
        from deSolve.radau import radau

        return radau(**common)
    raise ValueError("cannot run ode.band: method should be one of vode, lsoda, lsodar or lsode")


def _make_bmodel(func, ij: np.ndarray, ii: np.ndarray, n: int, names, ynames: bool):
    ij0 = ij - 1
    ii0 = ii - 1

    def bmodel(time, state, pars, **kw):
        ordered = np.asarray(state, dtype=np.float64).reshape(-1)
        model_state = ordered[ij0]
        if ynames and names is not None:
            model_vec = State(model_state, names)
        else:
            model_vec = model_state
        result = _call_model(func, time, model_vec, names, ynames, pars, kw)
        parents, components = _split_return(result)
        rates = np.asarray(components[0][0], dtype=np.float64).reshape(-1)
        if len(rates) != n:
            raise ValueError(
                "The number of derivatives returned by func() ("
                f"{len(rates)}) must equal the length of the initial conditions vector ({n})"
            )
        reordered = rates[ii0]
        if isinstance(result, dict):
            out = dict(result)
            key = list(out.keys())[0]
            out[key] = reordered
            return out
        out_list = list(result)
        out_list[0] = reordered
        return out_list

    return bmodel


def _solver_initial(values, ii: np.ndarray, state_names):
    y_solver = values[ii - 1]
    if state_names is None:
        return y_solver
    return State(y_solver, [state_names[i - 1] for i in ii])


def ode_1D(
    y,
    times,
    func,
    parms,
    nspec=None,
    dimens=None,
    method="lsoda",
    names=None,
    bandwidth=1,
    restructure=False,
    **kwargs,
):
    """Solve 1-D method-of-lines ODE systems (deSolve ``ode.1D``)."""
    extra_keys = set(kwargs)
    if extra_keys.intersection({"jacfunc"}):
        raise ValueError(
            "cannot run ode.1D with jacfunc specified - remove jacfunc from call list"
        )

    if nspec is None and dimens is None:
        raise ValueError("cannot run ode.1D: nspec OR dimens should be specified")

    values, state_names = _as_y(y)
    n = len(values)
    iscomplex = np.iscomplexobj(values)

    if nspec is None:
        nspec = n // int(dimens)
    nspec = int(nspec)
    if n % nspec != 0:
        raise ValueError(
            "cannot run ode.1D: nspec is not an integer fraction of number of state variables"
        )

    if names is not None and len(names) != nspec:
        raise ValueError("length of 'names' should equal 'nspec'")

    if method is None:
        method = "lsoda"

    method_str = method if isinstance(method, str) else None
    islsodes = method_str == "lsodes"

    if isinstance(method, str):
        allowed = (
            "lsoda",
            "lsode",
            "lsodes",
            "lsodar",
            "vode",
            "daspk",
            "euler",
            "rk4",
            "ode23",
            "ode45",
            "radau",
            "bdf",
            "adams",
            "impAdams",
            "iteration",
        )
        if method not in allowed:
            raise ValueError(
                f"'{method}' is not a valid method; choose from {', '.join(allowed)}"
            )

    if (
        isinstance(method, str)
        and nspec == 1
        and method in ("lsoda", "lsode", "lsodar", "vode", "daspk", "radau")
    ):
        out = _integrate_band(
            y,
            times,
            func,
            parms,
            method,
            bandup=nspec * bandwidth,
            banddown=nspec * bandwidth,
            kwargs=kwargs,
        )
        if dimens is None:
            dimens = n // nspec
        return _attach_1d_attrs(out, int(dimens), nspec, names)

    explicit = False
    adams_expl = False
    if isinstance(method, str):
        if method in ("euler", "rk4", "ode23", "ode45", "iteration"):
            explicit = True
        adams_expl = explicit or method == "adams"

    if (isinstance(func, str) and not explicit) or islsodes:
        if isinstance(method, str) and method not in (
            "lsodes",
            "euler",
            "rk4",
            "ode23",
            "ode45",
            "iteration",
        ):
            warnings.warn(
                "ode.1D: R-function specified in a DLL-> integrating with lsodes",
                stacklevel=2,
            )
        if dimens is None:
            dimens = n // nspec
        from deSolve.lsodes import lsodes

        if bandwidth != 1:
            out = lsodes(y=y, times=times, func=func, parms=parms, **kwargs)
        else:
            out = lsodes(
                y=y,
                times=times,
                func=func,
                parms=parms,
                sparsetype="1D",
                nnz=(nspec, int(dimens), bandwidth),
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
    elif callable(method) and not restructure:
        out = method(y, times, func, parms, **kwargs)
    elif callable(method) and restructure:
        if isinstance(func, str):
            raise ValueError("cannot run ode.1D with R-function specified in a DLL")
        ii = _order_index(n, nspec, True)
        ij = _order_index(n, nspec, False)
        bmod = _make_bmodel(func, ij, ii, n, state_names, ynames=True)
        y_solver = _solver_initial(values, ii, state_names)
        out = method(
            y_solver,
            times,
            func=bmod,
            parms=parms,
            bandup=nspec * bandwidth,
            banddown=nspec * bandwidth,
            jactype="bandint",
            **kwargs,
        )
        out = _restore_state_columns(out, ii, n, state_names)
    elif adams_expl:
        from deSolve.rk import rk

        if method == "euler":
            out = rk(y, times, func, parms, method="euler", **kwargs)
        elif method == "rk4":
            out = rk(y, times, func, parms, method="rk4", **kwargs)
        elif method == "ode23":
            out = rk(y, times, func, parms, method="ode23", **kwargs)
        elif method == "ode45":
            out = rk(y, times, func, parms, method="ode45", **kwargs)
        elif method == "adams" and not iscomplex:
            from deSolve.lsode import lsode

            out = lsode(y, times, func, parms, mf=10, **kwargs)
        elif method == "adams" and iscomplex:
            from deSolve.zvode import zvode

            out = zvode(y, times, func, parms, mf=10, **kwargs)
        elif method == "iteration":
            raise NotImplementedError("iteration is not yet translated for deSolve")
        else:
            raise ValueError("cannot run ode.1D: not a valid 'method'")
    else:
        if isinstance(func, str):
            raise ValueError("cannot run ode.1D with R-function specified in a DLL")
        ii = _order_index(n, nspec, True)
        ij = _order_index(n, nspec, False)
        bmod = _make_bmodel(func, ij, ii, n, state_names, ynames=True)
        y_solver = _solver_initial(values, ii, state_names)
        band_args = dict(
            bandup=nspec * bandwidth,
            banddown=nspec * bandwidth,
            jactype="bandint",
        )
        integrator_kwargs = {**band_args, **kwargs}
        if method is None:
            method = "lsode"
        if iscomplex:
            from deSolve.zvode import zvode

            if method == "vode":
                out = zvode(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
            elif method == "bdf":
                out = zvode(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
            elif method == "impAdams":
                out = zvode(y_solver, times, func=bmod, parms=parms, mf=15, **integrator_kwargs)
            else:
                raise ValueError("cannot run ode.1D: not a valid 'method'")
        elif method == "vode":
            from deSolve.vode import vode

            out = vode(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
        elif method in ("lsode", "bdf"):
            from deSolve.lsode import lsode

            out = lsode(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
        elif method == "impAdams":
            from deSolve.lsode import lsode

            out = lsode(y_solver, times, func=bmod, parms=parms, mf=15, **integrator_kwargs)
        elif method == "lsoda":
            from deSolve.lsoda import lsoda

            out = lsoda(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
        elif method == "lsodar":
            from deSolve.lsodar import lsodar

            out = lsodar(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
        elif method == "daspk":
            from deSolve.daspk import daspk

            out = daspk(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
        elif method == "radau":
            from deSolve.radau import radau

            out = radau(y_solver, times, func=bmod, parms=parms, **integrator_kwargs)
        else:
            raise ValueError("cannot run ode.1D: not a valid 'method'")
        out = _restore_state_columns(out, ii, n, state_names)

    if dimens is None:
        dimens = n // nspec
    return _attach_1d_attrs(out, int(dimens), nspec, names)
