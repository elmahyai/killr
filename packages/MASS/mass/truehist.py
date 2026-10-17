"""Density-scaled histograms (MASS ``truehist``)."""

from __future__ import annotations

import warnings

import numpy as np

from mass.hist_scott import _pretty_range, nclass_scott


def _nclass_fd(values: np.ndarray) -> int:
    q25, q75 = np.percentile(values, [25, 75])
    h = 2 * (q75 - q25) * values.size ** (-1 / 3)
    if h <= 0:
        return 1
    return max(1, int(np.ceil((values.max() - values.min()) / h)))


def truehist(
    data,
    nbins="Scott",
    h=None,
    x0=None,
    breaks=None,
    prob: bool = True,
    xlim=None,
    ymax=None,
    col="cyan",
    xlab=None,
    bty="n",
    ax=None,
    **kwargs,
):
    """Draw a histogram whose bar heights are counts or densities.

    The returned dictionary contains the computed breaks and estimates as
    well as the Matplotlib axes, which is useful when composing figures.
    """
    import matplotlib.pyplot as plt

    values = np.asarray(data, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]
    if values.size == 0:
        raise ValueError("'data' contains no finite values")
    if xlab is None:
        xlab = "data"
    if breaks is None:
        if h is None:
            if isinstance(nbins, str):
                key = nbins.casefold()
                if key == "scott":
                    nbins = nclass_scott(values)
                elif key in {"freedman-diaconis", "fd"}:
                    nbins = _nclass_fd(values)
                else:
                    raise ValueError("unknown binning rule")
            nbins = int(nbins)
            if not np.isfinite(nbins) or nbins <= 0:
                raise ValueError("'nbins' must result in a positive integer")
            h = float(np.diff(_pretty_range(values.min(), values.max(), nbins))[0])
        if not np.isfinite(h) or h <= 0:
            raise ValueError("'h' must be strictly positive")
        if x0 is None:
            x0 = -h / 1000
        first = int(np.floor((values.min() - x0) / h))
        last = int(np.ceil((values.max() - x0) / h))
        breaks = x0 + h * np.arange(first, last + 1)
    else:
        breaks = np.asarray(breaks, dtype=float)
    if breaks.size < 2 or np.any(np.diff(breaks) <= 0):
        raise ValueError("'breaks' must be strictly increasing")
    if values.min() < breaks[0] or values.max() > breaks[-1]:
        raise ValueError("'breaks' do not cover the data")
    widths = np.diff(breaks)
    if not prob and np.std(widths) > np.mean(widths) / 1000:
        warnings.warn("uneven breaks with 'prob = FALSE' will give a misleading plot", RuntimeWarning)
    counts, _ = np.histogram(values, bins=breaks)
    est = counts / (widths * values.size) if prob else counts.astype(float)
    if xlim is None:
        xlim = [breaks[0], breaks[-1]]
    if ymax is None:
        ymax = float(np.max(est))
    created = ax is None
    if created:
        _, ax = plt.subplots()
    plot_kwargs = dict(kwargs)
    plot_kwargs.pop("main", None)
    ax.bar(
        breaks[:-1],
        est,
        width=widths,
        align="edge",
        color=col,
        edgecolor=plot_kwargs.pop("border", None),
        **plot_kwargs,
    )
    ax.set_xlim(xlim)
    ax.set_ylim(0, ymax)
    ax.set_xlabel(xlab)
    ax.set_ylabel("" if prob else "Frequency")
    if bty == "n":
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
    if created:
        ax.figure.tight_layout()
    return {"breaks": breaks, "est": est, "axes": ax}
