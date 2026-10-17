"""Scott-rule histogram (MASS hist.scott)."""

from __future__ import annotations

import math
import sys
import warnings
from typing import Any

import numpy as np

from mass.errors import MassError

_EPS = sys.float_info.epsilon
_DBL_MIN = sys.float_info.min
_DBL_MAX = sys.float_info.max
_ROUNDING_EPS = 1e-10


def _seq_length(start: float, stop: float, length_out: int) -> list[float]:
    if length_out <= 0:
        return []
    if length_out == 1:
        return [float(start)]
    if start == stop:
        return [float(start)] * length_out
    step = (stop - start) / (length_out - 1)
    values = [float(start + i * step) for i in range(length_out)]
    values[0] = float(start)
    values[-1] = float(stop)
    return values


def _r_pretty(
    lo: float,
    up: float,
    ndiv: int,
    min_n: int,
    shrink_sml: float,
    high_u_fact: tuple[float, float, float],
    eps_correction: int,
    return_bounds: bool,
) -> tuple[float, float, int, float]:
    h, h5, f_min = high_u_fact
    lo_in = lo
    up_in = up
    span = up_in - lo_in
    if span == 0 and up_in == 0:
        cell = 1.0
        small = True
    else:
        cell = max(abs(lo_in), abs(up_in))
        unit_bound = 1 / (1 + h) if h5 >= 1.5 * h + 0.5 else 1.5 / (1 + h5)
        unit_bound = (1 + unit_bound) * max(1, ndiv) * _EPS
        small = span < cell * unit_bound * 3
    if small:
        if cell > 10:
            cell = 9 + cell / 10
        cell *= shrink_sml
        if min_n > 1:
            cell /= min_n
    else:
        cell = span
        if math.isfinite(span):
            if ndiv > 1:
                cell /= ndiv
        elif ndiv >= 2:
            cell = up_in / ndiv - lo_in / ndiv
    smallest = f_min * _DBL_MIN
    if smallest == 0:
        smallest = _DBL_MIN
    if cell < smallest:
        cell = smallest
    elif cell > _DBL_MAX / 1.25:
        cell = _DBL_MAX / 1.25
    base = 10.0 ** math.floor(math.log10(cell))
    unit = base
    candidate = 2 * base
    if candidate - cell < h * (cell - unit):
        unit = candidate
        candidate = 5 * base
        if candidate - cell < h5 * (cell - unit):
            unit = candidate
            candidate = 10 * base
            if candidate - cell < h * (cell - unit):
                unit = candidate
    ns = math.floor(lo_in / unit + _ROUNDING_EPS)
    nu = math.ceil(up_in / unit - _ROUNDING_EPS)
    if eps_correction and (eps_correction > 1 or not small):
        lo_adj = lo * (1 - _EPS) if lo_in != 0 else -_DBL_MIN
        up_adj = up * (1 + _EPS) if up_in != 0 else _DBL_MIN
    else:
        lo_adj = lo
        up_adj = up
    while ns * unit > lo_adj + _ROUNDING_EPS * unit:
        ns -= 1
    while not math.isfinite(ns * unit):
        ns += 1
    while nu * unit < up_adj - _ROUNDING_EPS * unit:
        nu += 1
    while not math.isfinite(nu * unit):
        nu -= 1
    intervals = int(0.5 + nu - ns)
    if intervals < min_n:
        extra = min_n - intervals
        if lo_in == 0 and ns == 0 and up_in != 0:
            nu += extra
        elif up_in == 0 and nu == 0 and lo_in != 0:
            ns -= extra
        elif ns >= 0:
            nu += extra // 2
            ns -= extra // 2 + extra % 2
        else:
            ns -= extra // 2
            nu += extra // 2 + extra % 2
        ndiv = min_n
    else:
        ndiv = intervals
    if return_bounds:
        if ns * unit < lo:
            lo = ns * unit
        if nu * unit > up:
            up = nu * unit
    else:
        lo = ns
        up = nu
    return lo, up, ndiv, unit


