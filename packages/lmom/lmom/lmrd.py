"""L-moment ratio diagram (lmom::lmrd).

``lmrd_plan`` does the work R does before it draws: it reads the points,
matches the distributions and two-parameter names, works out the plot region,
the curve data, the points inside the region and the legend anchor. ``lmrd``
draws the plan with ``killplot.lmrd_diagram`` and then the data points.

R's ``graphics::plot`` call is replaced by the Matplotlib axes passed in
(or the current axes). R's plot region is the requested range extended by
4 percent on each side, and that extended range is what ``lmrd`` sets on the
axes, so the axis limits match R.
"""

from __future__ import annotations

from collections.abc import Mapping

import numpy as np

from ._killplot import killplot_function
from ._lmrd_table import LMRD_2PAR, LMRD_3PAR, LMRD_COLUMNS, LMRD_DATA
from ._plotting import (
    LTY_TO_LINESTYLE,
    as_logical_false,
    current_axes,
    draw_points,
    extend_range,
    finite_range,
    make_words,
    pin_ratio,
    point_input,
    pmatch,
    recycle,
    unique_in_order,
)

XLAB = r"$L$-skewness"
YLAB = r"$L$-kurtosis"


def lmrd(x=None, y=None, distributions="GLO GEV GPA GNO PE3", twopar=None,
         xlim=None, ylim=None, pch=3, cex=None, col=None, lty=None, lwd=1,
         legend_lmrd=True, xlegend=None, ylegend=None, xlab=XLAB, ylab=YLAB,
         ax=None, **kwargs):
    """Draw an L-moment ratio diagram and return what was drawn, as R's ``lmrd`` does."""
    if kwargs:
        raise TypeError(f"extra graphics arguments are not translated: {sorted(kwargs)}")
    ax = current_axes(ax)
    ax.cla()
    plan = lmrd_plan(
        x, y, distributions=distributions, twopar=twopar, xlim=xlim, ylim=ylim,
        pch=pch, cex=cex, col=col, lty=lty, lwd=lwd, legend_lmrd=legend_lmrd,
        xlegend=xlegend, ylegend=ylegend, pin=pin_ratio(ax),
    )
    lmrd_diagram = killplot_function("lmrd_diagram", "lmrd_diagram")
    lmrd_diagram(ax, plan["usr_x"], plan["usr_y"], plan["curves"], plan["twopar"],
                 plan["legend"], xlab, ylab)
    if plan["points"] is not None:
        pts = plan["points"]
        draw_points(ax, pts["x"], pts["y"], "p", pch=pts["pch"], col=pts["col"],
                    label="points")
    return plan["out"]


