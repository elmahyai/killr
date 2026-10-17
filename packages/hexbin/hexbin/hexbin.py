"""Hexagonal binning of points. Ported from hexbin 1.28.6 `hexbin()` in R/hexbin.s4.R.

The binning loop is the Fortran kernel `hbin.f`, called through the `hexbin_kernels` crate.
`call`, `xlab` and `ylab` default to "" because R's `match.call()` and `deparse()` have no
Python equivalent; pass `xlab` and `ylab` explicitly to set them.
"""

from __future__ import annotations

import math
import warnings

import numpy as np
from hexbin_kernels import hbin as _hbin_kernel

from ._classes import NA_INTEGER, HexBin
from ._r import encompass_fails


def xy_coords(x, y=None):
    """The numeric part of `grDevices::xy.coords(x, y)` that hexbin uses."""
    if y is None:
        if isinstance(x, dict) and "x" in x and "y" in x:
            return np.asarray(x["x"], dtype=np.float64), np.asarray(x["y"], dtype=np.float64)
        arr = np.asarray(x, dtype=np.float64)
        if arr.ndim == 2 and arr.shape[1] == 2:
            return arr[:, 0].copy(), arr[:, 1].copy()
        if arr.ndim == 1:
            # xy.coords with y NULL: y is the vector, x is seq_along.
            return np.arange(1, arr.size + 1, dtype=np.float64), arr.copy()
        raise ValueError("cannot coerce 'x' to xy coordinates")
    xa = np.asarray(x, dtype=np.float64).ravel()
    ya = np.asarray(y, dtype=np.float64).ravel()
    if xa.size != ya.size:
        raise ValueError("'x' and 'y' lengths differ")
    return xa, ya


def hexbin(
    x,
    y=None,
    xbins=30,
    shape=1.0,
    xbnds=None,
    ybnds=None,
    xlab=None,
    ylab=None,
    IDs=False,
) -> HexBin:
    """Bin points into hexagon cells. Returns a `HexBin` holding the R `hexbin` slots.

    `xbnds` and `ybnds` default to the range of the non-missing x and y.
    `IDs=True` returns `cID`, one cell id per point (NA_INTEGER where x or y is NaN).
    """
    x, y = xy_coords(x, y)
    xlab_out = "" if xlab is None else xlab
    ylab_out = "" if ylab is None else ylab

    n0 = x.size
    na = np.isnan(x) | np.isnan(y)
    has_na = bool(na.any())
    ok = ~na
    if has_na:
        x = x[ok]
        y = y[ok]
    n = x.size

    # Default bounds are evaluated after NA removal, as R's lazy default does.
    xb_supplied = xbnds is not None
    yb_supplied = ybnds is not None
    xb = (float(x.min()), float(x.max())) if not xb_supplied else (float(xbnds[0]), float(xbnds[1]))
    yb = (float(y.min()), float(y.max())) if not yb_supplied else (float(ybnds[0]), float(ybnds[1]))

    if xb[1] - xb[0] <= 0:
        raise ValueError("xbnds[1] < xbnds[2] is not fulfilled")
    if xb_supplied and encompass_fails(xb, (x.min(), x.max())):
        raise ValueError("'xbnds' must encompass range(x)")
    if yb[1] - yb[0] <= 0:
        raise ValueError("ybnds[1] < ybnds[2] is not fulfilled")
    if yb_supplied and encompass_fails(yb, (y.min(), y.max())):
        raise ValueError("'ybnds' must encompass range(y)")

    jmax = math.floor(xbins + 1.5001)
    c1 = 2 * math.floor((xbins * shape) / math.sqrt(3) + 1.5001)
    imax = math.trunc((jmax * c1 - 1) / jmax + 1)

    cell, cnt, xcm, ycm, _nrow, ids = _hbin_kernel(
        np.ascontiguousarray(x),
        np.ascontiguousarray(y),
        float(xbins),
        float(shape),
        xb,
        yb,
        (int(imax), int(jmax)),
        bool(IDs),
    )

    if int(cnt.sum()) != n:
        warnings.warn("Lost counts in binning")

    cid = None
    if IDs:
        if has_na:
            cid = np.full(n0, NA_INTEGER, dtype=np.int32)
            cid[ok] = ids
        else:
            cid = np.asarray(ids, dtype=np.int32)

    return HexBin(
        cell=np.asarray(cell, dtype=np.int32),
        count=np.asarray(cnt, dtype=np.float64),
        xcm=np.asarray(xcm, dtype=np.float64),
        ycm=np.asarray(ycm, dtype=np.float64),
        xbins=float(xbins),
        shape=float(shape),
        xbnds=np.array(xb, dtype=np.float64),
        ybnds=np.array(yb, dtype=np.float64),
        dimen=np.array([imax, jmax], dtype=np.float64),
        n=n,
        ncells=int(cell.size),
        call=None,
        xlab=xlab_out,
        ylab=ylab_out,
        cID=cid,
    )
