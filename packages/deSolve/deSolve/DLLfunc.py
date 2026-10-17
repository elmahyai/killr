"""Evaluate a compiled derivative in a DLL (deSolve ``DLLfunc.R`` / ``call_DLL``)."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import numpy as np

try:
    from aquaphy import aquaphy_eval_py as _aquaphy_eval
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "aquaphy"))
    from aquaphy import aquaphy_eval_py as _aquaphy_eval

def _ccl4():
    try:
        from ccl4model import derivs_ccl4, init_ccl4
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "ccl4model"))
        from ccl4model import derivs_ccl4, init_ccl4
    return derivs_ccl4, init_ccl4


def _as_double_vector(x, name: str) -> np.ndarray:
    arr = np.asarray(x)
    if not np.issubdtype(arr.dtype, np.number):
        raise TypeError(f"`{name}' must be numeric")
    return np.asarray(arr, dtype=np.float64).reshape(-1)


def _func_name(func: Any) -> str:
    if isinstance(func, str):
        return func
    raise TypeError(
        "`func' must be a *name* referring to a function in a dll or of class CFunc"
    )


def _resolve_list_func(
    func,
    dllname,
    initfunc,
    initforc,
) -> tuple[Any, str | None, Any, Any]:
    if not isinstance(func, dict):
        return func, dllname, initfunc, initforc
    if dllname is not None and "dllname" in func:
        raise ValueError(
            "If 'func' is a list that contains dllname, argument 'dllname' should be NULL"
        )
    if initfunc is not None and "initfunc" in func:
        raise ValueError(
            "If 'func' is a list that contains initfunc, argument 'initfunc' should be NULL"
        )
    if initforc is not None and "initforc" in func:
        raise ValueError(
            "If 'func' is a list that contains initforc, argument 'initforc' should be NULL"
        )
    if func.get("initfunc") is not None:
        initfunc = func["initfunc"]
    if func.get("initforc") is not None:
        initforc = func["initforc"]
    if func.get("dllname") is not None:
        dllname = func["dllname"]
    return func.get("func"), dllname, initfunc, initforc


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


def _call_desolve_deriv(
    func: str,
    initfunc: Any,
    tin: float,
    y: np.ndarray,
    parms: np.ndarray,
    nout: int,
    forcings,
) -> tuple[np.ndarray, np.ndarray | None]:
    if func == "aquaphy":
        result = _aquaphy_eval(tin, y, parms, par=None)
        dy = np.asarray(result["delta"], dtype=np.float64).reshape(-1)
        var = np.asarray(result["var"], dtype=np.float64).reshape(-1)
        if nout > 0 and var.size != nout:
            var = var[:nout]
        return dy, var if nout > 0 else None

    if func == "derivsccl4":
        derivs_ccl4, init_ccl4 = _ccl4()
        if initfunc in ("initccl4",):
            init_ccl4(parms)
        elif initfunc not in (None, "deSolve", "ccl4model"):
            raise RuntimeError(f"cannot integrate: initfunc not loaded {initfunc}")
        ydot, out = derivs_ccl4(tin, y)
        dy = np.asarray(ydot, dtype=np.float64).reshape(-1)
        var = np.asarray(out, dtype=np.float64).reshape(-1)
        if nout > 0 and var.size != nout:
            var = var[:nout]
        return dy, var if nout > 0 else None

    raise RuntimeError(f"cannot run DLLfunc: dyn function not loaded: {func}")


def DLLfunc(
    func,
    times,
    y,
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
    """Call a compiled ODE derivative once (deSolve ``DLLfunc``)."""
    del rpar, ipar, fcontrol

    if initfunc is None:
        initfunc = dllname

    func, dllname, initfunc, _initforc = _resolve_list_func(
        func, dllname, initfunc, initforc
    )

    y_vec = _state_vector(y)
    n = y_vec.size
    y_names = _y_names(y)

    parms_vec = _as_double_vector(parms, "parms")

    if times is not None and not np.issubdtype(np.asarray(times).dtype, np.number):
        raise TypeError("`times' must be NULL or numeric")

    if outnames is not None and len(outnames) != int(nout):
        raise ValueError("length outnames should be = nout")

    if hasattr(func, "__class__") and func.__class__.__name__ == "CFunc":
        raise TypeError(
            "`func' must be a *name* referring to a function in a dll or of class CFunc"
        )

    if dllname is None or not isinstance(dllname, str):
        raise ValueError("`dllname' must be a name referring to a dll")

    func_name = _func_name(func)

    if dllname != "deSolve":
        raise RuntimeError(f"cannot run DLLfunc: dyn function not loaded: {func_name}")

    tin = _time_value(times)
    if forcings is not None or _initforc is not None:
        raise NotImplementedError(
            "DLLfunc with forcings requires checkforcings, which is not translated"
        )

    dy, var = _call_desolve_deriv(
        func_name,
        initfunc,
        tin,
        y_vec,
        parms_vec,
        int(nout),
        None,
    )

    result: dict[str, Any] = {
        "dy": dy,
        "var": np.nan if var is None else var,
    }
    names: dict[str, list[str]] = {}
    if y_names is not None and len(y_names) == n:
        names["dy"] = y_names
    if outnames is not None and var is not None:
        names["var"] = list(outnames)
    if names:
        result["names"] = names
    return result
