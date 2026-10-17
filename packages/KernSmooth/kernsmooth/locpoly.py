"""Local polynomial density and regression, ported from KernSmooth `locpoly`."""

from __future__ import annotations

import math

import numpy as np
from linbin import linbin as _linbin
from locpol import locpol as _locpol
from rlbin import rlbin as _rlbin


def locpoly(
    x,
    y=None,
    drv: int = 0,
    degree: int | None = None,
    kernel: str = "normal",
    bandwidth=None,
    gridsize: int = 401,
    bwdisc: int = 25,
    range_x=None,
    binned: bool = False,
    truncate: bool = True,
) -> dict:
    """Estimate a density, a regression function, or a derivative.

    Mirrors ``KernSmooth::locpoly``. Density binning uses the existing
    ``linbin`` crate. Regression binning uses ``rlbin``. The fit uses
    ``locpol``. ``kernel`` is accepted and ignored. Returns ``x`` and ``y``.
    """
    del kernel
    if bandwidth is None:
        raise ValueError("bandwidth is required")
    order = _integer(drv, "drv")
    if order < 0:
        raise ValueError("drv must be non-negative")
    poly = order + 1 if degree is None else _integer(degree, "degree")
    if poly < order:
        raise ValueError("degree must be at least drv")

    sample = np.asarray(x, dtype=np.float64)
    if sample.ndim != 1 or sample.size == 0:
        raise ValueError("x must be a non-empty one-dimensional sample")
    response = None if y is None else np.asarray(y, dtype=np.float64)

    if response is None:
        if range_x is None:
            low = float(np.min(sample))
            high = float(np.max(sample))
            extra = 0.05 * (high - low)
            a = low - extra
            b = high + extra
        else:
            a, b = _bounds(range_x)
        m = _gridsize(gridsize)
        grid = np.linspace(a, b, m)
        counts = np.asarray(
            _linbin(np.ascontiguousarray(sample), a, b, m, bool(truncate)),
            dtype=np.float64,
        )
        xcounts = np.ones(m, dtype=np.float64)
        ycounts = (m - 1) * counts / (sample.size * (b - a))
    elif binned:
        if response.ndim != 1 or response.shape != sample.shape:
            raise ValueError("binned x and y must be grid counts of the same length")
        if range_x is None:
            raise ValueError("range_x is required when binned is true")
        a, b = _bounds(range_x)
        m = int(sample.size)
        if m < 2:
            raise ValueError("gridsize must be at least 2")
        grid = np.linspace(a, b, m)
        xcounts = np.ascontiguousarray(sample)
        ycounts = np.ascontiguousarray(response)
    else:
        if response.ndim != 1 or response.shape != sample.shape:
            raise ValueError("x and y must have the same length")
        if range_x is None:
            a = float(np.min(sample))
            b = float(np.max(sample))
        else:
            a, b = _bounds(range_x)
        m = _gridsize(gridsize)
        grid = np.linspace(a, b, m)
        xcounts, ycounts = _rlbin(
            np.ascontiguousarray(sample),
            np.ascontiguousarray(response),
            a,
            b,
            m,
            bool(truncate),
        )
        xcounts = np.asarray(xcounts, dtype=np.float64)
        ycounts = np.asarray(ycounts, dtype=np.float64)

    if not b > a:
        raise ValueError("range_x must be strictly increasing")
    delta = (b - a) / (m - 1)
    hdisc, lvec, indic = _discretize(bandwidth, m, _integer(bwdisc, "bwdisc"), delta)
    curve = np.asarray(
        _locpol(
            np.ascontiguousarray(xcounts),
            np.ascontiguousarray(ycounts),
            order,
            delta,
            np.ascontiguousarray(hdisc),
            np.ascontiguousarray(lvec),
            np.ascontiguousarray(indic),
            poly,
        ),
        dtype=np.float64,
    )
    return {"x": grid, "y": curve * math.factorial(order)}


def _bounds(range_x) -> tuple[float, float]:
    bounds = np.asarray(range_x, dtype=np.float64)
    if bounds.shape != (2,):
        raise ValueError("range_x must contain two endpoints")
    return float(bounds[0]), float(bounds[1])


def _gridsize(gridsize) -> int:
    size = _integer(gridsize, "gridsize")
    if size < 2:
        raise ValueError("gridsize must be at least 2")
    return size


def _integer(value, name: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"{name} must be an integer")
    return int(number)


def _discretize(bandwidth, m: int, bands: int, delta: float):
    if bands < 1:
        raise ValueError("bwdisc must be at least 1")
    values = np.atleast_1d(np.asarray(bandwidth, dtype=np.float64)).reshape(-1)
    if values.size == 0 or not np.all(np.isfinite(values)) or np.any(values <= 0):
        raise ValueError("bandwidth must be strictly positive")
    tau = 4.0
    if values.size == m:
        ordered = np.sort(values)
        low = float(ordered[0])
        high = float(ordered[-1])
        hdisc = np.exp(np.linspace(math.log(low), math.log(high), bands))
        half = np.floor(tau * hdisc / delta).astype(np.int32)
        if bands > 1:
            gap = (math.log(float(hdisc[-1])) - math.log(float(hdisc[0]))) / (bands - 1)
            if gap == 0.0:
                indic = np.ones(m, dtype=np.int32)
            else:
                indic = np.rint((np.log(values) - math.log(low)) / gap).astype(np.int32) + 1
        else:
            indic = np.ones(m, dtype=np.int32)
    elif values.size == 1:
        width = float(values[0])
        hdisc = np.array([width], dtype=np.float64)
        half = np.array([math.floor(tau * width / delta)], dtype=np.int32)
        indic = np.ones(m, dtype=np.int32)
    else:
        raise ValueError("bandwidth must be a scalar or an array of length gridsize")
    if int(half.min()) == 0:
        raise ValueError(
            "Binning grid too coarse for current (small) bandwidth: consider increasing gridsize"
        )
    return hdisc, half, indic
