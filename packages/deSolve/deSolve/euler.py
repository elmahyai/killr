"""Forward Euler with the step fixed by ``times`` (deSolve ``euler``)."""

import sys
import warnings

import numpy as np

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
    _reject_compiled,
    _split_return,
    _unpack_model,
    _unlist_names,
)
from deSolve.timestep import _advance_timestep, _reset_timesteps

_MISSING = object()

_WARN_HMIN = "hmin and hmax cannot be used in 'euler' (fixed steps)."
_HINI = (
    "'hini' is not supported by this version of 'euler',\n"
    "but you can use ode(......, method = 'euler', hini= .....)\n"
    "to set internal time steps smaller than external steps.\n"
)
_WARN_EVENTS = (
    "events and roots are not supported by this version of euler,\n"
    "  but you can use ode(......, method = 'euler', .....)\n"
)
_WARN_JAC = (
    "Euler and Runge-Kutta solvers make no use of a Jacobian,\n"
    "  ('jacfunc', 'jactype', 'mf', 'bandup' and 'banddown' are ignored).\n"
)
_WARN_LAGS = (
    "lags are not yet implemented for Euler and Runge-Kutta solvers,\n"
    "  (argument 'lags' is ignored).\n"
)


def _warn_unsupported(kwargs):
    names = set(kwargs)
    if "hmin" in names or "hmax" in names:
        sys.stdout.write(_WARN_HMIN)
    if "hini" in names:
        sys.stdout.write(_HINI)
    if "events" in names or "rootfunc" in names:
        warnings.warn(_WARN_EVENTS, stacklevel=3)
    if names.intersection(("jacfunc", "jactype", "mf", "bandup", "banddown")):
        warnings.warn(_WARN_JAC, stacklevel=3)
    if "lags" in names:
        warnings.warn(_WARN_LAGS, stacklevel=3)


def _print_diagnostics(istate):
    sys.stdout.write("\n--------------------\n")
    sys.stdout.write("rk return code")
    sys.stdout.write("\n--------------------\n")
    sys.stdout.write(f"\n  return code (idid) =  {istate[0]} \n")
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


def euler(
    y,
    times,
    func,
    parms,
    verbose=False,
    ynames=True,
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
    **kwargs,
):
    """Integrate ``y' = func(t, y, parms)`` with explicit Euler."""
    if initfunc is _MISSING:
        initfunc = dllname
    if initpar is _MISSING:
        initpar = parms

    func, initfunc, dllname, initforc = _unpack_model(func, initfunc, dllname, initforc)
    _warn_unsupported(kwargs)
    _reject_compiled(func, dllname)

    del initfunc, initpar, initforc, rpar, ipar, nout, outnames, forcings, fcontrol

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

    def deriv(time, state):
        returned = _split_return(
            _call_model(func, time, state, names, ynames, parms, kwargs)
        )[1]
        derivative = returned[0][0]
        if len(derivative) != neq:
            _derivative_error(len(derivative), neq)
        return derivative

    def globals_at(time, state):
        returned = _split_return(
            _call_model(func, time, state, names, ynames, parms, kwargs)
        )[1]
        flat = _globals_of(returned)
        if len(flat) != nglobal:
            raise ValueError(
                "The number of global outputs returned by func() ("
                f"{len(flat)}) must equal the number from the first call ({nglobal})"
            )
        return flat

    nt = len(grid)
    table = np.empty((nt, 1 + neq + nglobal), dtype=np.float64)
    table[0, 0] = grid[0]
    table[0, 1 : 1 + neq] = values
    state = values.copy()
    _reset_timesteps()
    for it in range(nt - 1):
        t = grid[it]
        dt = grid[it + 1] - t
        _advance_timestep(dt)
        state = state + dt * deriv(t, state)
        table[it + 1, 0] = t + dt
        table[it + 1, 1 : 1 + neq] = state

    for row in range(nt):
        if nglobal == 0:
            _call_model(
                func,
                table[row, 0],
                table[row, 1 : 1 + neq],
                names,
                ynames,
                parms,
                kwargs,
            )
        else:
            table[row, 1 + neq :] = globals_at(
                table[row, 0], table[row, 1 : 1 + neq]
            )

    steps = nt - 1
    istate = [None] * 21
    istate[0] = 0
    istate[1] = steps
    istate[2] = steps + 1
    istate[17] = 1
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
    return result
