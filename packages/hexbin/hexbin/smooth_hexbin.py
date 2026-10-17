"""Hexagon smoother. Ported from hexbin 1.28.6 `smooth.hexbin` in R/smoothHexbin.R.

The smoothing loop is the Fortran kernel `hsm.f`, called through the `hexbin_kernels` crate.
The result grid is padded by two cells on each side, so the bounds and dimensions grow.
"""

from __future__ import annotations

import numpy as np
from hexbin_kernels import hsm as _hsm_kernel

from ._classes import HexBin, SmoothBin, base_slots
from ._r import add_bit


def smooth_hexbin(bin: HexBin, wts=(48, 4, 1)) -> SmoothBin:
    if not isinstance(bin, HexBin):
        raise TypeError("first argument must be a hexbin object")

    wts_i = np.asarray(wts, dtype=np.float64)
    wts_i = np.array([int(w) for w in wts_i], dtype=np.int64)
    if wts_i.size < 3:
        raise ValueError("wts must hold three integer weights")
    wt3 = (int(wts_i[0]), int(wts_i[1]), int(wts_i[2]))

    cell = bin.cell.astype(np.int64) - 1
    cnt = np.asarray(bin.count).astype(np.int64)
    xbins = bin.xbins
    row = int(bin.dimen[0])
    col = int(bin.dimen[1])
    ncol = col + 4
    nrow = row + 4
    nmax = ncol * nrow

    nr = cell // col + 2
    nc = cell % col + 3
    cell_pad = nr * ncol + nc

    out_cell, out_cnt = _hsm_kernel(
        np.ascontiguousarray(cell_pad, dtype=np.int32),
        np.ascontiguousarray(cnt, dtype=np.int32),
        int(nmax),
        int(ncol),
        wt3,
    )

    base = base_slots(bin)
    base["xbins"] = bin.xbins + 4
    base["xbnds"] = add_bit(bin.xbnds, f=2 / xbins)
    base["ybnds"] = add_bit(bin.ybnds, f=2 / xbins)
    base["dimen"] = np.array([nrow, ncol], dtype=np.float64)
    base["cell"] = np.asarray(out_cell, dtype=np.int32)
    base["count"] = np.asarray(out_cnt, dtype=np.float64)
    return SmoothBin(**base, wts=np.asarray(wts, dtype=np.float64))
