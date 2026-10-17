"""Evaluate a compiled DAE residual in a DLL (deSolve ``DLLfunc.R`` ``DLLres`` / ``call_DLL`` type 2)."""

from __future__ import annotations

from typing import Any, Callable

import numpy as np


def _as_double_vector(x, name: str) -> np.ndarray:
    arr = np.asarray(x)
    if not np.issubdtype(arr.dtype, np.number):
        raise TypeError(f"`{name}' must be numeric")
    return np.asarray(arr, dtype=np.float64).reshape(-1)


def _time_value(times) -> float:
    if times is None:
        return 0.0
    arr = np.asarray(times, dtype=np.float64).reshape(-1)
    if arr.size == 0:
        return 0.0
    return float(arr[0])


def _y_names(y) -> list[str] | None:
    if isinstance(y, dict):
        return list(y.keys())
    names = getattr(y, "names", None)
    if names is not None:
        return list(names)
    return None


def _state_vector(y) -> np.ndarray:
    if isinstance(y, dict):
        return _as_double_vector(list(y.values()), "y")
    return _as_double_vector(y, "y")


class _ForcingState:
    __slots__ = ("tvec", "fvec", "fmethod", "findex", "maxindex", "intpol")

    def __init__(self, tvec, fvec, fmethod):
        self.tvec = tvec
        self.fvec = fvec
        self.fmethod = fmethod
        self.findex = 0
        self.maxindex = len(tvec) - 2
        self.intpol = 0.0
        if fmethod == 1 and len(tvec) > 1:
            self.intpol = (fvec[1] - fvec[0]) / (tvec[1] - tvec[0])

    def value_at(self, time: float) -> float:
        tvec = self.tvec
        fvec = self.fvec
        ii = self.findex
        zerograd = False
        while time > tvec[ii + 1]:
            if ii + 2 > self.maxindex:
                zerograd = True
                break
            ii += 1
        while time < tvec[ii]:
            ii -= 1
        if ii != self.findex:
            self.findex = ii
            if not zerograd and self.fmethod == 1:
                self.intpol = (fvec[ii + 1] - fvec[ii]) / (tvec[ii + 1] - tvec[ii])
            else:
                self.intpol = 0.0
        return fvec[ii] + self.intpol * (time - tvec[ii])


def _prepare_forcings(flux, times, fcontrol=None):
    con = {"method": "linear", "rule": 2, "f": 0, "ties": "ordered"}
    if fcontrol:
        con.update(fcontrol)
    method_names = ("linear", "constant")
    if con["method"] not in method_names:
        raise ValueError("invalid interpolation method for forcing functions")
    fmethod = method_names.index(con["method"]) + 1

    forcings = np.asarray(flux, dtype=np.float64)
    if forcings.ndim != 2 or forcings.shape[1] != 2:
        raise ValueError("forcing function data sets should consist of two-column matrix")
    forcings = forcings.copy()
    r_t = (float(np.min(times)), float(np.max(times)))
    t = forcings[:, 0]
    if t[0] > r_t[0]:
        if con["rule"] == 2:
            forcings = np.vstack([[r_t[0], forcings[0, 1]], forcings])
        else:
            raise ValueError("extrapolating forcing function data sets to first timepoint 1")
    if forcings[-1, 0] < r_t[1]:
        if con["rule"] == 2:
            forcings = np.vstack([forcings, [r_t[1], forcings[-1, 1]]])
        else:
            raise ValueError("extrapolating forcing function data sets to last timepoint 1")

    if con["ties"] != "ordered":
        x = forcings[:, 0]
        y = forcings[:, 1]
        ux = np.unique(x)
        if ux.size < x.size:
            y = np.array([y[x == xi].mean() for xi in ux])
            x = ux
        else:
            order = np.argsort(x)
            x = x[order]
            y = y[order]
        forcings = np.column_stack([x, y])

    if fmethod == 2 and con["f"] != 0:
        y = forcings[:, 1]
        yy = np.r_[y[1:], y[-1]]
        forcings[:, 1] = (1.0 - con["f"]) * y + con["f"] * yy

    return forcings[:, 0], forcings[:, 1], fmethod


def _resolve_list_res(
    res,
    dllname,
    initfunc,
    initforc,
) -> tuple[Any, str | None, Any, Any]:
    if not isinstance(res, dict):
        return res, dllname, initfunc, initforc
    if dllname is not None and "dllname" in res:
        raise ValueError(
            "If 'res' is a list that contains dllname, argument 'dllname' should be NULL"
        )
    if initfunc is not None and "initfunc" in res:
        raise ValueError(
            "If 'res' is a list that contains initfunc, argument 'initfunc' should be NULL"
        )
    if initforc is not None and "initforc" in res:
        raise ValueError(
            "If 'res' is a list that contains initforc, argument 'initforc' should be NULL"
        )
    if res.get("initfunc") is not None:
        initfunc = res["initfunc"]
    if res.get("initforc") is not None:
        initforc = res["initforc"]
    if res.get("dllname") is not None:
        dllname = res["dllname"]
    return res.get("res"), dllname, initfunc, initforc


def _res_name(res: Any) -> str:
    if isinstance(res, str):
        return res
    raise TypeError("`res' must be a *name* referring to a function in a dll")


