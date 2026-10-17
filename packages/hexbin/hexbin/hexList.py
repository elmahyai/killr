"""Bin points once per group. Ported from hexbin 1.28.6 `hexList` in R/hexbinList.R.

Groups are taken in order of first appearance, as R's `unique(given)` gives them.
`Xbins` is `integer(xbins)` in R, a vector of zeros of that length, and it is kept that way.
"""

from __future__ import annotations

import numpy as np

from ._classes import HexBinList
from .hexbin import hexbin, xy_coords


def hexList(
    x,
    y=None,
    given=None,
    xbins=30,
    shape=1.0,
    xbnds=None,
    ybnds=None,
    xlab=None,
    ylab=None,
) -> HexBinList:
    xa, ya = xy_coords(x, y)
    if given is None or len(given) != xa.size:
        raise ValueError("Given is is different length from x and y")
    # as.character() for factors and other labels; string arrays compare in C.
    labels = np.asarray(given).astype(str)
    uniq, first = np.unique(labels, return_index=True)
    groups = uniq[np.argsort(first, kind="stable")]

    if xbnds is None:
        xbnds = (float(np.min(xa)), float(np.max(xa)))
    if ybnds is None:
        ybnds = (float(np.min(ya)), float(np.max(ya)))

    hbins = []
    for g in groups:
        mask = labels == g
        hbins.append(
            hexbin(
                xa[mask],
                ya[mask],
                xbins=xbins,
                shape=shape,
                xbnds=xbnds,
                ybnds=ybnds,
            )
        )

    mx = max(float(np.max(h.count)) for h in hbins)
    mn = min(float(np.min(h.count)) for h in hbins)
    return HexBinList(
        n=len(hbins),
        hbins=hbins,
        Xbnds=np.asarray(xbnds, dtype=np.float64),
        Ybnds=np.asarray(ybnds, dtype=np.float64),
        Xbins=np.zeros(int(xbins), dtype=np.float64),
        Shape=float(shape),
        Bnames=[str(g) for g in groups],
        CntBnds=np.array([mn, mx], dtype=np.float64),
    )
