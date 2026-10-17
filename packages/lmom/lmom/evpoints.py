"""Plotting positions for an extreme-value plot (lmom::evpoints)."""

from __future__ import annotations

import numpy as np

from ._plotting import current_axes, draw_points, ppoints, sorted_non_missing


def evpoints(y, ax=None, **kwargs):
    """Add the sorted data, with Gumbel reduced variates, to the current plot."""
    xval, yval = evpoints_data(y)
    ax = current_axes(ax)
    draw_points(ax, xval, yval, "p", pch=1, col="black", label="points", **kwargs)
    return None


def evpoints_data(y):
    """The reduced variates and sorted values. Missing values are dropped."""
    yval = sorted_non_missing(y)
    n = yval.size
    xval = -np.log(-np.log(ppoints(n, 0.44)))
    return xval, yval
