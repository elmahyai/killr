"""Classical fourth-order Runge-Kutta with the step fixed by `times`.

The step is the difference of successive output times. There is no
interpolation and no event handling. Global values after the derivatives
are filled by a second pass over the stored rows, and that pass is not
added to the evaluation count.
"""

import sys
import warnings

import numpy as np

from deSolve.timestep import _advance_timestep, _reset_timesteps

_MISSING = object()

_WARN_HMIN = "hmin and hmax cannot be used in 'rk4' (fixed steps)."
_HINI = (
    "'hini' is not supported by this version of rk4,\n"
    "but you can use ode(......, method = 'rk4', hini= .....)\n"
    "to set internal time steps smaller than external steps.\n"
)
_WARN_EVENTS = (
    "events and roots are not supported by this version of rk4,\n"
    "  but you can use ode(......, method = 'rk4', .....)\n"
)
_WARN_JAC = (
    "Euler and Runge-Kutta solvers make no use of a Jacobian,\n"
    "  ('jacfunc', 'jactype', 'mf', 'bandup' and 'banddown' are ignored).\n"
)
_WARN_LAGS = (
    "lags are not yet implemented for Euler and Runge-Kutta solvers,\n"
    "  (argument 'lags' is ignored).\n"
)

_ISTATE_TEXT = (
    "The return code :",
    "The number of steps taken for the problem so far:",
    "The number of function evaluations for the problem so far:",
    "The number of Jacobian evaluations so far:",
    "The method order last used (successfully):",
    "The order of the method to be attempted on the next step:",
    "If return flag =-4,-5: the largest component in error vector",
    "The length of the real work array actually required:",
    "The length of the integer work array actually required:",
    "The number of matrix LU decompositions so far:",
    "The number of nonlinear (Newton) iterations so far:",
    "The number of convergence failures of the solver so far ",
    "The number of error test failures of the integrator so far:",
    "The number of Jacobian evaluations and LU decompositions so far:",
    "The method indicator for the last succesful step,\n           1=adams (nonstiff), 2= bdf (stiff):",
    "The current method indicator to be attempted on the next step,\n           1=adams (nonstiff), 2= bdf (stiff):",
    "The number of nonzero elements in the sparse Jacobian:",
    "The order (or maximum order) of the method:",
    "The number of convergence failures of the linear iteration so far",
    "The number of linear (Krylov) iterations so far ",
    "The number of psol calls so far:",
)


class State(np.ndarray):
    """State vector. An integer index is positional and a string index is a name."""

    def __new__(cls, values, names):
        base = np.array(values, dtype=np.float64, copy=True).reshape(-1)
        obj = base.view(cls)
        obj.names = None if names is None else [str(name) for name in names]
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        names = getattr(obj, "names", None)
        self.names = None if names is None else list(names)

    def __getitem__(self, key):
        if isinstance(key, str):
            if not self.names or key not in self.names:
                raise KeyError(key)
            return super().__getitem__(self.names.index(key))
        return super().__getitem__(key)


class DeSolveMatrix:
    """Matrix of class deSolve, one row per output time."""

    def __init__(self, data, colnames, istate, lengthvar, lengthvar_names, dimvar):
        self.data = data
        self.colnames = list(colnames)
        self.istate = istate
        self.lengthvar = lengthvar
        self.lengthvar_names = lengthvar_names
        self.dimvar = dimvar
        self.type = "rk"

    def __str__(self):
        width = 14
        header = "".join(f"{name:>{width}}" for name in self.colnames)
        lines = [" " * 4 + header]
        for index in range(self.data.shape[0]):
            cells = "".join(f"{value:14.7g}" for value in self.data[index])
            lines.append(f"{index + 1:4d}{cells}")
        return "\n".join(lines)


def _numeric_vector(value, message):
    if isinstance(value, (bool, np.bool_, str, bytes, dict)):
        raise ValueError(message)
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(message) from exc
    if array.dtype.kind not in "iuf":
        raise ValueError(message)
    return np.ravel(array, order="F").astype(np.float64, copy=True)


def _as_y(y):
    if isinstance(y, dict):
        if any(isinstance(key, (bool, np.bool_)) for key in y):
            raise ValueError("`y' must be numeric")
        names = [str(key) for key in y.keys()]
        try:
            values = _numeric_vector(list(y.values()), "`y' must be numeric")
        except ValueError:
            raise ValueError("`y' must be numeric") from None
        return values, names
    if isinstance(y, State):
        return np.array(y, dtype=np.float64, copy=True).reshape(-1), (
            None if y.names is None else list(y.names)
        )
    return _numeric_vector(y, "`y' must be numeric"), None


def _as_times(times):
    return _numeric_vector(times, "`times' must be NULL or numeric")


def _unpack_model(func, initfunc, dllname, initforc):
    if not isinstance(func, dict):
        return func, initfunc, dllname, initforc
    if "initfunc" in func and initfunc is not None:
        raise ValueError(
            "If 'func' is a list that contains initfunc, argument 'initfunc' should be NULL"
        )
    if "dllname" in func and dllname is not None:
        raise ValueError(
            "If 'func' is a list that contains dllname, argument 'dllname' should be NULL"
        )
    if "initforc" in func and initforc is not None:
        raise ValueError(
            "If 'func' is a list that contains initforc, argument 'initforc' should be NULL"
        )
    if func.get("initfunc") is not None:
        initfunc = func["initfunc"]
    if func.get("dllname") is not None:
        dllname = func["dllname"]
    if func.get("initforc") is not None:
        initforc = func["initforc"]
    return func.get("func"), initfunc, dllname, initforc


