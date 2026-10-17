"""Add points to an L-moment ratio diagram (lmom::lmrdpoints)."""

from __future__ import annotations

from ._plotting import current_axes, draw_points, point_input


def lmrdpoints(x, y=None, type="p", ax=None, **kwargs):
    """Draw the (tau_3, tau_4) points on the current L-moment ratio diagram.

    ``x`` and ``y`` are the coordinates. With ``y`` absent, ``x`` must be a
    mapping with ``t_3``/``t_4`` or ``tau_3``/``tau_4``, as in R.
    """
    xv, yv = lmrdpoints_data(x, y)
    ax = current_axes(ax)
    draw_points(ax, xv, yv, type, pch=1, col="black", label="points", **kwargs)
    return None


def lmrdpoints_data(x, y=None):
    """The coordinates lmrdpoints draws. This is the data step, with no drawing."""
    return point_input(x, y)
