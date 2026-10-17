"""Points in sparse cells. Ported from hexbin 1.28.6 `inout.hex` in R/hexutil.R."""

from __future__ import annotations

import numpy as np

from ._classes import HexBin, NA_INTEGER


def inout_hex(hbin: HexBin, mincnt) -> np.ndarray:
    """Return the 1-based positions of the points whose cell holds fewer than `mincnt` points."""
    if hbin.cID is None:
        raise ValueError("bin object must have a cID slot, \n try re-binning with ID = TRUE")
    ids = np.asarray(hbin.cID)
    valid = ids != NA_INTEGER
    levels, counts = np.unique(ids[valid], return_counts=True)
    sparse = levels[counts < mincnt]
    mask = valid & np.isin(ids, sparse)
    return np.flatnonzero(mask) + 1