def _reject_compiled(func, dllname):
    if isinstance(func, str):
        if not isinstance(dllname, str):
            raise ValueError(
                "You need to specify the name of the dll or shared library "
                "where func can be found (without extension)"
            )
        raise ValueError(f"dyn function 'func' not loaded {func}")
    if not callable(func):
        raise ValueError("`func' must be a function or character vector")


def _warn_unsupported(kwargs):
    names = set(kwargs)
    if "hmin" in names or "hmax" in names:
        warnings.warn(_WARN_HMIN, stacklevel=3)
    if "hini" in names:
        sys.stdout.write(_HINI)
    if "events" in names or "rootfunc" in names:
        warnings.warn(_WARN_EVENTS, stacklevel=3)
    if names.intersection(("jacfunc", "jactype", "mf", "bandup", "banddown")):
        warnings.warn(_WARN_JAC, stacklevel=3)
    if "lags" in names:
        warnings.warn(_WARN_LAGS, stacklevel=3)


def _component(value):
    """One element of the list returned by the model, flattened down columns."""
    if value is None:
        return np.zeros(0, dtype=np.float64), None, None
    if isinstance(value, dict):
        names = [str(key) for key in value.keys()]
        try:
            data = np.array(list(value.values()), dtype=np.float64)
        except (TypeError, ValueError) as exc:
            raise ValueError("Model function must return a list\n") from exc
        return data.reshape(-1), names, None
    if isinstance(value, (str, bytes, bool, np.bool_)):
        raise ValueError("Model function must return a list\n")
    if isinstance(value, State):
        data = np.array(value, dtype=np.float64, copy=True).reshape(-1)
        names = None if value.names is None else list(value.names)
        return data, names, None
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Model function must return a list\n") from exc
    if array.dtype.kind not in "iuf":
        raise ValueError("Model function must return a list\n")
    shape = tuple(int(dim) for dim in array.shape) if array.ndim >= 2 else None
    data = np.ravel(array, order="F").astype(np.float64, copy=True)
    return data, None, shape


def _split_return(result):
    if isinstance(result, dict):
        parents = [str(key) for key in result.keys()]
        elements = list(result.values())
    elif isinstance(result, (list, tuple)):
        parents = None
        elements = list(result)
    else:
        raise ValueError("Model function must return a list\n")
    if not elements:
        raise ValueError("Model function must return a list\n")
    components = [_component(element) for element in elements]
    return parents, components


def _derivative_error(got, expected):
    raise ValueError(
        "The number of derivatives returned by func() ("
        f"{got}must equal the length of the initial conditions vector ({expected})"
    )


def _unlist_names(extras, parents):
    collected = []
    saw = False
    for index, (data, inner, _shape) in enumerate(extras):
        length = len(data)
        if length == 0:
            continue
        parent = "" if parents is None else parents[index]
        if inner:
            saw = True
            if parent:
                collected.extend(
                    f"{parent}.{name}" if name else f"{parent}{offset + 1}"
                    for offset, name in enumerate(inner)
                )
            else:
                collected.extend("" if name is None else name for name in inner)
        elif parent:
            saw = True
            if length == 1:
                collected.append(parent)
            else:
                collected.extend(f"{parent}{offset + 1}" for offset in range(length))
        else:
            collected.extend([""] * length)
    if not saw:
        return None
    return collected


def _call_model(func, time, values, names, ynames, parms, kwargs):
    if ynames and names is not None:
        state = State(values, names)
    else:
        state = np.array(values, dtype=np.float64, copy=True).reshape(-1)
    return func(float(time), state, parms, **kwargs)


def _globals_of(components):
    pieces = []
    for data, _inner, _shape in components[1:]:
        if len(data):
            pieces.append(data)
    if not pieces:
        return np.zeros(0, dtype=np.float64)
    return np.concatenate(pieces)


def _lengthvar(components, parents):
    lengths = [int(len(data)) for data, _inner, _shape in components]
    if parents is None:
        return lengths, None
    return lengths, list(parents)


def _dimvar(components, nglobal):
    if len(components) >= nglobal + 1:
        return None
    dims = [shape for _data, _inner, shape in components[1:] if shape is not None]
    if not dims:
        return None
    return dims


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


def rk4(
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
    """Integrate `y' = func(t, y, parms)` with classical Runge-Kutta of order 4.

    `times` supplies every output point, and the first value is the
    initial time. The return is one row per time. Column one is time,
    then the states, then any global values after the derivatives.
    """
    if initfunc is _MISSING:
        initfunc = dllname
    if initpar is _MISSING:
        initpar = parms

    func, initfunc, dllname, initforc = _unpack_model(func, initfunc, dllname, initforc)
    _warn_unsupported(kwargs)
    _reject_compiled(func, dllname)

    # Compiled models read rpar, ipar, nout, outnames, and forcings.
    # An R function ignores them, including a supplied nout.
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
        f1 = dt * deriv(t, state)
        stage = state + 0.5 * f1
        f2 = dt * deriv(t + 0.5 * dt, stage)
        stage = state + 0.5 * f2
        f3 = dt * deriv(t + 0.5 * dt, stage)
        stage = state + f3
        f4 = dt * deriv(t + dt, stage)
        state = state + (f1 + 2.0 * f2 + 2.0 * f3 + f4) / 6.0
        table[it + 1, 0] = t + dt
        table[it + 1, 1 : 1 + neq] = state

    # The stored rows are visited again so global outputs match the
    # accepted state. nglobal == 0 still evaluates the model and drops
    # the return value.
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
    istate[2] = steps * 4 + 1
    istate[17] = 4
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
