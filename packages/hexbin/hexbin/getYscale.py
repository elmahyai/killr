"""Y scale of a hexVP. Ported from hexbin 1.28.6 `getYscale` in R/hexViewport.R.

In hexbin 1.28.6 the R generic and method are commented out. The commented body is `x@yscale`,
which is the slot read translated here.
"""

from __future__ import annotations

import numpy as np

from ._classes import HexVP


def getYscale(x: HexVP) -> np.ndarray:
    """Return the y scale `c(min, max)` of a hexVP."""
    if not isinstance(x, HexVP):
        raise TypeError("no applicable method for 'getYscale'")
    return np.array(x.yscale, dtype=np.float64)
