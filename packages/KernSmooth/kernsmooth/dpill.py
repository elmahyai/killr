"""Direct plug-in bandwidth for local linear regression, ported from KernSmooth `dpill`."""

from __future__ import annotations

import math

import numpy as np
from blkest import blkest as _blkest
from cp import cp as _cp
from rlbin import rlbin as _rlbin
from sdiag import sdiag as _sdiag
from sstdiag import sstdiag as _sstdiag

from kernsmooth.locpoly import locpoly


def dpill(
    x,
    y,
    blockmax=5,
    divisor=20,
    trim=0.01,
    proptrun=0.05,
    gridsize=401,
    range_x=None,
    truncate=True,
) -> float:
    """Select a bandwidth for local linear regression.

    Mirrors ``KernSmooth::dpill``. Pairs are sorted by ``x`` and trimmed, then
    binned with the ``rlbin`` crate. Blocked quartic fits and Mallows' Cp come
    from ``cp`` and ``blkest``. The pilot smooths are ``locpoly``. The smoother
    diagonals are ``sdiag`` and ``sstdiag``. Returns one bandwidth.
    """
    sample_x = np.asarray(x, dtype=np.float64)
    sample_y = np.asarray(y, dtype=np.float64)
    if sample_x.ndim != 1 or sample_y.ndim != 1:
        raise ValueError("x and y must be one-dimensional")
    if sample_x.shape != sample_y.shape:
        raise ValueError("x and y must have the same length")
    if sample_x.size == 0:
        raise ValueError("x must contain at least one observation")
    if not np.all(np.isfinite(sample_x)) or not np.all(np.isfinite(sample_y)):
        raise ValueError("x and y must be finite")

    order = np.argsort(sample_x, kind="mergesort")
    xs = np.ascontiguousarray(sample_x[order])
    ys = np.ascontiguousarray(sample_y[order])
    kept = _trim(xs.size, _number(trim, "trim"))
    xs = xs[kept]
    ys = ys[kept]
    n = int(xs.size)
    # R's default range.x = range(x) is forced after x has been trimmed.
    if range_x is None:
        a = float(np.min(xs))
        b = float(np.max(xs))
    else:
        a, b = _bounds(range_x)
    if not b > a:
        raise ValueError("range_x must be strictly increasing")

    m = _integer(gridsize, "gridsize")
    if m < 2:
        raise ValueError("gridsize must be at least 2")
    xcounts, ycounts = _rlbin(xs, ys, a, b, m, bool(truncate))
    xcounts = np.asarray(xcounts, dtype=np.float64)
    ycounts = np.asarray(ycounts, dtype=np.float64)

    nmax = _block_count(n, _number(blockmax, "blockmax"), _number(divisor, "divisor"))
    cpvals = np.asarray(_cp(xs, ys, 5, nmax), dtype=np.float64)
    nval = int(np.argmin(cpvals)) + 1
    sigsq_q, _th22_q, th24_q = _blkest(xs, ys, nval, 4)

    gamseh = _pilot_gamma(sigsq_q, th24_q, b - a, n)
    bounds = (a, b)
    second = locpoly(
        xcounts,
        ycounts,
        drv=2,
        bandwidth=gamseh,
        range_x=bounds,
        binned=True,
    )["y"]
    cut = math.floor(_number(proptrun, "proptrun") * m)
    if cut < 0:
        raise ValueError("proptrun must be non-negative")
    th22kn = float(np.sum((second[cut : m - cut] ** 2) * xcounts[cut : m - cut]) / n)

    c3k = 0.5 + 2.0 * math.sqrt(2.0) - (4.0 / 3.0) * math.sqrt(3.0)
    c3k = _r_power(4.0 * c3k / math.sqrt(2.0 * math.pi), 1.0 / 9.0)
    lamseh = c3k * _r_power(
        (sigsq_q**2) * (b - a) / ((th22kn * n) ** 2),
        1.0 / 9.0,
    )
    fitted = locpoly(xcounts, ycounts, bandwidth=lamseh, range_x=bounds, binned=True)["y"]
    delta = (b - a) / (m - 1)
    half = _half_width(lamseh, delta)
    bandwidths = np.array([lamseh], dtype=np.float64)
    halves = np.array([half], dtype=np.int32)
    indic = np.ones(m, dtype=np.int32)
    smooth = np.asarray(
        _sdiag(np.ascontiguousarray(xcounts), delta, bandwidths, halves, indic, 1),
        dtype=np.float64,
    )
    square = np.asarray(
        _sstdiag(np.ascontiguousarray(xcounts), delta, bandwidths, halves, indic, 1),
        dtype=np.float64,
    )

    sigsqn = (
        float(np.sum(ys * ys))
        - 2.0 * float(np.sum(fitted * ycounts))
        + float(np.sum((fitted * fitted) * xcounts))
    )
    sigsqd = (
        n
        - 2.0 * float(np.sum(smooth * xcounts))
        + float(np.sum(square * xcounts))
    )
    sigsqkn = sigsqn / sigsqd
    return _r_power(
        sigsqkn * (b - a) / (2.0 * math.sqrt(math.pi) * th22kn * n),
        1.0 / 5.0,
    )


def _pilot_gamma(sigsq_q: float, th24_q: float, span: float, n: int) -> float:
    gamseh = sigsq_q * span / (abs(th24_q) * n)
    if th24_q < 0.0:
        gamseh = _r_power(3.0 * gamseh / (8.0 * math.sqrt(math.pi)), 1.0 / 7.0)
    if th24_q > 0.0:
        gamseh = _r_power(15.0 * gamseh / (16.0 * math.sqrt(math.pi)), 1.0 / 7.0)
    return gamseh


def _half_width(bandwidth: float, delta: float) -> int:
    width = math.floor(4.0 * bandwidth / delta)
    if width < 0 or width > np.iinfo(np.int32).max:
        raise ValueError("bandwidth is too large for the binning grid")
    return int(width)


def _block_count(n: int, blockmax: float, divisor: float) -> int:
    if divisor <= 0.0:
        raise ValueError("divisor must be positive")
    nmax = max(min(math.floor(n / divisor), blockmax), 1.0)
    count = int(math.trunc(nmax))
    if count < 1:
        raise ValueError("blockmax and divisor produce no blocks")
    return count


def _trim(n: int, trim: float):
    if trim < 0.0:
        raise ValueError("trim must be non-negative")
    drop = math.floor(trim * n)
    if drop < 0 or 2 * drop >= n:
        raise ValueError("trim leaves no observations")
    return slice(drop, n - drop)


def _bounds(range_x) -> tuple[float, float]:
    bounds = np.asarray(range_x, dtype=np.float64)
    if bounds.shape != (2,):
        raise ValueError("range_x must contain two endpoints")
    return float(bounds[0]), float(bounds[1])


def _number(value, name: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number") from error
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def _integer(value, name: str) -> int:
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be an integer") from error
    if not math.isfinite(number) or not number.is_integer():
        raise ValueError(f"{name} must be an integer")
    return int(number)


def _r_power(base: float, exponent: float) -> float:
    if not math.isfinite(base) or base < 0.0:
        return math.nan
    return base**exponent
