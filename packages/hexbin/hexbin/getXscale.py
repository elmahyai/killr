"""X scale of a hexVP. Ported from hexbin 1.28.6 `getXscale` in R/hexViewport.R.

In hexbin 1.28.6 the R generic and method are commented out. The commented body is `x@xscale`,
which is the slot read translated here.
"""

from __future__ import annotations

import numpy as np

from ._classes import HexVP


def getXscale(x: HexVP) -> np.ndarray:
    """Return the x scale `c(min, max)` of a hexVP."""
    if not isinstance(x, HexVP):
        raise TypeError("no applicable method for 'getXscale'")
    return np.array(x.xscale, dtype=np.float64)
