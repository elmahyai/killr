"""Gray-level erosion of a hexbin object. Ported from hexbin 1.28.6 `erode.hexbin` in R/hexbin.s4.R.

The erosion order is the Fortran kernel `herode.f`, called through the `hexbin_kernels` crate.
"""

from __future__ import annotations

import numpy as np
from hexbin_kernels import herode as _herode_kernel

from ._classes import ErodeBin, HexBin, base_slots


def erode_hexbin(hbin: HexBin, cdfcut: float = 0.5):
    """Erode the cells of `hbin` by count, from the lowest cells up.

    Returns an `ErodeBin`. When no cell reaches the `cdfcut` quantile, returns the string
    "no cells selected", as R does.
    """
    if not isinstance(hbin, HexBin):
        raise TypeError("first argument must be a hexbin object")

    cell = hbin.cell
    cnt = hbin.count
    tmp = np.sort(cnt)
    cdf = np.cumsum(tmp) / np.sum(cnt)
    good = cdfcut <= cdf
    if not good.any():
        return "no cells selected"
    crit = tmp[good].min()
    good = crit <= cnt
    cell = cell[good]
    cnt = cnt[good]

    bdim = hbin.dimen
    erode_order = _herode_kernel(
        np.ascontiguousarray(cell, dtype=np.int32),
        np.ascontiguousarray(cnt, dtype=np.int32),
        (int(bdim[0]), int(bdim[1])),
    )

    return ErodeBin(
        **base_slots(hbin),
        cdfcut=float(cdfcut),
        eroded=np.asarray(good, dtype=bool),
        erode=np.asarray(erode_order, dtype=np.int32),
    )
