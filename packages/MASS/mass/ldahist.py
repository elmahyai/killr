"""Histograms and densities of one linear discriminant, by group (MASS ldahist).

``ldahist`` takes the projected values of one discriminant and the group of
each value. The data part is ``ldahist_data``: the class breaks, the
per-group histogram heights, and the per-group kernel density on a 200-point
grid. ``ldahist`` draws those with Matplotlib.

The density follows R's ``stats::density.default`` with a Gaussian kernel,
R 4.4 and later coordinates, linear binning, and the FFT convolution.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.hist_fd import _extend
from mass.hist_scott import _pretty_range
from mass.width_sj import width_sj

_R_PALETTE = ["black", "#DF536B", "#61D04F", "#2297E6", "#28E2E5", "#CD0BBC", "#F5C710", "gray62"]
_TYPES = ("histogram", "density", "both")


def _match_type(value: str) -> str:
    text = str(value)
    if text in _TYPES:
        return text
    hits = [item for item in _TYPES if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    raise MassError("'arg' should be one of " + ", ".join(repr(item) for item in _TYPES))


def _cut_counts(values: np.ndarray, breaks: np.ndarray) -> np.ndarray:
    """``tabulate(cut(values, breaks, include.lowest = TRUE))``: right-closed bins."""
    nb = breaks.size - 1
    idx = np.searchsorted(breaks, values, side="left") - 1
    idx[values == breaks[0]] = 0
    valid = (values >= breaks[0]) & (values <= breaks[-1]) & (idx >= 0) & (idx < nb)
    return np.bincount(idx[valid], minlength=nb).astype(float)


def _bin_dist(x: np.ndarray, w: np.ndarray, xlo: float, xhi: float, n: int) -> np.ndarray:
    """Linear binning onto ``2 * n`` cells, as R's ``C_BinDist``."""
    y = np.zeros(2 * n)
    xdelta = (xhi - xlo) / (n - 1)
    ixmax = n - 2
    xpos = (x - xlo) / xdelta
    ix = np.floor(xpos).astype(np.int64)
    fx = xpos - ix
    inside = (ix >= 0) & (ix <= ixmax)
    np.add.at(y, ix[inside], w[inside] * (1.0 - fx[inside]))
    np.add.at(y, ix[inside] + 1, w[inside] * fx[inside])
    low = ix == -1
    if np.any(low):
        y[0] += float(np.sum(w[low] * fx[low]))
    high = ix == ixmax + 1
    np.add.at(y, ix[high], w[high] * (1.0 - fx[high]))
    return y


def _density_gaussian(x: np.ndarray, bw: float, from_: float, to: float, n_user: int = 200) -> tuple[np.ndarray, np.ndarray]:
    """``density(x, n = n_user, bw = bw, from = from_, to = to)`` for a Gaussian kernel."""
    nx = x.size
    weights = np.full(nx, 1.0 / nx)
    n = max(n_user, 512)
    if n > 512:
        n = 2 ** int(math.ceil(math.log2(n)))
    ext = 4.0
    lo = from_ - ext * bw
    up = to + ext * bw
    y = _bin_dist(x, weights, lo, up, n)
    kords = np.linspace(0.0, (2 * n - 1) / (n - 1) * (up - lo), 2 * n)
    kords[n + 1 : 2 * n] = -kords[n - 1 : 0 : -1]
    kern = np.exp(-0.5 * (kords / bw) ** 2) / (bw * math.sqrt(2.0 * math.pi))
    conv = np.fft.ifft(np.fft.fft(y) * np.conj(np.fft.fft(kern))).real
    dens = np.maximum(0.0, conv[:n])
    xords = np.linspace(lo, up, n)
    grid = np.linspace(from_, to, n_user)
    return grid, np.interp(grid, xords, dens)


