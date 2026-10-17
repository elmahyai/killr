"""Bivariate binned kernel density estimate, ported from KernSmooth `bkde2D`."""

from __future__ import annotations

import math
import warnings

import numpy as np
from lbtwod import lbtwod as _lbtwod

_TAU = 3.4


def bkde2d(
    x,
    bandwidth,
    gridsize=(51, 51),
    range_x=None,
    truncate=True,
) -> dict[str, np.ndarray]:
    """Compute a 2D binned kernel density estimate.

    Mirrors ``KernSmooth::bkde2D``. ``x`` is a two-column sample and
    ``bandwidth`` has length 2. A single bandwidth is used in both directions.
    Returns ``x1``, ``x2``, and ``fhat``. Bin counts come from the ``lbtwod``
    crate. The bivariate normal kernel and the two-dimensional FFT stay in
    NumPy.

    The default range extends the data by 1.5 bandwidths on each side.
    Observations outside the mesh are ignored. ``truncate`` is retained from
    the R signature; KernSmooth 2.23-26 bins with that same rule either way.
    """
    del truncate
    sample = np.asarray(x, dtype=np.float64)
    if sample.ndim != 2 or sample.shape[1] != 2:
        raise ValueError("x must be a two-column sample")
    n = int(sample.shape[0])
    if n < 1:
        raise ValueError("x must contain at least one observation")
    if not np.all(np.isfinite(sample)):
        raise ValueError("x must not contain missing values")

    h1, h2 = _bandwidth(bandwidth)
    m1, m2 = _gridsize(gridsize)
    if range_x is None:
        a1 = float(np.min(sample[:, 0]) - 1.5 * h1)
        b1 = float(np.max(sample[:, 0]) + 1.5 * h1)
        a2 = float(np.min(sample[:, 1]) - 1.5 * h2)
        b2 = float(np.max(sample[:, 1]) + 1.5 * h2)
    else:
        (a1, b1), (a2, b2) = _range_x(range_x)

    x1 = np.linspace(a1, b1, m1)
    x2 = np.linspace(a2, b2, m2)
    gcounts = np.asarray(
        _lbtwod(
            np.ascontiguousarray(sample[:, 0]),
            np.ascontiguousarray(sample[:, 1]),
            a1,
            a2,
            b1,
            b2,
            m1,
            m2,
        ),
        dtype=np.float64,
    ).reshape(m1, m2)

    length1, kappa1 = _margin(h1, a1, b1, m1)
    length2, kappa2 = _margin(h2, a2, b2, m2)
    if min(length1, length2) == 0:
        warnings.warn(
            "Binning grid too coarse for current (small) bandwidth: consider increasing 'gridsize'",
            stacklevel=2,
        )
    kernel = np.outer(kappa1, kappa2) / n

    pad1 = _fft_size(m1 + length1)
    pad2 = _fft_size(m2 + length2)
    weights = np.zeros((pad1, pad2), dtype=np.float64)
    weights[: length1 + 1, : length2 + 1] = kernel
    if length1:
        weights[pad1 - length1 : pad1, : length2 + 1] = kernel[:0:-1, :]
    if length2:
        weights[:, pad2 - length2 : pad2] = weights[:, length2:0:-1]

    counts = np.zeros((pad1, pad2), dtype=np.float64)
    counts[:m1, :m2] = gcounts
    fhat = np.fft.ifft2(np.fft.fft2(weights) * np.fft.fft2(counts)).real[:m1, :m2]
    fhat = fhat * (fhat > 0.0)
    return {"x1": x1, "x2": x2, "fhat": fhat}


def _bandwidth(bandwidth) -> tuple[float, float]:
    values = np.asarray(bandwidth, dtype=np.float64).reshape(-1)
    if values.size == 1:
        values = np.repeat(values, 2)
    if values.size != 2 or not np.all(np.isfinite(values)) or np.any(values <= 0.0):
        raise ValueError("'bandwidth' must be strictly positive")
    return float(values[0]), float(values[1])


def _gridsize(gridsize) -> tuple[int, int]:
    values = np.asarray(gridsize, dtype=np.float64).reshape(-1)
    if values.size != 2:
        raise ValueError("gridsize must contain two counts")
    counts = []
    for value in values:
        if not np.isfinite(value) or value < 2 or int(value) != value:
            raise ValueError("gridsize must be two integers of at least 2")
        counts.append(int(value))
    return counts[0], counts[1]


def _range_x(range_x) -> tuple[tuple[float, float], tuple[float, float]]:
    try:
        first, second = range_x
    except (TypeError, ValueError) as exc:
        raise ValueError("range_x must be a list of two min/max pairs") from exc
    return _ends(first), _ends(second)


def _ends(pair) -> tuple[float, float]:
    values = np.asarray(pair, dtype=np.float64).reshape(-1)
    if values.size != 2 or not np.all(np.isfinite(values)):
        raise ValueError("each range_x entry must contain a finite minimum and maximum")
    low = float(values[0])
    high = float(values[1])
    if not high > low:
        raise ValueError("range_x must be strictly increasing")
    return low, high


def _margin(bandwidth: float, low: float, high: float, count: int) -> tuple[int, np.ndarray]:
    length = min(
        math.floor(_TAU * bandwidth * (count - 1) / (high - low)),
        count - 1,
    )
    lags = np.arange(length + 1, dtype=np.float64)
    factor = (high - low) / (bandwidth * (count - 1))
    weights = _dnorm(lags * factor) / bandwidth
    total = float(np.sum(np.concatenate([weights, weights[:0:-1]])) * factor * bandwidth)
    return length, weights / total


def _dnorm(z: np.ndarray) -> np.ndarray:
    return np.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _fft_size(count: int) -> int:
    """Smallest power of two at least ``count``, matching R's ``2^ceiling(log/log(2))``."""
    return 2 ** math.ceil(math.log(count) / math.log(2))
