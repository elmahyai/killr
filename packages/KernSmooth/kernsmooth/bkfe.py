"""Binned kernel functional estimate, ported from KernSmooth `bkfe`."""

from __future__ import annotations

import math
import warnings

import numpy as np
from linbin import linbin as _linbin


def bkfe(
    x,
    drv,
    bandwidth,
    gridsize: int = 401,
    range_x=None,
    binned: bool = False,
    truncate: bool = True,
) -> float:
    """Estimate a binned kernel density functional.

    Mirrors ``KernSmooth::bkfe``. ``drv`` is a non-negative even integer.
    ``bandwidth`` is required. When ``binned`` is false, bin counts come
    from the ``linbin`` crate. The normal-kernel weights and the FFT stay
    in NumPy. Returns one number.
    """
    order = _even_order(drv)
    if bandwidth is None or float(bandwidth) <= 0:
        raise ValueError("'bandwidth' must be strictly positive")
    bandwidth_used = float(bandwidth)

    sample = np.asarray(x, dtype=np.float64)
    if sample.ndim != 1:
        raise ValueError("x must be a one-dimensional sample")

    if binned:
        if range_x is None:
            raise ValueError("range_x is required when binned is true")
        gcounts = sample
        gridsize = int(gcounts.size)
    else:
        gridsize = int(gridsize)
        if gridsize < 2:
            raise ValueError("gridsize must be at least 2")
        if sample.size < 1:
            raise ValueError("x must contain at least one observation")

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

    m = gridsize
    if not binned:
        gcounts = np.asarray(
            _linbin(np.ascontiguousarray(sample), a, b, m, bool(truncate)),
            dtype=np.float64,
        )

    n = float(np.sum(gcounts))
    delta = (b - a) / (m - 1)
    tau = 4 + order
    length = min(math.floor(tau * bandwidth_used / delta), m)
    if length == 0:
        warnings.warn(
            "Binning grid too coarse for current (small) bandwidth: consider increasing 'gridsize'",
            stacklevel=2,
        )

    arg = np.arange(length + 1, dtype=np.float64) * delta / bandwidth_used
    kappa = _dnorm(arg) * _hermite(arg, order) / bandwidth_used ** (order + 1)

    pad = 2 ** math.ceil(math.log(m + length + 1) / math.log(2))
    kappa = np.concatenate(
        [kappa, np.zeros(pad - 2 * length - 1, dtype=np.float64), kappa[:0:-1]]
    )
    padded = np.concatenate([gcounts, np.zeros(pad - m, dtype=np.float64)])
    smoothed = np.fft.ifft(np.fft.fft(kappa) * np.fft.fft(padded)).real[:m]
    return float(np.sum(gcounts * smoothed) / (n ** 2))


def _even_order(drv) -> int:
    try:
        value = float(drv)
    except (TypeError, ValueError) as error:
        raise ValueError("drv must be a non-negative even integer") from error
    if not math.isfinite(value) or not value.is_integer() or value < 0 or int(value) % 2:
        raise ValueError("drv must be a non-negative even integer")
    return int(value)


def _hermite(arg: np.ndarray, order: int) -> np.ndarray:
    """Probabilists' Hermite polynomial He_order, as in the R recurrence."""
    if order == 0:
        return np.ones_like(arg)
    previous = np.ones_like(arg)
    current = arg.copy()
    if order == 1:
        return current
    for degree in range(2, order + 1):
        nxt = arg * current - (degree - 1) * previous
        previous = current
        current = nxt
    return current


def _dnorm(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
