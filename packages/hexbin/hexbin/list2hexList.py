"""Combine hexbin objects into a hexbinList. Ported from hexbin 1.28.6 `list2hexList` in R/hexutil.R.

R takes the names of a named list for `Bnames`. Here the input is a dict, whose keys are
those names. A list without names is an error, as it is in R.
"""

from __future__ import annotations

import numpy as np

from ._classes import HexBin, HexBinList


def list2hexList(binlst) -> HexBinList:
    if isinstance(binlst, dict):
        names = [str(k) for k in binlst.keys()]
        items = list(binlst.values())
    else:
        names = None
        items = list(binlst)

    if len(items) < 2:
        raise ValueError(" need at least 2 hex bin objects")
    if not all(isinstance(h, HexBin) for h in items):
        raise ValueError("All Elements of list must be hexbin objects")

    # bnds.check: the same xbnds and ybnds in every object.
    xb0 = np.asarray(items[0].xbnds)
    yb0 = np.asarray(items[0].ybnds)
    xb_ok = all(np.array_equal(np.asarray(h.xbnds), xb0) for h in items)
    yb_ok = all(np.array_equal(np.asarray(h.ybnds), yb0) for h in items)
    if not (xb_ok and yb_ok):
        raise ValueError("All bin objects in list need the same xbnds and ybnds")
    if not all(h.xbins == items[0].xbins for h in items):
        raise ValueError("All bin objects in list need the same number of bins")
    if not all(h.shape == items[0].shape for h in items):
        raise ValueError("All bin objects in list need the same shape parameter")

    if names is None:
        raise ValueError(
            "assignment of an object of class \"NULL\" is not valid for slot 'Bnames'"
        )

    mx = max(float(np.max(h.count)) for h in items)
    mn = min(float(np.min(h.count)) for h in items)
    return HexBinList(
        n=len(items),
        hbins=items,
        Xbnds=xb0.copy(),
        Ybnds=yb0.copy(),
        Xbins=items[0].xbins,
        Shape=items[0].shape,
        Bnames=names,
        CntBnds=np.array([mn, mx], dtype=np.float64),
    )
