"""Bivariate median cell of an eroded hexbin. Ported from hexbin 1.28.6 `getHMedian` in R/hexbin.s4.R."""

from __future__ import annotations

import numpy as np

from ._classes import ErodeBin
from .hcell2xy import hcell2xy


def getHMedian(ebin: ErodeBin) -> dict:
    """Return `{"x": ..., "y": ...}` for the cell with the largest erosion order.

    R's `which.max` takes the first of any tied maxima, and `np.argmax` does the same.
    """
    if not isinstance(ebin, ErodeBin):
        raise TypeError("no applicable method for 'getHMedian'")
    xy = hcell2xy(ebin)
    erode_order = np.asarray(ebin.erode)
    if erode_order.size == 0:
        raise ValueError("1 == length(med <- which.max(ebin@erode)) is not TRUE")
    med = int(np.argmax(erode_order))
    return {"x": float(xy["x"][med]), "y": float(xy["y"][med])}
