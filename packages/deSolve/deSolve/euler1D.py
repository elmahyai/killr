"""1-D spatial wrapper around ``euler`` (deSolve ``euler.1D``)."""

from __future__ import annotations

from deSolve.euler import euler
from deSolve.ode1D import _attach_1d_attrs
from deSolve.rk4 import _as_y


def euler_1D(
    y,
    times,
    func,
    parms,
    nspec=None,
    dimens=None,
    names=None,
    verbose=False,
    ynames=True,
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
    """Integrate a 1-D reaction-transport model with explicit Euler."""
    if nspec is None and dimens is None:
        raise ValueError("cannot run euler.1D: nspec OR dimens should be specified")

    values, _state_names = _as_y(y)
    n = len(values)

    if dimens is None:
        dimens = n // int(nspec)
    nspec = int(nspec if nspec is not None else n // int(dimens))

    if n % nspec != 0:
        raise ValueError(
            "cannot run ode.1D: nspec is not an integer fraction of number of state variables"
        )

    if names is not None and len(names) != nspec:
        raise ValueError("length of 'names' should equal 'nspec'")

    out = euler(
        y,
        times,
        func,
        parms,
        verbose=verbose,
        ynames=ynames,
        dllname=dllname,
        initfunc=initfunc,
        initpar=initpar,
        rpar=rpar,
        ipar=ipar,
        nout=nout,
        outnames=outnames,
        forcings=forcings,
        initforc=initforc,
        fcontrol=fcontrol,
        **kwargs,
    )
    if dimens is None:
        dimens = n // nspec
    return _attach_1d_attrs(out, int(dimens), nspec, names)
