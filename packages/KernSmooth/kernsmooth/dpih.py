"""Direct plug-in histogram bin width, ported from KernSmooth `dpih`."""

from __future__ import annotations

import math

import numpy as np
from linbin import linbin as _linbin

from kernsmooth.bkfe import bkfe
from kernsmooth.dpik import _follow_up, _level, _real_power, _scale

_SCALES = ("minim", "stdev", "iqr")


def dpih(
    x,
    scalest: str = "minim",
    level: int = 2,
    gridsize: int = 401,
    range_x=None,
    truncate: bool = True,
) -> float:
    """Select a histogram bin width.

    Mirrors ``KernSmooth::dpih``. Bin counts come from the ``linbin`` crate.
    Plug-in functionals come from ``bkfe``. Returns one bin width.
    """
    sample = np.asarray(x, dtype=np.float64)
    if sample.ndim != 1:
        raise ValueError("x must be a one-dimensional sample")
    n = int(sample.size)
    if n < 2:
        raise ValueError("x must contain at least two observations")
    if scalest not in _SCALES:
        raise ValueError(f"scalest must be one of {', '.join(_SCALES)}")

    stage = _level(level)
    gridsize = int(gridsize)
    if gridsize < 2:
        raise ValueError("gridsize must be at least 2")

    if range_x is None:
        a = float(np.min(sample))
        b = float(np.max(sample))
    else:
        bounds = np.asarray(range_x, dtype=np.float64)
        if bounds.shape != (2,):
            raise ValueError("range_x must contain two endpoints")
        a = float(bounds[0])
        b = float(bounds[1])
    if not b > a:
        raise ValueError("range_x must be strictly increasing")

    scale = _scale(sample, scalest)
    if scale == 0:
        raise ValueError("scale estimate is zero for input data")

    center = float(np.mean(sample))
    standardized = (sample - center) / scale
    sa = (a - center) / scale
    sb = (b - center) / scale
    counts = np.asarray(
        _linbin(np.ascontiguousarray(standardized), sa, sb, gridsize, bool(truncate)),
        dtype=np.float64,
    )
    if stage == 0:
        width = _real_power(24.0 * math.sqrt(math.pi) / n, 1.0 / 3.0)
    else:
        psi2 = _psi2(counts, n, stage, sa, sb)
        width = _real_power(6.0 / (-psi2 * n), 1.0 / 3.0)
    return float(scale * width)


def histogram_breaks(x, width: float) -> np.ndarray:
    """Break points matching R's ``seq(min(x) - h, max(x) + h, by = h)``."""
    sample = np.asarray(x, dtype=np.float64)
    start = float(np.min(sample)) - width
    stop = float(np.max(sample)) + width
    count = int(math.floor((stop - start) / width + 1e-10)) + 1
    breaks = start + width * np.arange(count, dtype=np.float64)
    if breaks.size and breaks[-1] > stop + 1e-10 * abs(width):
        breaks = breaks[:-1]
    return breaks


def _psi2(counts: np.ndarray, n: int, level: int, sa: float, sb: float) -> float:
    bounds = (sa, sb)
    root = 2 * level + 3
    alpha = _real_power(2.0 / ((root - 2) * n), 1.0 / root) * math.sqrt(2.0)
    order = 2 * level
    estimate = bkfe(counts, order, alpha, range_x=bounds, binned=True)
    while order > 2:
        order -= 2
        estimate = bkfe(
            counts,
            order,
            _follow_up(estimate, n, order),
            range_x=bounds,
            binned=True,
        )
    return float(estimate)
