"""Integer row and column of every cell in the grid. Ported from hexbin 1.28.6 `hcell2xyInt` in R/hexutil.R."""

from __future__ import annotations

import math

import numpy as np

from ._classes import HexBin


def hcell2xyInt(
    hbin: HexBin | None = None,
    xbins=None,
    xbnds=None,
    ybnds=None,
    shape=None,
) -> dict:
    """Return `{"i": rows, "j": columns}`, 1-based, for every grid cell.

    With no `hbin`, the grid is built from `xbins` and `shape`, and `xbnds` and `ybnds`
    must be given, as R requires.
    """
    if hbin is None and (xbnds is None or ybnds is None):
        raise ValueError("Need a hexbin object or boundaries to make lattice")
    if hbin is None and (xbins is None or shape is None):
        raise ValueError("Need xbins and shape to make a lattice")
    if hbin is not None:
        dimen = (int(hbin.dimen[0]), int(hbin.dimen[1]))
    else:
        jmax = math.floor(xbins + 1.5001)
        imax = 2 * math.floor((xbins * shape) / math.sqrt(3) + 1.5001)
        dimen = (imax, jmax)

    total = dimen[0] * dimen[1]
    cell = np.arange(total, dtype=np.int64)
    i = cell // dimen[1]
    j = cell % dimen[1]
    return {"i": i + 1, "j": j + 1}
