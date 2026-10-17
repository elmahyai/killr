"""Plot region of a hexVP. Ported from hexbin 1.28.6 `getPlt`, the method for hexVP in R/hexViewport.R.

`ret_unit` and `numeric` are R's `ret.unit` and `numeric`. Only the numeric value in the unit the
object stores (npc) is translated; other units need grid's device size.
"""

from __future__ import annotations

import numpy as np

from ._classes import HexVP
from ._units import numeric_in_unit


def getPlt(x: HexVP, ret_unit: str = "npc", numeric: bool = False) -> np.ndarray:
    """Return the plot region `c(width, height)` of a hexVP."""
    if not isinstance(x, HexVP):
        raise TypeError("no applicable method for 'getPlt'")
    return numeric_in_unit(x.plt, x.plt_unit, ret_unit, numeric, "getPlt")
