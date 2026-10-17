"""Binary search over a monotonic integer parameter (gtools 3.9.5 ``binsearch``)."""

from __future__ import annotations

import math
import warnings
from typing import Any, Callable

import numpy as np


def _range_bounds(range_) -> tuple[float, float]:
    values = np.asarray(range_, dtype=np.float64).ravel()
    if values.size == 0:
        raise ValueError("invalid 'range' argument")
    return float(np.min(values)), float(np.max(values))


def binsearch(
    fun: Callable[..., float],
    range_,
    /,
    *args: Any,
    target: float = 0,
    lower: float | None = None,
    upper: float | None = None,
    maxiter: int = 100,
    showiter: bool = False,
) -> dict[str, Any]:
    """Search ``range`` for an integer where monotonic ``fun`` meets ``target``."""
    rmin, rmax = _range_bounds(range_)
    if lower is None:
        lower_lim = math.ceil(rmin)
    else:
        lower_lim = float(lower)
    if upper is None:
        upper_lim = math.floor(rmax)
    else:
        upper_lim = float(upper)
    lo = lower_lim
    hi = upper_lim

    counter = 0
    val_lo = float(fun(lo, *args))
    val_hi = float(fun(hi, *args))

    if val_lo > val_hi:
        sign = -1
    else:
        sign = 1

    if target * sign < val_lo * sign or target * sign > val_hi * sign:
        outside_range = True
    else:
        outside_range = False

    while counter < maxiter and not outside_range:
        counter += 1

        if hi - lo <= 1 or lo < lower_lim or hi > upper_lim:
            break

        center = round((hi - lo) / 2 + lo)
        val = float(fun(center, *args))

        if showiter:
            print("--------------")
            print(f"Iteration # {counter} ")
            print(f"lo= {lo} ")
            print(f"hi= {hi} ")
            print(f"center= {center} ")
            print(f"fun(lo)= {val_lo} ")
            print(f"fun(hi)= {val_hi} ")
            print(f"fun(center)= {val} ")

        if val == target:
            val_lo = val_hi = val
            lo = hi = center
            break
        if sign * val < sign * target:
            lo = center
            val_lo = val
        else:
            hi = center
            val_hi = val

        if showiter:
            print(f"new lo= {lo} ")
            print(f"new hi= {hi} ")
            print("--------------")

    retval: dict[str, Any] = {
        "call": None,
        "numiter": counter,
    }

    if outside_range:
        if target * sign < val_lo * sign:
            warnings.warn("Reached lower boundary", RuntimeWarning, stacklevel=2)
            retval["flag"] = "Lower Boundary"
            retval["where"] = lo
            retval["value"] = val_lo
        else:
            warnings.warn("Reached upper boundary", RuntimeWarning, stacklevel=2)
            retval["flag"] = "Upper Boundary"
            retval["where"] = hi
            retval["value"] = val_hi
    elif counter >= maxiter:
        warnings.warn("Maximum number of iterations reached", RuntimeWarning, stacklevel=2)
        retval["flag"] = "Maximum number of iterations reached"
        retval["where"] = np.array([lo, hi], dtype=np.float64)
        retval["value"] = np.array([val_lo, val_hi], dtype=np.float64)
    elif val_lo == target:
        retval["flag"] = "Found"
        retval["where"] = lo
        retval["value"] = val_lo
    elif val_hi == target:
        retval["flag"] = "Found"
        retval["where"] = hi
        retval["value"] = val_hi
    else:
        retval["flag"] = "Between Elements"
        retval["where"] = np.array([lo, hi], dtype=np.float64)
        retval["value"] = np.array([val_lo, val_hi], dtype=np.float64)

    return retval
