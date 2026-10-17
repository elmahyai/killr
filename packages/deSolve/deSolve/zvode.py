"""Variable-coefficient ODE integrator for complex state (deSolve ``zvode``)."""

from __future__ import annotations

import sys

import numpy as np

from deSolve.rk4 import (
    DeSolveMatrix,
    _as_times,
    _call_model,
    _globals_of,
    _lengthvar,
    _reject_compiled,
    _split_return,
    _unlist_names,
    _unpack_model,
    _derivative_error,
)

try:
    from zvode import integrate_zvode
except ImportError:  # pragma: no cover
    integrate_zvode = None

_ALLOWED_MF = frozenset(
    list(range(10, 18)) + list(range(20, 28)) + [-11, -12, -14, -15, -21, -22, *range(-27, -23, -1)]
)

_ISTATE_IN = (0, *range(11, 23))
_ISTATE_OUT = tuple(range(13))


def _as_y_complex(y):
    if isinstance(y, dict):
        if any(isinstance(key, (bool, np.bool_)) for key in y):
            raise ValueError("`y' must be numeric")
        names = [str(key) for key in y.keys()]
        try:
            values = np.array(list(y.values()), dtype=np.complex128)
        except (TypeError, ValueError):
            raise ValueError("`y' must be numeric") from None
        return values.reshape(-1), names
    try:
        array = np.asarray(y)
    except (TypeError, ValueError) as exc:
        raise ValueError("`y' must be numeric") from exc
    if array.dtype.kind != "c":
        raise ValueError("'y' should be complex, not real")
    return np.ravel(array).astype(np.complex128, copy=True), None


def _check_input(y, times, func, rtol, atol, jacfunc, tcrit, hmin, hmax, hini, dllname):
    values, _ = _as_y_complex(y)
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


