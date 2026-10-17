"""Cell centres of a hexbin object. Ported from hexbin 1.28.6 `hcell2xy` in R/hexbin.s4.R."""

from __future__ import annotations

import math

import numpy as np

from ._classes import ErodeBin, HexBin


def hcell2xy(hbin: HexBin, check_erosion: bool = True) -> dict:
    """Return `{"x": ..., "y": ...}`, the centre of each cell of `hbin`.

    For an `ErodeBin` with `check_erosion=True`, only the eroded cells are returned.
    """
    if not isinstance(hbin, HexBin):
        raise TypeError("no applicable method for 'hcell2xy'")
    xbins = hbin.xbins
    xbnds = hbin.xbnds
    c3 = (xbnds[1] - xbnds[0]) / xbins
    ybnds = hbin.ybnds
    c4 = ((ybnds[1] - ybnds[0]) * math.sqrt(3)) / (2 * hbin.shape * xbins)
    jmax = int(hbin.dimen[1])
    cell = hbin.cell.astype(np.int64) - 1
    i = cell // jmax
    j = cell % jmax
    y = c4 * i + ybnds[0]
    x = c3 * np.where(i % 2 == 0, j, j + 0.5) + xbnds[0]
    if check_erosion and isinstance(hbin, ErodeBin):
        keep = np.asarray(hbin.eroded, dtype=bool)
        return {"x": x[keep], "y": y[keep]}
    return {"x": x, "y": y}
