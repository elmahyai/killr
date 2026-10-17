"""Quantile curve for an extreme-value plot (lmom::evdistq).

R draws the curve over the plot region's x-range, ``par("usr")[1:2]``, not over
a probability grid. The grid is ``seq(usr[1], usr[2], length = npoints)`` in
reduced variates, and the curve is ``qfunc(exp(-exp(-grid)), para)``.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ._plotting import LTY_TO_LINESTYLE, current_axes


def evdistq(qfunc, para=None, npoints=101, usr=None, ax=None, col="black",
            lty="solid", lwd=1.0):
    """Draw the quantile curve on the current axes and return ``(grid, curve)``.

    ``usr`` is the plot region's x-limits (R's ``par("usr")[1:2]``). When it is
    not given, the x-limits of the axes are used, as R uses the current plot.
    ``grid`` is the reduced variate at each point and ``curve`` the quantile.
    """
    axes = current_axes(ax)
    if usr is None:
        usr = axes.get_xlim()
    style = _line_style(lty)
    xval, yval = evdistq_data(qfunc, para, npoints, usr)
    axes.plot(xval, yval, color=col, linestyle=style, linewidth=float(lwd))
    return xval, yval


def evdistq_data(qfunc, para, npoints, usr):
    """The grid and the quantile curve over ``usr``. Nothing is drawn here."""
    lo, hi = float(usr[0]), float(usr[1])
    xval = np.linspace(lo, hi, int(npoints))
    pval = np.exp(-np.exp(-xval))
    yval = _quantile(qfunc, pval, para)
    return xval, yval


def _quantile(qfunc, pval, para):
    """R: qfunc(pval) when para is missing, do.call for a named list, else qfunc(pval, para)."""
    if para is None:
        return np.asarray(qfunc(pval), dtype=float)
    if isinstance(para, Mapping):
        return np.asarray(qfunc(pval, **para), dtype=float)
    return np.asarray(qfunc(pval, para), dtype=float)


def _line_style(lty) -> str:
    key = str(lty)
    if key not in LTY_TO_LINESTYLE:
        raise NotImplementedError(f"line type {lty!r} is not translated")
    return LTY_TO_LINESTYLE[key]
