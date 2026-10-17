"""Generic `hsmooth`. Ported from hexbin 1.28.6 `hsmooth` in R/smoothHexbin.R.

R's generic `hsmooth(bin, wts)` has no default for `wts`, so `wts` is required here too.
The only method is `hexbin`, so this calls `smooth_hexbin`.
"""

from __future__ import annotations

from .smooth_hexbin import smooth_hexbin


def hsmooth(bin, wts):
    return smooth_hexbin(bin, wts)
