"""Banded Jacobian ODE driver (deSolve ``ode.band``)."""

from __future__ import annotations

import numpy as np

from deSolve.rk4 import DeSolveMatrix, _as_y


def _attach_band_attrs(out: DeSolveMatrix, dimens: int, nspec: int, names) -> DeSolveMatrix:
    out.dimens = int(dimens)
    out.nspec = int(nspec)
    out.ynames = None if names is None else list(names)
    return out


def ode_band(
    y,
    times,
    func,
    parms,
    nspec=None,
    dimens=None,
    bandup=None,
    banddown=None,
    method="lsode",
    names=None,
    **kwargs,
):
    """Solve banded method-of-lines ODE systems (deSolve ``ode.band``)."""
    if bandup is None:
        raise ValueError("cannot run ode.band: bandup is not specified")
    if banddown is None:
        raise ValueError("cannot run ode.band: banddown is not specified")
    if nspec is None and dimens is None:
        raise ValueError("cannot run ode.band: nspec OR dimens should be specified")

    values, state_names = _as_y(y)
    n = len(values)

    if nspec is None:
        nspec = n // int(dimens)
    nspec = int(nspec)
    if n % nspec != 0:
        raise ValueError(
            "cannot run ode.band: nspec is not an integer fraction of number of state variables"
        )

    if names is not None and len(names) != nspec:
        raise ValueError("length of 'names' should equal 'nspec'")

    if method is None:
        method = "lsode"

    band_args = dict(
        bandup=int(bandup),
        banddown=int(banddown),
        jactype="bandint",
        **kwargs,
    )

    if method == "vode":
        from deSolve.vode import vode

        out = vode(y, times, func, parms=parms, **band_args)
    elif method == "lsode":
        from deSolve.lsode import lsode

        out = lsode(y, times, func, parms=parms, **band_args)
    elif method == "lsoda":
        from deSolve.lsoda import lsoda

        out = lsoda(y, times, func, parms=parms, **band_args)
    elif method == "lsodar":
        from deSolve.lsodar import lsodar

        out = lsodar(y, times, func, parms=parms, **band_args)
    elif method == "daspk":
        from deSolve.daspk import daspk

        out = daspk(y, times, func, parms=parms, **band_args)
    elif method == "radau":
        from deSolve.radau import radau

        out = radau(y, times, func, parms=parms, **band_args)
    else:
        raise ValueError("cannot run ode.band: method should be one of vode, lsoda, lsodar or lsode")

    if dimens is None:
        dimens = n // nspec
    return _attach_band_attrs(out, int(dimens), nspec, names)
