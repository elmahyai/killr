"""General ODE driver (deSolve ``ode``)."""

from __future__ import annotations

import numpy as np

from deSolve.rk4 import _as_y
from deSolve.rkMethod import RkMethod, rkMethod


_ALLOWED = (
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
    "bdf_d",
    "adams",
    "impAdams",
    "impAdams_d",
    "iteration",
)


def ode(y, times, func, parms, method="lsoda", **kwargs):
    """Integrate ODE systems (deSolve ``ode``)."""
    if method is None:
        method = "lsoda"

    if isinstance(method, (list, dict)) or isinstance(method, RkMethod):
        from deSolve.rk import rk

        if isinstance(method, dict):
            method = rkMethod(method)
        elif isinstance(method, str):
            method = rkMethod(method)
        elif not isinstance(method, RkMethod):
            raise TypeError("'method' should be given as string or as a list of class 'rkMethod'")
        return rk(y, times, func, parms, method=method, **kwargs)

    if callable(method):
        return method(y, times, func, parms, **kwargs)

    if not isinstance(method, str):
        raise TypeError("'method' should be given as string or as a list of class 'rkMethod'")
    if method not in _ALLOWED:
        raise ValueError(f"'{method}' is not a valid method; choose from {', '.join(_ALLOWED)}")

    values, _ = _as_y(y)
    is_complex = np.iscomplexobj(values)

    if is_complex:
        from deSolve.zvode import zvode

        if method == "vode":
            return zvode(y, times, func, parms, **kwargs)
        if method == "bdf":
            return zvode(y, times, func, parms, mf=22, **kwargs)
        if method == "bdf_d":
            return zvode(y, times, func, parms, mf=23, **kwargs)
        if method == "adams":
            return zvode(y, times, func, parms, mf=10, **kwargs)
        if method == "impAdams":
            return zvode(y, times, func, parms, mf=12, **kwargs)
        if method == "impAdams_d":
            return zvode(y, times, func, parms, mf=13, **kwargs)
        raise ValueError(f"'{method}' is not a valid method; choose from {', '.join(_ALLOWED)}")

    if method == "lsoda":
        from deSolve.lsoda import lsoda

        return lsoda(y, times, func, parms, **kwargs)
    if method == "vode":
        from deSolve.vode import vode

        return vode(y, times, func, parms, **kwargs)
    if method == "lsode":
        from deSolve.lsode import lsode

        return lsode(y, times, func, parms, **kwargs)
    if method == "lsodes":
        from deSolve.lsodes import lsodes

        return lsodes(y, times, func, parms, **kwargs)
    if method == "lsodar":
        from deSolve.lsodar import lsodar

        return lsodar(y, times, func, parms, **kwargs)
    if method == "daspk":
        from deSolve.daspk import daspk

        return daspk(y, times, func, parms, **kwargs)
    if method == "euler":
        from deSolve.rk import rk

        return rk(y, times, func, parms, method="euler", **kwargs)
    if method == "rk4":
        from deSolve.rk import rk

        return rk(y, times, func, parms, method="rk4", **kwargs)
    if method == "ode23":
        from deSolve.rk import rk

        return rk(y, times, func, parms, method="ode23", **kwargs)
    if method == "ode45":
        from deSolve.rk import rk

        return rk(y, times, func, parms, method="ode45", **kwargs)
    if method == "radau":
        from deSolve.radau import radau

        return radau(y, times, func, parms, **kwargs)
    if method == "bdf":
        from deSolve.lsode import lsode

        return lsode(y, times, func, parms, mf=22, **kwargs)
    if method == "bdf_d":
        from deSolve.lsode import lsode

        return lsode(y, times, func, parms, mf=23, **kwargs)
    if method == "adams":
        from deSolve.lsode import lsode

        return lsode(y, times, func, parms, mf=10, **kwargs)
    if method == "impAdams":
        from deSolve.lsode import lsode

        return lsode(y, times, func, parms, mf=12, **kwargs)
    if method == "impAdams_d":
        from deSolve.lsode import lsode

        return lsode(y, times, func, parms, mf=13, **kwargs)
    if method == "iteration":
        raise NotImplementedError("iteration is not yet translated for deSolve")

    raise ValueError(f"'{method}' is not a valid method; choose from {', '.join(_ALLOWED)}")
