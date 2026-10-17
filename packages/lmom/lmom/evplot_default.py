"""Extreme-value plot, default method (lmom::evplot.default).

``evplot_plan`` does the R work before drawing: the plotting positions, the
limits (R's ``xlim`` and ``ylim`` widened by the quantile curve), the quantile
curve on the plot region, and the return-period ticks. ``evplot_default``
draws the plan with ``killplot.extreme_value_plot``.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ._killplot import killplot_function
from ._plotting import (
    current_axes,
    extend_range,
    ppoints,
    r_number_string,
    sorted_non_missing,
)

XLAB = r"Reduced variate,  $-\log(-\log(F))$"
YLAB = "Quantile"

_RP_LAB = np.array([2, 5, 10, 20, 50, 100, 200, 500, 1000, 10000, 100000,
                    1e6, 1e7, 1e8], dtype=float)


def evplot_default(y=None, qfunc=None, para=None, npoints=101, plim=None,
                   xlim=(-2, 5), ylim=None, type=None, xlab=XLAB, ylab=YLAB,
                   rp_axis=True, ax=None, **kwargs):
    """Draw an extreme-value plot and return the plotted data, as R's ``evplot.default`` does."""
    if kwargs:
        raise TypeError(f"extra graphics arguments are not translated: {sorted(kwargs)}")
    ax = current_axes(ax)
    ax.cla()
    plan = evplot_plan(y, qfunc=qfunc, para=para, npoints=npoints, plim=plim,
                       xlim=xlim, ylim=ylim, type_=type, rp_axis=rp_axis)
    extreme_value_plot = killplot_function("extreme_value_plot", "extreme_value_plot")
    points = (plan["x"], plan["y"]) if plan["has_points"] else None
    extreme_value_plot(ax, plan["usr_x"], plan["usr_y"], xlab, ylab, points=points,
                       point_type=plan["type"], curve=plan["curve"],
                       return_axis=plan["rp_axis"])
    return plan


def evplot_plan(y=None, *, qfunc=None, para=None, npoints=101, plim=None,
                xlim=(-2, 5), ylim=None, type_=None, rp_axis=True):
    """The data behind an extreme-value plot. Nothing is drawn here."""
    if plim is not None:
        # R: xlim <- c(-log(-log(plim))). This is one number, so the plot fails later.
        xlim_v = (float(-np.log(-np.log(plim))),)
    else:
        xlim_v = tuple(float(v) for v in xlim)

    missing_ylim = ylim is None
    ylim_v = (0.0, 1.0) if missing_ylim else tuple(float(v) for v in ylim)

    if y is None:
        xx = np.array([0.0])
        yy = np.array([0.0])
        ptype = "n"
        has_points = False
    else:
        yy = sorted_non_missing(y)
        lyy = yy.size
        if lyy == 0:
            raise ValueError("evplot needs at least one non-missing value")
        xx = -np.log(-np.log(ppoints(lyy, 0.44)))
        if missing_ylim:
            ylim_v = (min(0.0, float(yy[0])), float(yy[-1]))
        if plim is None:
            xlim_v = (min(xlim_v[0], float(xx[0])), max(xlim_v[1], float(xx[lyy - 1])))
        ptype = "p" if type_ is None else type_
        has_points = True

    if qfunc is not None and missing_ylim:
        pval = np.exp(-np.exp(-np.array([min(xlim_v), max(xlim_v)])))
        yval = _quantile(qfunc, pval, para)
        both = np.concatenate([np.asarray(ylim_v, dtype=float), yval])
        ylim_v = (float(both.min()), float(both.max()))

    # R fails in plot.window when xlim is not two numbers.
    if len(xlim_v) != 2:
        raise ValueError("invalid 'xlim' value")
    usr_x = extend_range(*xlim_v)
    usr_y = extend_range(*ylim_v)

    curve = None
    if qfunc is not None:
        xval = np.linspace(usr_x[0], usr_x[1], int(npoints))
        pval = np.exp(-np.exp(-xval))
        curve = (xval, _quantile(qfunc, pval, para))

    rp = None
    if rp_axis:
        tic = -np.log(-np.log(1 - 1 / _RP_LAB))
        keep = (tic >= usr_x[0]) & (tic <= usr_x[1])
        tic = tic[keep]
        labels = [r_number_string(v) for v in _RP_LAB[keep]]
        ypos = usr_y[0] + (usr_y[1] - usr_y[0]) * 0.05
        text_x = float((tic.min() + tic.max()) * 0.5) if tic.size else float("nan")
        rp = {"tic": tic, "lab": labels, "ypos": float(ypos), "text_x": text_x}

    return {
        "x": xx,
        "y": yy,
        "has_points": has_points,
        "type": ptype,
        "usr_x": usr_x,
        "usr_y": usr_y,
        "curve": curve,
        "rp_axis": rp,
    }


def _quantile(qfunc, pval, para):
    """R: qfunc(pval), do.call(qfunc, c(list(pval), para)), or qfunc(pval, para)."""
    if para is None:
        return np.asarray(qfunc(pval), dtype=float)
    if isinstance(para, Mapping):
        return np.asarray(qfunc(pval, **para), dtype=float)
    return np.asarray(qfunc(pval, para), dtype=float)
