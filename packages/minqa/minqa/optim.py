"""Derivative-free optimizers from minqa.

Rcpp is the compile bridge in the R package. It is not loaded. The search
itself is Powell's Fortran, ported in the bobyqa, newuoa, and uobyqa crates.
"""

from __future__ import annotations

import inspect
import math
import warnings
from collections.abc import Callable, Sequence


class MinqaResult:
    """The list R returns, with classes ``(method, "minqa")``."""

    def __init__(self, par, fval, feval, ierr, msg, kind: str):
        self.par = par
        self.fval = fval
        self.feval = feval
        self.ierr = ierr
        self.msg = msg
        self.classes = (kind, "minqa")

    def __str__(self) -> str:
        estimates = ", ".join(_r_string(value) for value in self.par)
        return (
            f"parameter estimates: {estimates} \n"
            f"objective: {_r_string(self.fval)} \n"
            f"number of function evaluations: {self.feval} \n"
        )

    def __repr__(self) -> str:
        return str(self)


def _r_string(value: float) -> str:
    """A short form of R's ``toString`` for one double."""

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    text = format(value, ".15g")
    if "e" in text or "E" in text:
        mantissa, exponent = text.lower().split("e")
        return f"{mantissa}e{int(exponent):+03d}"
    return text


def _as_float_vector(value, name: str) -> list[float]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"Argument `{name}` must be numeric")
        return [float(value)]
    out = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise TypeError(f"Argument `{name}` must be numeric")
        out.append(float(item))
    return out


def _require_function(fn) -> None:
    if not callable(fn):
        raise ValueError("is.function(fn) is not TRUE")
    try:
        parameters = list(inspect.signature(fn).parameters.values())
    except (TypeError, ValueError):
        return
    positional = [
        item
        for item in parameters
        if item.kind in (item.POSITIONAL_ONLY, item.POSITIONAL_OR_KEYWORD, item.VAR_POSITIONAL)
    ]
    if not positional:
        raise ValueError("length(formals(fn)) >= 1 is not TRUE")


