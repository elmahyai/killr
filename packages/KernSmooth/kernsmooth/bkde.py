"""Binned kernel density estimate, ported from KernSmooth `bkde`."""

from __future__ import annotations

import math
import warnings

import numpy as np
from linbin import linbin as _linbin

_KERNELS = ("normal", "box", "epanech", "biweight", "triweight")

_DEL0 = {
    "normal": (1.0 / (4.0 * math.pi)) ** 0.1,
    "box": (9.0 / 2.0) ** 0.2,
    "epanech": 15.0 ** 0.2,
    "biweight": 35.0 ** 0.2,
    "triweight": (9450.0 / 143.0) ** 0.2,
}

_BETA_SHAPES = {
    "box": 1,
    "epanech": 2,
    "biweight": 3,
    "triweight": 4,
}


def bkde(
    x,
    kernel: str = "normal",
    canonical: bool = False,
    bandwidth: float | None = None,
    gridsize: int = 401,
    range_x=None,
    truncate: bool = True,
) -> dict[str, np.ndarray]:
    """Compute a binned kernel density estimate.

    Mirrors ``KernSmooth::bkde``. Returns ``{"x": grid, "y": density}``.
    Bin counts come from the ``linbin`` crate. Kernel weights and the FFT
    stay in NumPy, as they do in the R wrapper.
    """
    sample = np.asarray(x, dtype=np.float64)
    if sample.ndim != 1:
        raise ValueError("x must be a one-dimensional sample")
    n = sample.size
    if n < 2:
        raise ValueError("x must contain at least two observations")
    if kernel not in _KERNELS:
        raise ValueError(f"kernel must be one of {', '.join(_KERNELS)}")

    gridsize = int(gridsize)
    if gridsize < 2:
        raise ValueError("gridsize must be at least 2")

    if bandwidth is not None and bandwidth <= 0:
        raise ValueError("'bandwidth' must be strictly positive")

    del0 = _DEL0[kernel]
    if bandwidth is None:
        scale = float(np.sqrt(np.var(sample, ddof=1)))
        bandwidth_used = del0 * (243.0 / (35.0 * n)) ** 0.2 * scale
    elif canonical:
        bandwidth_used = del0 * float(bandwidth)
    else:
        bandwidth_used = float(bandwidth)
    if bandwidth_used <= 0:
        raise ValueError("'bandwidth' must be strictly positive")

    tau = 4.0 if kernel == "normal" else 1.0
    if range_x is None:
        a = float(np.min(sample) - tau * bandwidth_used)
        b = float(np.max(sample) + tau * bandwidth_used)
    else:
        bounds = np.asarray(range_x, dtype=np.float64)
        if bounds.shape != (2,):
            raise ValueError("range_x must contain two endpoints")
        a = float(bounds[0])
        b = float(bounds[1])
    if not b > a:
        raise ValueError("range_x must be strictly increasing")

    m = gridsize
    gpoints = np.linspace(a, b, m)
    gcounts = np.asarray(
        _linbin(np.ascontiguousarray(sample), a, b, m, bool(truncate)),
        dtype=np.float64,
    )

    delta = (b - a) / (bandwidth_used * (m - 1))
    length = min(math.floor(tau / delta), m)
    if length == 0:
        warnings.warn(
            "Binning grid too coarse for current (small) bandwidth: consider increasing 'gridsize'",
            stacklevel=2,
        )

    lags = np.arange(length + 1, dtype=np.float64)
    kappa = _kernel_weights(kernel, lags * delta, n, bandwidth_used)

    pad = 2 ** math.ceil(math.log(m + length + 1) / math.log(2))
    kappa = np.concatenate(
        [kappa, np.zeros(pad - 2 * length - 1, dtype=np.float64), kappa[:0:-1]]
    )
    total = float(np.sum(kappa) * (b - a) / (m - 1) * n)
    gcounts = np.concatenate([gcounts, np.zeros(pad - m, dtype=np.float64)])
    density = np.fft.ifft(np.fft.fft(kappa / total) * np.fft.fft(gcounts)).real[:m]
    return {"x": gpoints, "y": density}


def _kernel_weights(kernel: str, z: np.ndarray, n: int, bandwidth: float) -> np.ndarray:
    if kernel == "normal":
        weights = _dnorm(z)
    else:
        weights = 0.5 * _dbeta_equal(0.5 * (z + 1.0), _BETA_SHAPES[kernel])
    return weights / (n * bandwidth)


def _dnorm(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _dbeta_equal(z: np.ndarray, shape: int) -> np.ndarray:
    """Beta density with equal integer shapes, matching R's ``dbeta`` on [0, 1]."""
    out = np.zeros_like(z, dtype=np.float64)
    inside = (z >= 0.0) & (z <= 1.0)
    if shape == 1:
        out[inside] = 1.0
        return out
    scale = {2: 6.0, 3: 30.0, 4: 140.0}[shape]
    values = z[inside]
    out[inside] = scale * (values * (1.0 - values)) ** (shape - 1)
    return out