def _bin_breaks(
    data: np.ndarray,
    nbins: int,
    h: float | None,
    x0: float | None,
    breaks: np.ndarray | None,
) -> tuple[np.ndarray, float | None]:
    if breaks is not None:
        return np.asarray(breaks, dtype=float), h
    if h is None:
        pretty = _pretty_range(float(data.min()), float(data.max()), int(nbins), min_n=int(nbins) // 3)
        h = float(pretty[1] - pretty[0])
    if x0 is None:
        x0 = -h / 1000.0
    first = math.floor((float(data.min()) - x0) / h)
    last = math.ceil((float(data.max()) - x0) / h)
    return x0 + h * np.arange(first, last + 1, dtype=float), h


def ldahist_data(
    data,
    g,
    nbins: int = 25,
    h: float | None = None,
    x0: float | None = None,
    breaks=None,
    xlim=None,
    ymax: float = 0.0,
    width: float | None = None,
    type: str = "histogram",
) -> dict[str, Any]:
    """Breaks, per-group histogram heights, and per-group densities of ``data``."""
    kind = _match_type(type)
    values = np.asarray(data, dtype=float).reshape(-1)
    labels = np.asarray(g).reshape(-1)
    keep = ~np.isnan(values)
    values = values[keep]
    labels = labels[keep]
    groups = sorted({str(item) for item in labels})
    label_str = np.asarray([str(item) for item in labels])
    counts = {grp: int(np.sum(label_str == grp)) for grp in groups}
    groups = [grp for grp in groups if counts[grp] > 0]

    brk, h_used = _bin_breaks(values, nbins, h, x0, None if breaks is None else np.asarray(breaks, dtype=float))
    if xlim is None:
        xlim = (float(brk[0]), float(brk[-1]))
    xlim = (float(xlim[0]), float(xlim[1]))
    ymax = float(ymax)

    est: dict[str, np.ndarray] = {}
    if kind in ("histogram", "both"):
        if np.any(np.diff(brk) <= 0):
            raise MassError("'breaks' must be strictly increasing")
        if values.min() < brk.min() or values.max() > brk.max():
            raise MassError("'breaks' do not cover the data")
        for grp in groups:
            sel = values[label_str == grp]
            est1 = _cut_counts(sel, brk) / (np.diff(brk) * sel.size)
            ymax = max(ymax, float(np.max(est1)))
            est[grp] = est1

    dens: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    width_used = width
    if kind in ("density", "both"):
        for grp in groups:
            sel = values[label_str == grp]
            # R assigns width inside the loop when it is missing. After that
            # missing(width) is FALSE, so every group reuses the first width.
            if width_used is None:
                width_used = width_sj(sel)
            bw = width_used / 4.0
            grid, dy = _density_gaussian(sel, bw, xlim[0], xlim[1], 200)
            ymax = max(ymax, float(np.max(dy)))
            dens[grp] = (grid, dy)

    return {
        "breaks": brk,
        "h": h_used,
        "xlim": xlim,
        "ymax": ymax,
        "groups": groups,
        "est": est,
        "density": dens,
        "width": width_used,
        "type": kind,
    }


def _r_col(value: Any) -> Any:
    if isinstance(value, (int, float, np.integer, np.floating)):
        idx = int(value)
        return _R_PALETTE[(idx - 1) % len(_R_PALETTE)] if idx > 0 else "white"
    return value


def ldahist(
    data,
    g,
    nbins: int = 25,
    h: float | None = None,
    x0: float | None = None,
    breaks=None,
    xlim=None,
    ymax: float = 0.0,
    width: float | None = None,
    type: str = "histogram",
    sep: bool | None = None,
    col: Any = 5,
    xlab: str = "data",
    bty: str = "n",
    **kwargs: Any,
) -> dict[str, Any]:
    """Draw per-group histograms or densities of one discriminant.

    One panel per group is drawn when ``sep`` is true. The default is true
    for ``histogram`` and ``both``, and false for ``density``.
    """
    import matplotlib.pyplot as plt

    kind = _match_type(type)
    if sep is None:
        sep = kind != "density"
    result = ldahist_data(data, g, nbins=nbins, h=h, x0=x0, breaks=breaks, xlim=xlim, ymax=ymax, width=width, type=kind)
    brk = result["breaks"]
    groups = result["groups"]
    fill = _r_col(col)
    x_lim = _extend(result["xlim"][0], result["xlim"][1])
    y_lim = _extend(0.0, result["ymax"])

    def style(ax, label: str) -> None:
        ax.set_xlim(x_lim)
        ax.set_ylim(y_lim)
        ax.set_xlabel(label)
        ax.set_ylabel("")
        if bty == "n":
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)

    def draw(ax, grp: str) -> None:
        if kind in ("histogram", "both"):
            ax.bar(
                brk[:-1],
                result["est"][grp],
                width=np.diff(brk),
                align="edge",
                color=fill,
                edgecolor="black",
            )
        if kind in ("density", "both"):
            grid, dy = result["density"][grp]
            ax.plot(grid, dy, color="black")

    if sep:
        fig, axes = plt.subplots(len(groups), 1, squeeze=False)
        panels = [axes[i, 0] for i in range(len(groups))]
        for ax, grp in zip(panels, groups):
            style(ax, f"group {grp}")
            draw(ax, grp)
    else:
        fig, ax = plt.subplots()
        panels = [ax]
        style(ax, xlab)
        for grp in groups:
            draw(ax, grp)
    fig.tight_layout()
    result["figure"] = fig
    result["axes"] = panels
    result["xlim_axes"] = x_lim
    result["ylim_axes"] = y_lim
    return result