def _pretty_range(lo: float, hi: float, n: int, *, min_n: int = 1) -> np.ndarray:
    high_u_bias = 1.5
    u5_bias = 0.5 + 1.5 * high_u_bias
    lo_out, up_out, ndiv, _unit = _r_pretty(
        float(lo),
        float(hi),
        int(n),
        int(min_n),
        0.75,
        (high_u_bias, u5_bias, 2**-20),
        0,
        True,
    )
    breaks = _seq_length(lo_out, up_out, ndiv + 1)
    if ndiv:
        delta = abs(up_out - lo_out) / ndiv
        breaks = [0.0 if abs(v) < 1e-14 * delta else v for v in breaks]
    return np.asarray(breaks, dtype=float)


def nclass_scott(x) -> int:
    """Suggested class count from Scott's rule (grDevices)."""
    values = np.asarray(x, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    n = values.size
    if n == 0:
        raise MassError("'x' has length zero")
    h = 3.5 * math.sqrt(float(np.var(values, ddof=1))) * n ** (-1.0 / 3.0)
    if h > 0:
        return max(1, int(math.ceil((float(values.max()) - float(values.min())) / h)))
    return 1


def _hist_counts(values: np.ndarray, breaks: np.ndarray) -> np.ndarray:
    counts = np.zeros(len(breaks) - 1, dtype=int)
    for value in values:
        if value < breaks[0] or value > breaks[-1]:
            continue
        if value == breaks[0]:
            counts[0] += 1
            continue
        bin_index = int(np.searchsorted(breaks, value, side="left") - 1)
        counts[bin_index] += 1
    return counts


def _hist_numeric(
    x,
    nclass: int,
    *,
    plot: bool = True,
    prob: bool = True,
    xlab: str | None = None,
    ax=None,
    **kwargs: Any,
):
    """Build an R hist.default object for a Scott class count."""
    del prob  # MASS passes prob=; R hist ignores it when plot=FALSE.
    values = np.asarray(x, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    n = int(values.size)
    if n == 0:
        raise MassError("'x' must be numeric")
    if nclass < 1:
        raise MassError("invalid number of 'breaks'")
    lo = float(values.min())
    hi = float(values.max())
    breaks = _pretty_range(lo, hi, nclass, min_n=1)
    n_b = breaks.size
    if n_b <= 1:
        raise MassError(f"hist.default: pretty() error, breaks={breaks!r}")
    widths = np.diff(breaks)
    equidist = True
    counts = _hist_counts(values, breaks)
    if counts.sum() < n:
        raise MassError("some 'x' not counted; maybe 'breaks' do not span range of 'x'")
    density = counts / (n * widths)
    mids = 0.5 * (breaks[:-1] + breaks[1:])
    xname = xlab if xlab is not None else "x"
    result = {
        "breaks": breaks,
        "counts": counts,
        "density": density,
        "mids": mids,
        "xname": xname,
        "equidist": equidist,
        "n": n,
    }
    if plot:
        import matplotlib.pyplot as plt

        created = ax is None
        if created:
            _, ax = plt.subplots()
        ax.bar(
            breaks[:-1],
            density,
            width=widths,
            align="edge",
            facecolor=kwargs.pop("col", kwargs.pop("color", "lightgray")),
            edgecolor=kwargs.pop("border", "black"),
            **kwargs,
        )
        ax.set_xlabel(xname)
        ax.set_ylabel("Density")
        main = kwargs.pop("main", f"Histogram of {xname}")
        if main:
            ax.set_title(main)
        if created:
            plt.tight_layout()
        result["axes"] = ax
    elif kwargs:
        unused = ", ".join(repr(key) for key in kwargs)
        warnings.warn(f"arguments {unused} are not made use of", RuntimeWarning, stacklevel=3)
    return result


def hist_scott(
    x,
    prob: bool = True,
    xlab: str | None = None,
    plot: bool = True,
    ax=None,
    **kwargs: Any,
):
    """Histogram with Scott bin-width selection."""
    if xlab is None:
        xlab = "x"
    nclass = nclass_scott(x)
    return _hist_numeric(x, nclass, plot=plot, prob=prob, xlab=xlab, ax=ax, **kwargs)
