"""Freedman-Diaconis histogram (MASS hist.FD) and grDevices nclass.FD.

``hist.FD(x)`` is ``hist(x, nclass.FD(x), prob = prob, xlab = xlab)``. The
class count, the pretty breaks, and the fuzzed binning follow R's
``hist.default``. The drawing uses Matplotlib, and the axis limits are the
ones R's ``xaxs = "r"`` gives: each range is extended by 4 percent.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.hist_scott import _pretty_range

_R_EXPAND = 0.04


def _extend(lo: float, hi: float, f: float = _R_EXPAND) -> tuple[float, float]:
    """R's ``extendrange(c(lo, hi), f = f)``, which sets the plot axis limits."""
    span = hi - lo
    return lo - f * span, hi + f * span


def signif_r(values, digits: int = 5) -> np.ndarray:
    """``signif(values, digits)`` with decimal rounding of the printed value."""
    out = np.array(values, dtype=float, copy=True)
    for i, value in enumerate(out):
        if math.isfinite(value) and value != 0.0:
            out[i] = float(f"{value:.{digits - 1}e}")
    return out


def nclass_fd(x, digits: int = 5) -> int:
    """Number of classes by the Freedman-Diaconis rule (grDevices ``nclass.FD``)."""
    values = np.asarray(x, dtype=float).reshape(-1)
    if not np.all(np.isfinite(values)):
        raise MassError("missing value where TRUE/FALSE needed")
    rounded = signif_r(values, digits)
    q1, q3 = np.quantile(rounded, [0.25, 0.75])
    h = 2.0 * (q3 - q1)
    if h == 0:
        sorted_vals = np.sort(rounded)
        al = 1.0 / 4.0
        al_min = 1.0 / 512.0
        while h == 0:
            al = al / 2.0
            if al < al_min:
                break
            lo, hi = np.quantile(sorted_vals, [al, 1.0 - al])
            h = (hi - lo) / (1.0 - 2.0 * al)
    if h == 0:
        h = 3.5 * math.sqrt(float(np.var(values, ddof=1)))
    if h > 0:
        span = float(values.max() - values.min())
        return int(math.ceil(span / h * len(values) ** (1.0 / 3.0)))
    return 1


def _bin_count(x: np.ndarray, fuzzy: np.ndarray) -> np.ndarray:
    """R's ``C_BinCount`` with ``right = TRUE`` and ``include.lowest = TRUE``."""
    nb = fuzzy.size
    idx = np.searchsorted(fuzzy, x, side="left") - 1
    idx[x == fuzzy[0]] = 0
    valid = (x >= fuzzy[0]) & (x <= fuzzy[-1]) & (idx >= 0) & (idx <= nb - 2)
    return np.bincount(idx[valid], minlength=nb - 1).astype(int)


def r_hist(values, nclass: int) -> dict[str, Any]:
    """The data part of R's ``hist(x, nclass)`` with ``plot = FALSE``."""
    x = np.asarray(values, dtype=float).reshape(-1)
    x = x[np.isfinite(x)]
    n = int(x.size)
    if n == 0:
        raise MassError("invalid length(x)")
    if nclass < 1:
        raise MassError("invalid number of 'breaks'")
    breaks = _pretty_range(float(x.min()), float(x.max()), int(nclass), min_n=1)
    n_b = breaks.size
    if n_b <= 1:
        raise MassError("hist.default: pretty() error")
    h = np.diff(breaks)
    if n_b > 5:
        scale = float(np.median(h))
    elif n_b <= 3:
        scale = float(x.max() - x.min())
    else:
        scale = float(np.min(h[h > 0]))
    diddle = 1e-7 * scale
    fuzz = np.full(n_b, diddle)
    fuzz[0] = -diddle
    counts = _bin_count(x, breaks + fuzz)
    if counts.sum() < n:
        raise MassError("some 'x' not counted; maybe 'breaks' do not span range of 'x'")
    density = counts / (n * h)
    mids = 0.5 * (breaks[1:] + breaks[:-1])
    # Breaks come from pretty(), so R's use.br is FALSE and equidist is TRUE.
    return {
        "breaks": breaks,
        "counts": counts,
        "density": density,
        "mids": mids,
        "n": n,
        "equidist": True,
    }


def hist_fd(
    x,
    prob: bool = True,
    xlab: str | None = None,
    plot: bool = True,
    ax=None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Histogram whose class count follows the Freedman-Diaconis rule."""
    if xlab is None:
        xlab = "x"
    values = np.asarray(x, dtype=float).reshape(-1)
    nclass = nclass_fd(values)
    result = r_hist(values, nclass)
    if not plot:
        return result
    import matplotlib.pyplot as plt

    breaks = result["breaks"]
    heights = result["density"] if prob else result["counts"].astype(float)
    created = ax is None
    if created:
        _, ax = plt.subplots()
    color = kwargs.pop("col", "lightgray")
    border = kwargs.pop("border", "black")
    main = kwargs.pop("main", f"Histogram of {xlab}")
    ax.bar(
        breaks[:-1],
        heights,
        width=np.diff(breaks),
        align="edge",
        color=color,
        edgecolor=border,
    )
    xlim = _extend(float(breaks[0]), float(breaks[-1]))
    ylim = _extend(min(0.0, float(heights.min())), max(0.0, float(heights.max())))
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_xlabel(xlab)
    ax.set_ylabel("Density" if prob else "Frequency")
    if main:
        ax.set_title(main)
    if created:
        ax.figure.tight_layout()
    result.update({"xlim": xlim, "ylim": ylim, "axes": ax})
    return result
