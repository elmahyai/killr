"""Aspect ratio of the plotting region. Ported from hexbin 1.28.6 `optShape` in R/hexutil.R.

Only the numeric path is translated: `height` and `width` given directly, or a hexVP-like
object with a `plt` attribute. The grid `viewport` branch needs grid's unit conversion,
which is not translated, so it raises NotImplementedError.
"""

from __future__ import annotations


def optShape(vp=None, height=None, width=None, mar=None) -> float:
    if vp is None and (height is None or width is None):
        raise ValueError("Need a viewport object or height and width of the plotting region.")
    if vp is not None:
        plt = getattr(vp, "plt", None)
        if plt is None:
            raise NotImplementedError(
                "grid viewport input needs grid unit conversion, which is not translated"
            )
        height = plt[1]
        width = plt[0]
    if mar is not None:
        height = height - mar[0] - mar[2]
        width = width - mar[1] - mar[3]
    return float(height) / float(width)
