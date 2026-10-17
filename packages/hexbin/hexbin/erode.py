"""Generic `erode`. Ported from hexbin 1.28.6 `erode` in R/hexbin.s4.R.

R dispatches `erode` on the class of `hbin`. The only method is `hexbin`, so this
function calls `erode_hexbin` directly.
"""

from __future__ import annotations

from .erode_hexbin import erode_hexbin


def erode(hbin, cdfcut: float = 0.5):
    return erode_hexbin(hbin, cdfcut)
