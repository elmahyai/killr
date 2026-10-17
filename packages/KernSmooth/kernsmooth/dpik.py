"""Direct plug-in bandwidth selector, ported from KernSmooth `dpik`."""

from __future__ import annotations

import math

import numpy as np
from linbin import linbin as _linbin

from kernsmooth.bkde import _DEL0
from kernsmooth.bkfe import bkfe

_SCALES = ("minim", "stdev", "iqr")


def dpik(
    x,
    scalest: str = "minim",
    level: int = 2,
    kernel: str = "normal",
    canonical: bool = False,
    gridsize: int = 401,
    range_x=None,
    truncate: bool = True,
) -> float:
    """Select a bandwidth for a kernel density estimate.

    Mirrors ``KernSmooth::dpik``. Bin counts come from the ``linbin`` crate.
    Plug-in functionals come from ``bkfe``. Returns one bandwidth.
    """
    sample = np.asarray(x, dtype=np.float64)
    if sample.ndim != 1:
        raise ValueError("x must be a one-dimensional sample")
    n = int(sample.size)
    if n < 2:
        raise ValueError("x must contain at least two observations")
    if kernel not in _DEL0:
        raise ValueError(f"kernel must be one of {', '.join(_DEL0)}")
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
    psi4 = _psi4(counts, n, stage, sa, sb)
    del0 = 1.0 if canonical else _DEL0[kernel]
    return float(scale * del0 * _real_power(1.0 / (psi4 * n), 0.2))


def _level(level) -> int:
    try:
        value = float(level)
    except (TypeError, ValueError) as error:
        raise ValueError("Level should be between 0 and 5") from error
    if not math.isfinite(value) or not value.is_integer() or value < 0 or value > 5:
        raise ValueError("Level should be between 0 and 5")
    return int(value)


def _scale(sample: np.ndarray, scalest: str) -> float:
    stdev = float(np.sqrt(np.var(sample, ddof=1)))
    quartile = np.quantile(sample, [0.25, 0.75])
    iqr = float((quartile[1] - quartile[0]) / 1.349)
    if scalest == "stdev":
        return stdev
    if scalest == "iqr":
        return iqr
    return min(iqr, stdev)


def _psi4(counts: np.ndarray, n: int, level: int, sa: float, sb: float) -> float:
    bounds = (sa, sb)
    if level == 0:
        return 3.0 / (8.0 * math.sqrt(math.pi))

    root = 2 * level + 5
    alpha = _real_power(2.0 * math.sqrt(2.0) ** root / ((root - 2) * n), 1.0 / root)
    order = 2 * level + 2
    estimate = bkfe(counts, order, alpha, range_x=bounds, binned=True)
    while order > 4:
        order -= 2
        estimate = bkfe(
            counts,
            order,
            _follow_up(estimate, n, order),
            range_x=bounds,
            binned=True,
        )
    return float(estimate)


def _follow_up(higher: float, n: int, order: int) -> float:
    """Bandwidth for the next lower even derivative, as in the R plug-in steps."""
    sign = -1.0 if (order // 2) % 2 == 0 else 1.0
    magnitude = 1.0
    factor = 3
    for _ in range(order // 2 - 1):
        magnitude *= factor
        factor += 2
    coefficient = sign * magnitude
    exponent = 1.0 / (order + 3)
    return _real_power(coefficient * math.sqrt(2.0 / math.pi) / (higher * n), exponent)


def _real_power(base: float, exponent: float) -> float:
    if base < 0:
        return -((-base) ** exponent)
    return base ** exponent
