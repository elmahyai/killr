"""Equal-scale scatter plotting (MASS ``eqscplot``)."""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np


def eqscplot(
    x,
    y=None,
    ratio: float = 1,
    tol: float = 0.04,
    uin=None,
    ax=None,
    **kwargs,
):
    """Plot points with equal physical units per unit on both axes.

    ``x`` may be an ``n x 2`` array or a mapping with ``x`` and ``y`` keys,
    matching the two convenient input forms accepted by MASS.
    """
    import matplotlib.pyplot as plt

    if isinstance(x, Mapping):
        y = x["y"]
        x = x["x"]
        xlab0, ylab0 = "x", "y"
    else:
        values = np.asarray(x)
        if y is None and values.ndim == 2 and values.shape[1] >= 2:
            x, y = values[:, 0], values[:, 1]
            labels = getattr(values, "columns", None)
            xlab0 = str(labels[0]) if labels is not None else ""
            ylab0 = str(labels[1]) if labels is not None else ""
        elif y is None:
            raise TypeError("y is required unless x is an n x 2 array")
        else:
            xlab0, ylab0 = "x", "y"

    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.size != y.size:
        raise ValueError("'x' and 'y' lengths differ")
    finite_x = x[np.isfinite(x)]
    finite_y = y[np.isfinite(y)]
    if finite_x.size == 0 or finite_y.size == 0:
        raise ValueError("need finite values in both 'x' and 'y'")

    xlim = np.asarray(kwargs.pop("xlim", [finite_x.min(), finite_x.max()]), dtype=float)
    ylim = np.asarray(kwargs.pop("ylim", [finite_y.min(), finite_y.max()]), dtype=float)
    if xlim.size != 2 or ylim.size != 2:
        raise ValueError("'xlim' and 'ylim' must have length two")
    midx, midy = np.mean(xlim), np.mean(ylim)
    xspan, yspan = abs(np.diff(xlim)[0]), abs(np.diff(ylim)[0])
    xlim = midx + (1 + tol) * 0.5 * np.array([-xspan, xspan])
    ylim = midy + (1 + tol) * 0.5 * np.array([-yspan, yspan])

    xlab = kwargs.pop("xlab", xlab0)
    ylab = kwargs.pop("ylab", ylab0)
    created = ax is None
    if created:
        _, ax = plt.subplots()
    # Axes position is the closest Matplotlib equivalent to R's physical pin.
    fig = ax.figure
    fig.canvas.draw()
    bbox = ax.get_window_extent().transformed(fig.dpi_scale_trans.inverted())
    oxuin, oyuin = bbox.width / np.diff(xlim)[0], bbox.height / np.diff(ylim)[0]
    xuin, yuin = oxuin, oyuin
    if uin is None:
        if yuin > xuin * ratio:
            yuin = xuin * ratio
        else:
            xuin = yuin / ratio
    else:
        uin = np.asarray(uin, dtype=float).reshape(-1)
        if uin.size == 1:
            uin = uin * np.array([1.0, ratio])
        if uin.size != 2 or np.any(np.array([xuin, yuin]) < uin):
            raise ValueError("'uin' is too large to fit plot in")
        xuin, yuin = uin
    xlim = midx + np.array([-1.0, 1.0]) * xspan * 0.5 * (1 + tol)
    ylim = midy + np.array([-1.0, 1.0]) * yspan * 0.5 * (1 + tol)
    # Equal aspect preserves the requested ratio while allowing Matplotlib
    # to choose the final limits from the physical axes dimensions.
    ax.set_aspect(float(ratio), adjustable="box")
    ax.plot(x, y, **kwargs)
    ax.set_xlim(xlim)
    ax.set_ylim(ylim)
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    if created:
        fig.tight_layout()
    return ax
