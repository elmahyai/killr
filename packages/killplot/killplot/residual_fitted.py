"""Residuals against fitted values, with an optional reference line and point labels.

R draws this chart with lattice (``nlme::plot.lme``, which is ``plot.nls``).
Matplotlib has no single call for it: it needs a light grid, a reference line
given by intercept and slope, and text labels at the flagged points. The caller
decides which points are labelled and what the labels say; this function only
draws them.
"""

from __future__ import annotations

import numpy as np

__all__ = ["residual_fitted_plot"]

_R_GRID = "#D3D3D3"
_R_SYMBOL = "#0080ff"
_R_LINE = "black"
_R_EXPAND = 0.07


def _extended(values):
    """Range of ``values`` extended by 7 percent on each side (lattice's extend.limits)."""
    lo = float(np.min(values))
    hi = float(np.max(values))
    span = hi - lo
    if span == 0:
        span = abs(lo) if lo != 0 else 1.0
    return lo - _R_EXPAND * span, hi + _R_EXPAND * span


def residual_fitted_plot(
    ax,
    x,
    y,
    *,
    xlab,
    ylab,
    abline=None,
    grid=True,
    label_mask=None,
    labels=None,
):
    """Draw ``y`` against ``x`` on ``ax``.

    ``abline`` is None or a pair ``(intercept, slope)``; ``(0, 0)`` is a
    horizontal line at zero. ``label_mask`` is a boolean array of the same
    length as ``x``; the points it selects get the matching entries of
    ``labels`` as text. The axis limits are extended by 7 percent on each side,
    as lattice extends them.
    """
    x = np.asarray(x, dtype=float).reshape(-1)
    y = np.asarray(y, dtype=float).reshape(-1)
    if x.shape != y.shape:
        raise ValueError("x and y must have the same length")

    if grid:
        ax.set_axisbelow(True)
        ax.grid(True, color=_R_GRID, linewidth=0.8)
    ax.scatter(x, y, s=30, facecolors="none", edgecolors=_R_SYMBOL, linewidths=0.8)
    if abline is not None:
        intercept, slope = float(abline[0]), float(abline[1])
        ax.axline((0.0, intercept), slope=slope, color=_R_LINE, linewidth=1.0)
    if label_mask is not None:
        mask = np.asarray(label_mask, dtype=bool).reshape(-1)
        if labels is None or len(labels) != x.size:
            raise ValueError("labels must have one entry per point")
        for i in np.flatnonzero(mask):
            ax.text(x[i], y[i], str(labels[i]), ha="center", va="center")
    # Set the limits from the points only: the reference line's anchor point
    # would otherwise stretch the x axis to zero.
    ax.set_xlim(*_extended(x))
    ax.set_ylim(*_extended(y))
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    return ax