def _component_complex(value):
    if value is None:
        return np.zeros(0, dtype=np.complex128), None, None
    if isinstance(value, dict):
        names = [str(key) for key in value.keys()]
        try:
            data = np.array(list(value.values()), dtype=np.complex128)
        except (TypeError, ValueError) as exc:
            raise ValueError("Model function must return a list\n") from exc
        return data.reshape(-1), names, None
    if isinstance(value, (str, bytes, bool, np.bool_)):
        raise ValueError("Model function must return a list\n")
    try:
        array = np.asarray(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("Model function must return a list\n") from exc
    if array.dtype.kind != "c":
        raise ValueError("derivatives (first element returned by 'func') should be complex, not real")
    shape = tuple(int(dim) for dim in array.shape) if array.ndim >= 2 else None
    data = np.ravel(array, order="F").astype(np.complex128, copy=True)
    return data, None, shape


def _split_return_complex(result):
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
    components = [_component_complex(element) for element in elements]
    return parents, components


def _check_func_complex(func2, times, y, ynames, names):
    if not np.iscomplexobj(y):
        raise ValueError("'y' should be complex, not real")
    state = y
    if ynames and names is not None:
        state = np.array(y, dtype=np.complex128, copy=True)
    returned = _split_return_complex(func2(times[0], state))
    parents, components = returned
    got = len(components[0][0])
    neq = len(y)
    if got != neq:
        _derivative_error(got, neq)
    if components[0][0].dtype.kind != "c":
        raise ValueError("derivatives (first element returned by 'func') should be complex, not real")
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


def _call_model_complex(func, time, values, names, ynames, parms, kwargs):
    if ynames and names is not None:
        state = np.array(values, dtype=np.complex128, copy=True)
        state = _NamedComplexState(state, names)
    else:
        state = np.asarray(values, dtype=np.complex128)
    return func(float(time), state, parms, **kwargs)


class _NamedComplexState(np.ndarray):
    """Complex state vector with optional string names."""

    def __new__(cls, values, names):
        obj = np.array(values, dtype=np.complex128, copy=True).reshape(-1).view(cls)
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


def _set_istate(raw: list[int]) -> list:
    out = [None] * 21
    for iout, iin in zip(_ISTATE_OUT, _ISTATE_IN):
        out[iout] = raw[iin] if iin < len(raw) else None
    return out


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
    result.type = "cvode"
    result.rstate = list(rstate)
    return result


def zvode(
    y,
    times,
    func,
    parms,
    rtol=1e-6,
    atol=1e-6,
    jacfunc=None,
    jactype="fullint",
    mf=None,
    verbose=False,
    tcrit=None,
    hmin=0,
    hmax=None,
    hini=0,
    ynames=True,
    maxord=None,
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
    **kwargs,
):
    """Integrate complex ``y' = func(t, y, parms)`` with the Livermore ZVODE method."""
    if integrate_zvode is None:
        raise ImportError("zvode extension is not built")

    if initfunc is None:
        initfunc = dllname
    if initpar is None:
        initpar = parms

    func, initfunc, dllname, initforc = _unpack_model(func, initfunc, dllname, initforc)
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

    values, names = _as_y_complex(y)
    grid = _as_times(times)
    if len(grid) == 0:
        raise ValueError("`times' must be NULL or numeric")
    n = len(values)

    hmax = _check_input(y, times, func, rtol, atol, jacfunc, tcrit, hmin, hmax, hini, dllname)

    if maxord is not None and maxord < 1:
        raise ValueError("`maxord' must be >1")

    if mf is None:
        if jactype == "fullint":
            imp = 22
        elif jactype == "fullusr":
            imp = 21
        elif jactype == "bandusr":
            imp = 24
        elif jactype == "bandint":
            imp = 25
        else:
            raise ValueError(
                "'jactype' must be one of 'fullint', 'fullusr', 'bandusr' or 'bandint' if 'mf' not specified"
            )
    else:
        imp = int(mf)

    if imp not in _ALLOWED_MF:
        raise ValueError("method flag 'mf' not allowed")

    miter = abs(imp) % 10
    if miter in (1, 4) and jacfunc is None:
        raise ValueError(
            "'jacfunc' NOT specified; either specify 'jacfunc' or change 'jactype' or 'mf'"
        )

    meth = abs(imp) // 10
    if maxord is None:
        maxord = 12 if meth == 1 else 5
    if meth == 1 and maxord > 12:
        raise ValueError("'maxord' too large: should be <= 12")
    if meth == 2 and maxord > 5:
        raise ValueError("'maxord' too large: should be <= 5")
    if miter in (4, 5) and bandup is None:
        raise ValueError("'bandup' must be specified if banded Jacobian")
    if miter in (4, 5) and banddown is None:
        raise ValueError("'banddown' must be specified if banded Jacobian")
    if banddown is None:
        banddown = 1
    if bandup is None:
        bandup = 1

    def func2(time, state):
        return _call_model_complex(func, time, state, names, ynames, parms, kwargs)

    nglobal, nmtot, components = _check_func_complex(func2, grid, values, ynames, names)

    state0 = (
        _NamedComplexState(values, names)
        if ynames and names is not None
        else np.asarray(values, dtype=np.complex128)
    )
    if miter in (1, 4):
        if jacfunc is None:
            raise ValueError("Jacobian function must return a matrix\n")

        def jac_wrapped(time, state):
            mat = jacfunc(float(time), state, parms, **kwargs)
            return np.asarray(mat, dtype=np.complex128)

        jac_test = jac_wrapped(grid[0], state0)
        if jac_test.ndim != 2:
            raise ValueError("Jacobian function must return a matrix\n")
        dd = jac_test.shape
        if (miter == 4 and dd != (bandup + banddown + banddown + 1, n)) or (
            miter == 1 and dd != (n, n)
        ):
            raise ValueError("Jacobian dimension not ok")
        jac_py = jac_wrapped
    else:
        jac_py = None

    rtol_scalar = float(np.asarray(rtol, dtype=np.float64).reshape(-1)[0])
    atol_scalar = float(np.asarray(atol, dtype=np.float64).reshape(-1)[0])

    def deriv_for_rust(t, y_arr):
        state = y_arr
        if ynames and names is not None:
            state = _NamedComplexState(np.asarray(y_arr, dtype=np.complex128), names)
        out = _split_return_complex(
            _call_model_complex(func, float(t), state, names, ynames, parms, kwargs)
        )[1][0][0]
        return list(out)

    table, istate_raw, rstate = integrate_zvode(
        np.asarray(values, dtype=np.complex128),
        np.asarray(grid, dtype=np.float64),
        deriv_for_rust,
        mf=imp,
        rtol=rtol_scalar,
        atol=atol_scalar,
        maxord=int(maxord),
        maxsteps=int(maxsteps),
        banddown=int(banddown),
        bandup=int(bandup),
        hini=float(hini or 0.0),
        hmax=float(hmax),
        hmin=float(hmin),
        tcrit=float(tcrit) if tcrit is not None else None,
        jacfunc=jac_py,
    )

    table = np.asarray(table, dtype=np.complex128)
    table[0, 0] = grid[0] + 0.0j

    if nglobal > 0:
        for row in range(table.shape[0]):
            t = float(np.real(table[row, 0]))
            st = table[row, 1 : 1 + n]
            state = _NamedComplexState(st, names) if ynames and names else st
            comps = _split_return_complex(
                _call_model_complex(func, t, state, names, ynames, parms, kwargs)
            )[1]
            table[row, 1 + n :] = _globals_of(comps)

    result = _save_out(table, names, n, nglobal, nmtot, istate_raw, rstate)
    if verbose:
        sys.stdout.write(f"zvode completed with istate[0] = {istate_raw[0]}\n")
    return result