def _is_cfunc(res: Any) -> bool:
    return hasattr(res, "__class__") and res.__class__.__name__ == "CFunc"


def _chemres_kernel(
    t: float,
    y: np.ndarray,
    dy: np.ndarray,
    parms: np.ndarray,
    prod: float,
    nout: int,
) -> tuple[np.ndarray, np.ndarray | None]:
    del t
    k = float(parms[0])
    ka = float(parms[1])
    r_rate = float(parms[2])
    ra = ka * y[2]
    rb = ka / k * y[0] * y[1]
    delta = np.array(
        [
            -dy[0] + ra - rb,
            -dy[1] + ra - rb - r_rate * y[1],
            -dy[2] - ra + rb + prod,
        ],
        dtype=np.float64,
    )
    if nout <= 0:
        return delta, None
    var = np.array([y[0] + y[1] + y[2], prod], dtype=np.float64)
    if nout < 2:
        raise RuntimeError("nout should be at least 2")
    if var.size != nout:
        var = var[:nout]
    return delta, var


def _call_py_res(
    res: Callable[..., Any],
    t: float,
    y: np.ndarray,
    dy: np.ndarray,
    parms: np.ndarray,
    prod: float | None,
    nout: int,
) -> tuple[np.ndarray, np.ndarray | None]:
    if prod is None:
        out = res(t, y, dy, parms)
    else:
        out = res(t, y, dy, parms, prod)
    if isinstance(out, dict):
        delta = _as_double_vector(out["delta"], "delta")
        var_raw = out.get("var")
        var = None if var_raw is None or nout <= 0 else _as_double_vector(var_raw, "var")
        return delta, var
    if isinstance(out, (tuple, list)) and len(out) == 2:
        delta = _as_double_vector(out[0], "delta")
        var = None if nout <= 0 else _as_double_vector(out[1], "var")
        return delta, var
    delta = _as_double_vector(out, "delta")
    return delta, None


def _call_desolve_res(
    res_name: str,
    t: float,
    y: np.ndarray,
    dy: np.ndarray,
    parms: np.ndarray,
    prod: float | None,
    nout: int,
) -> tuple[np.ndarray, np.ndarray | None]:
    if res_name == "chemres":
        if prod is None:
            prod = 0.0
        return _chemres_kernel(t, y, dy, parms, prod, nout)
    raise RuntimeError(f"cannot run DLLres: res function not loaded: {res_name}")


def _forcing_prod(forcings, times, initforc, dllname, fcontrol) -> float | None:
    if forcings is None:
        return None
    if initforc is None:
        raise ValueError("initforc must be specified if forcings are given")
    del initforc, dllname
    tvec, fvec, fmethod = _prepare_forcings(forcings, np.asarray([_time_value(times)]), fcontrol)
    state = _ForcingState(tvec, fvec, fmethod)
    return state.value_at(_time_value(times))


def DLLres(
    res,
    times,
    y,
    dy,
    parms,
    dllname,
    initfunc=None,
    rpar=None,
    ipar=None,
    nout=0,
    outnames=None,
    forcings=None,
    initforc=None,
    fcontrol=None,
):
    """Call a compiled DAE residual once (deSolve ``DLLres``)."""
    del rpar, ipar

    if initfunc is None:
        initfunc = dllname

    res, dllname, initfunc, initforc = _resolve_list_res(res, dllname, initfunc, initforc)

    y_vec = _state_vector(y)
    dy_vec = _as_double_vector(dy, "dy")
    n = y_vec.size
    if dy_vec.size != n:
        raise ValueError("`dy' and 'y' muxt hve the same length")

    y_names = _y_names(y)
    parms_vec = _as_double_vector(parms, "parms")

    if times is not None and not np.issubdtype(np.asarray(times).dtype, np.number):
        raise TypeError("`time' must be NULL or numeric")

    if outnames is not None and len(outnames) != int(nout):
        raise ValueError("length outnames should be = nout")

    tin = _time_value(times)
    prod = _forcing_prod(forcings, times, initforc, dllname, fcontrol)

    use_callable = callable(res) and not isinstance(res, str)
    if _is_cfunc(res):
        use_callable = True

    if use_callable:
        delta, var = _call_py_res(res, tin, y_vec, dy_vec, parms_vec, prod, int(nout))
    else:
        if dllname is None or not isinstance(dllname, str):
            raise ValueError("`dllname' must be a name referring to a dll")
        if dllname != "deSolve":
            raise RuntimeError(f"cannot run DLLres: res function not loaded: {_res_name(res)}")
        if initfunc not in (None, dllname, "initparms", "initforcs", "deSolve"):
            raise RuntimeError(f"cannot integrate: initfunc not loaded {initfunc}")
        res_name = _res_name(res)
        delta, var = _call_desolve_res(res_name, tin, y_vec, dy_vec, parms_vec, prod, int(nout))

    result: dict[str, Any] = {
        "delta": delta,
        "var": np.nan if var is None else var,
    }
    names: dict[str, list[str]] = {}
    if y_names is not None and len(y_names) == n:
        names["delta"] = y_names
    if outnames is not None and var is not None:
        names["var"] = list(outnames)
    if names:
        result["names"] = names
    return result