def _trunc(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ValueError("NAs in control are not allowed")
    return int(float(value))


def _control(par: list[float], control: dict | None) -> dict:
    n = len(par)
    supplied = {} if control is None else dict(control)
    extra = [key for key in supplied if key not in {
        "npt", "rhobeg", "rhoend", "iprint", "maxfun", "obstop", "force.start", "force_start",
    }]
    if extra:
        warnings.warn("unused control arguments ignored", UserWarning, stacklevel=3)
    npt = supplied.get("npt", min(n + 2, 2 * n))
    rhobeg = supplied.get("rhobeg", None)
    rhoend = supplied.get("rhoend", None)
    iprint = supplied.get("iprint", 0)
    maxfun = supplied.get("maxfun", 10000)
    obstop = supplied.get("obstop", True)
    if "force.start" in supplied:
        force_start = supplied["force.start"]
    else:
        force_start = supplied.get("force_start", False)
    npt = _trunc(npt)
    npt = max(n + 2, min(npt, ((n + 1) * (n + 2)) // 2))
    if npt > 2 * n + 1:
        warnings.warn(
            "Setting npt > 2 * length(par) + 1 is not recommended.",
            UserWarning,
            stacklevel=3,
        )
    if rhobeg is None:
        rhobeg = min(0.95, 0.2 * max(abs(value) for value in par))
    else:
        rhobeg = float(rhobeg)
    if rhoend is None:
        rhoend = 1.0e-6 * rhobeg
    else:
        rhoend = float(rhoend)
    if not (0 < rhoend):
        raise ValueError("0 < ctrl$rhoend is not TRUE")
    if not (rhoend <= rhobeg):
        raise ValueError("ctrl$rhoend <= ctrl$rhobeg is not TRUE")
    maxfun = _trunc(maxfun)
    if maxfun < 10 * n * n:
        warnings.warn(
            "maxfun < 10 * length(par)^2 is not recommended.",
            UserWarning,
            stacklevel=3,
        )
    if obstop is not True and obstop is not False:
        raise ValueError("obstop must be TRUE or FALSE")
    if force_start is not True and force_start is not False:
        raise ValueError("force.start must be TRUE or FALSE")
    return {
        "npt": npt,
        "rhobeg": rhobeg,
        "rhoend": rhoend,
        "iprint": _trunc(iprint),
        "maxfun": maxfun,
        "obstop": obstop,
        "force.start": force_start,
    }


def _prepare(par, fn, control):
    values = _as_float_vector(par, "par")
    if not values or any(not math.isfinite(value) for value in values):
        raise ValueError("all(is.finite(par)) is not TRUE")
    _require_function(fn)
    return values, _control(values, control)


def _call(fn, par: list[float], extra: dict):
    if extra:
        value = fn(par, **extra)
    else:
        value = fn(par)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and len(value) > 1:
            raise ValueError("Objective function must return a single numeric value.")
        raise ValueError("Objective function must return a single numeric value.")
    return float(value)


def _bounds(lower, upper, n: int) -> tuple[list[float], list[float]]:
    lower_v = _as_float_vector(lower, "lower")
    upper_v = _as_float_vector(upper, "upper")
    if len(lower_v) == 1:
        lower_v = lower_v * n
    if len(upper_v) == 1:
        upper_v = upper_v * n
    if len(lower_v) != n:
        raise ValueError("length(lower) == n is not TRUE")
    if len(upper_v) != n:
        raise ValueError("length(upper) == n is not TRUE")
    if any(not (low < high) for low, high in zip(lower_v, upper_v)):
        raise ValueError("all(lower < upper) is not TRUE")
    return lower_v, upper_v


def _message(kind: str, ierr: int) -> tuple[int, str | None]:
    table = {
        "bobyqa": {
            10: (2, "bobyqa -- NPT is not in the required interval"),
            320: (5, "bobyqa detected too much cancellation in denominator"),
            390: (1, "bobyqa -- maximum number of function evaluations exceeded"),
            430: (3, "bobyqa -- a trust region step failed to reduce q"),
            20: (4, "bobyqa -- one of the box constraint ranges is too small (< 2*RHOBEG)"),
        },
        "newuoa": {
            10: (2, "newuoa -- NPT is not in the required interval"),
            320: (5, "newuoa detected too much cancellation in denominator"),
            390: (1, "newuoa -- maximum number of function evaluations exceeded"),
            3701: (3, "newuoa -- a trust region step failed to reduce q"),
        },
        "uobyqa": {
            390: (1, "uobyqa -- maximum number of function evaluations exceeded"),
            2101: (3, "uobyqa -- a trust region step failed to reduce q"),
        },
    }
    if ierr <= 0:
        return 0, f"Normal exit from {kind}"
    mapped = table[kind].get(ierr)
    if mapped is None:
        return ierr, None
    return mapped


def bobyqa(par, fn: Callable, lower=-math.inf, upper=math.inf, control=None, **kwargs):
    """Minimize ``fn`` inside box bounds with Powell's BOBYQA."""

    import bobyqa as engine

    values, ctrl = _prepare(par, fn, control)
    _call(fn, values, kwargs)
    n = len(values)
    lower_v, upper_v = _bounds(lower, upper, n)
    outside = [value < low or value > high for value, low, high in zip(values, lower_v, upper_v)]
    if any(outside):
        if ctrl["obstop"]:
            raise ValueError("Starting values violate bounds")
        values = [max(low, max(value, high)) for value, low, high in zip(values, lower_v, upper_v)]
        warnings.warn("Some parameters adjusted to nearest bound", UserWarning, stacklevel=2)
    span = [high - low for low, high in zip(lower_v, upper_v)]
    if any(width < 2 * ctrl["rhobeg"] for width in span):
        warnings.warn(
            "All upper - lower must be >= 2*rhobeg. Changing rhobeg",
            UserWarning,
            stacklevel=2,
        )
        ctrl["rhobeg"] = 0.2 * min(span)
    if (
        all(math.isfinite(value) for value in upper_v)
        and all(math.isfinite(value) for value in lower_v)
        and all(value >= low for value, low in zip(values, lower_v))
        and all(value <= high for value, high in zip(values, upper_v))
        and not ctrl["force.start"]
    ):
        close = [width < ctrl["rhobeg"] for width in span]
        if any(close):
            values = [
                low + ctrl["rhobeg"] if flag else value
                for value, low, flag in zip(values, lower_v, close)
            ]
            warnings.warn("Some parameters adjusted away from lower bound", UserWarning, stacklevel=2)
        if any(close):
            values = [
                high - ctrl["rhobeg"] if flag else value
                for value, high, flag in zip(values, upper_v, close)
            ]
            warnings.warn("Some parameters adjusted away from upper bound", UserWarning, stacklevel=2)

    def objective(point):
        return _call(fn, list(point), kwargs)

    updated, ierr, _nfev = engine.solve(
        values,
        lower_v,
        upper_v,
        int(ctrl["npt"]),
        float(ctrl["rhobeg"]),
        float(ctrl["rhoend"]),
        int(ctrl["iprint"]),
        int(ctrl["maxfun"]),
        objective,
    )
    code, msg = _message("bobyqa", ierr)
    return MinqaResult(list(updated), objective(updated), _nfev, code, msg, "bobyqa")


def newuoa(par, fn: Callable, control=None, **kwargs):
    """Minimize ``fn`` without bounds with Powell's NEWUOA."""

    import newuoa as engine

    values, ctrl = _prepare(par, fn, control)
    _call(fn, values, kwargs)

    def objective(point):
        return _call(fn, list(point), kwargs)

    updated, ierr, nfev = engine.solve(
        values,
        int(ctrl["npt"]),
        float(ctrl["rhobeg"]),
        float(ctrl["rhoend"]),
        int(ctrl["iprint"]),
        int(ctrl["maxfun"]),
        objective,
    )
    code, msg = _message("newuoa", ierr)
    return MinqaResult(list(updated), objective(updated), nfev, code, msg, "newuoa")


def uobyqa(par, fn: Callable, control=None, **kwargs):
    """Minimize ``fn`` without bounds with Powell's UOBYQA."""

    import uobyqa as engine

    values, ctrl = _prepare(par, fn, control)
    _call(fn, values, kwargs)

    def objective(point):
        return _call(fn, list(point), kwargs)

    updated, ierr, nfev = engine.solve(
        values,
        float(ctrl["rhobeg"]),
        float(ctrl["rhoend"]),
        int(ctrl["iprint"]),
        int(ctrl["maxfun"]),
        objective,
    )
    code, msg = _message("uobyqa", ierr)
    return MinqaResult(list(updated), objective(updated), nfev, code, msg, "uobyqa")