def lmrd_plan(x=None, y=None, *, distributions="GLO GEV GPA GNO PE3", twopar=None,
              xlim=None, ylim=None, pch=3, cex=None, col=None, lty=None, lwd=1,
              legend_lmrd=True, xlegend=None, ylegend=None, pin=1.0):
    """The data behind an L-moment ratio diagram. Nothing is drawn here."""
    x_missing = x is None
    if x_missing:
        xv = np.empty(0)
        yv = np.empty(0)
    else:
        xv, yv = point_input(x, y)

    # distributions: R's make.words on a single string, or the vector as given.
    if as_logical_false(distributions):
        dists = []
    elif isinstance(distributions, (str, bool)):
        dists = make_words(distributions)
    else:
        seq = list(distributions)
        dists = make_words(seq) if len(seq) == 1 else [str(d) for d in seq]
    upper = [d.upper() for d in dists]
    idx = []
    unknown = []
    for raw, up in zip(dists, upper):
        if up in LMRD_3PAR["distributions"]:
            idx.append(LMRD_3PAR["distributions"].index(up))
        else:
            unknown.append(raw)
    if unknown:
        raise ValueError("unknown distribution(s) " + " ".join(unknown))

    # two-parameter names.
    if twopar is None:
        tp = [LMRD_3PAR["twopar"][i] for i in idx]
    elif (isinstance(twopar, bool) and twopar is False) or (isinstance(twopar, str) and twopar == "FALSE"):
        tp = []
    else:
        tp = twopar
    words = unique_in_order(make_words(tp))
    m2 = pmatch([w.upper() for w in words], LMRD_2PAR["distributions"])
    bad2 = [w for w, m in zip(words, m2) if m is None]
    if bad2:
        raise ValueError("unknown 2-parameter distribution(s)" + " ".join(bad2))

    # plot region: R's range over the frame limits and the data, then the 4 percent extension.
    xlim_req = tuple(xlim) if xlim is not None else finite_range(xv, 0.0, 0.6)
    ylim_req = tuple(ylim) if ylim is not None else finite_range(yv, 0.0, 0.4)
    usr_x = extend_range(float(xlim_req[0]), float(xlim_req[1]))
    usr_y = extend_range(float(ylim_req[0]), float(ylim_req[1]))

    col_user = None
    if col is not None:
        col_user = [col] if isinstance(col, str) else list(col)
    lty_user = None
    if lty is not None:
        lty_user = [lty] if isinstance(lty, str) else list(lty)
    lwd_list = [lwd] if isinstance(lwd, (int, float)) else list(lwd)

    curves = []
    legend = None
    out = {"lines": None, "twopar": None, "points": None}
    n = len(dists)
    if n > 0:
        if col_user is not None and (x_missing or len(col_user) > 1):
            col_lines = col_user
        else:
            col_lines = [LMRD_3PAR["col"][i] for i in idx]
        lty_lines = lty_user if lty_user is not None else [LMRD_3PAR["lty"][i] for i in idx]
        lwd_lines = recycle(lwd_list, n)
        cols_r = recycle(col_lines, n)
        ltys_r = recycle(lty_lines, n)
        tau3_grid = np.round(LMRD_DATA[:, 0], 2)
        for i, up in enumerate(upper):
            column = LMRD_COLUMNS.index(up)
            curves.append({
                "name": up,
                "x": tau3_grid,
                "y": LMRD_DATA[:, column],
                "col": cols_r[i],
                "linestyle": LTY_TO_LINESTYLE[ltys_r[i]],
                "lwd": lwd_lines[i],
            })
        out["lines"] = {
            "distributions": upper,
            "col.lines": list(col_lines),
            "lty": list(lty_lines),
            "lwd": lwd_lines,
        }

        if legend_lmrd is True:
            opts = {}
        elif isinstance(legend_lmrd, Mapping):
            opts = dict(legend_lmrd)
        else:
            opts = None
        if opts is not None:
            lx = xlegend if xlegend is not None else usr_x[0] + 0.01 * (usr_x[1] - usr_x[0])
            ly = ylegend if ylegend is not None else usr_y[1] - 0.01 * (usr_y[1] - usr_y[0]) * pin
            labels = upper
            for key, value in opts.items():
                if key == "x":
                    lx = value
                elif key == "y":
                    ly = value
                elif key == "legend":
                    labels = list(value)
                else:
                    raise NotImplementedError(f"legend.lmrd option {key!r} is not translated")
            legend = {
                "x": lx,
                "y": ly,
                "labels": labels,
                "col": cols_r,
                "linestyle": [LTY_TO_LINESTYLE[t] for t in ltys_r],
                "lwd": lwd_lines,
            }

    # two-parameter points inside the plot region (R: match2 * (inside)).
    tw = {"x": np.empty(0), "y": np.empty(0), "labels": []}
    if words:
        out["twopar"] = words
        t3 = np.asarray(LMRD_2PAR["tau3"], dtype=float)
        t4 = np.asarray(LMRD_2PAR["tau4"], dtype=float)
        kept = [m for m in m2 if (
            usr_x[0] <= t3[m - 1] <= usr_x[1] and usr_y[0] <= t4[m - 1] <= usr_y[1])]
        if kept:
            k = np.asarray(kept) - 1
            tw = {"x": t3[k], "y": t4[k], "labels": [LMRD_2PAR["text"][j] for j in k]}

    points = None
    if not x_missing:
        col_pts = col_user[0] if (col_user is not None and len(col_user) == 1) else "black"
        points = {"x": xv, "y": yv, "pch": pch, "col": col_pts}
        out["points"] = {"col.pts": col_pts, "pch": pch, "cex": cex}

    return {
        "usr_x": usr_x,
        "usr_y": usr_y,
        "curves": curves,
        "twopar": tw,
        "legend": legend,
        "points": points,
        "out": out,
    }
