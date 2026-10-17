"""Plots of quantile regression fits: plot.rq.process, plot.rqs, plot.summary.rqs, plot.table.rq.

Drawing is Matplotlib. Each function takes an optional ``fig`` (a Matplotlib
figure to draw on) and an optional ``log`` (a ``PlotLog``). When a log is given,
the function records what each panel draws, in the token format that the R
recorder in ``packages/quantreg/proof/plot_record.R`` writes:

    T xlab ylab main          labels of one plot call
    L nrow ncol               the layout set by par(mfrow=)
    W xmin xmax ymin ymax     the window after a plot call (R's par("usr"))
    P x y type col            points, a line, or an abline across the window
    Y x y col                 a polygon
    V name values             a returned value

Axis windows follow R's default ``xaxs = "r"`` and ``yaxs = "r"``: the range is
extended by 4 percent on each side.
"""

from __future__ import annotations

import math
import sys
from typing import Any, Sequence

import numpy as np
from scipy.stats import norm

# R 4.x default palette, used when a colour is given as a palette index.
R_PALETTE = ("#000000", "#DF536B", "#61D04F", "#2297E6", "#28E2E5", "#CD0BBC", "#F5C710", "#9E9E9E")
_NAMED_COLOURS = {"black": "#000000", "gray62": "#9E9E9E", "grey62": "#9E9E9E"}

# quantreg's defunct table.rq message, as table.R writes it.
TABLE_RQ_MESSAGE = (
    "table.rq() and related methods are defunct --  see ?rq, which now accepts a vector of taus."
)


class PlotLog:
    """Records the drawing calls of one plot function."""

    def __init__(self) -> None:
        self.log: list[tuple[str, tuple[Any, ...]]] = []

    def record(self, tag: str, *fields: Any) -> None:
        self.log.append((tag, fields))


def format_log(log: PlotLog) -> list[str]:
    """One text line per record, in the layout plot_record.R writes.

    Each field is its length followed by its values. Numbers use %.17g.
    """
    lines = []
    for tag, fields in log.log:
        tokens = [tag]
        for field in fields:
            if isinstance(field, np.ndarray):
                items = field.ravel().tolist()
            elif isinstance(field, (list, tuple)):
                items = list(field)
            else:
                items = [field]
            tokens.append(str(len(items)))
            for item in items:
                tokens.append(item if isinstance(item, str) else "%.17g" % float(item))
        lines.append(" ".join(tokens))
    return lines


def canon_col(col: Any) -> str:
    """The colour as R's rgb(t(col2rgb(col))) writes it: upper-case #RRGGBB."""
    if isinstance(col, (int, np.integer)):
        return R_PALETTE[(int(col) - 1) % len(R_PALETTE)]
    text = str(col)
    if text in _NAMED_COLOURS:
        return _NAMED_COLOURS[text]
    if text.startswith("#") and len(text) == 7:
        return text.upper()
    raise ValueError(f"colour {text!r} is not in this translation")


def gray(level: float) -> str:
    """R's gray(level) as a hex string."""
    value = int(255 * float(level) + 0.5)
    return f"#{value:02X}{value:02X}{value:02X}"


def n2mfrow(nr_plots: int, asp: float = 1.0) -> tuple[int, int]:
    """grDevices::n2mfrow: rows and columns for nr_plots panels."""
    nr = int(nr_plots)
    if asp == 1 and nr <= 12:
        if nr <= 3:
            return nr, 1
        if nr <= 6:
            return (nr + 1) // 2, 2
        return (nr + 2) // 3, 3
    nrow = math.ceil(math.sqrt(nr / asp))
    rc = [nrow, math.ceil(nr / nrow)]
    do = True
    while do and rc[0] * rc[1] > nr:
        cand = [rc[0] - 0, rc[1] - 1]
        do = cand[0] * cand[1] >= nr
        if do:
            rc = cand
        else:
            cand = [rc[0] - 1, rc[1] - 0]
            do = cand[0] * cand[1] >= nr
            if do:
                rc = cand
    return rc[0], rc[1]


def _window(lo: float, hi: float) -> tuple[float, float]:
    """R's plot window for the range lo..hi with xaxs = "r"."""
    temp = 0.04 * (hi - lo)
    return lo - temp, hi + temp


def _range(values: Sequence[float]) -> tuple[float, float]:
    arr = np.asarray(values, dtype=float).ravel()
    return float(np.min(arr)), float(np.max(arr))


def _layout(log: PlotLog | None, nrow: int, ncol: int) -> None:
    if log is not None:
        log.record("L", [nrow, ncol])


def _plot_xy(ax, log, x, y, type_="p", col="black", xlab="", ylab="", main="", ylim=None):
    """plot(): set the labels and window, draw the points or line, then record."""
    xs = np.asarray(x, dtype=float).ravel()
    ys = np.asarray(y, dtype=float).ravel()
    if log is not None:
        log.record("T", [xlab], [ylab], [main])
    lo_x, hi_x = _range(xs)
    lo_y, hi_y = _range(ys) if ylim is None else (float(ylim[0]), float(ylim[1]))
    ax.set_xlim(*_window(lo_x, hi_x))
    ax.set_ylim(*_window(lo_y, hi_y))
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    ax.set_title(main)
    colour = canon_col(col)
    if log is not None:
        log.record("W", [*ax.get_xlim(), *ax.get_ylim()])
    _draw_series(ax, xs, ys, type_, colour)
    if log is not None:
        log.record("P", xs, ys, [type_], [colour])


def _draw_series(ax, xs, ys, type_, colour):
    if type_ == "l":
        ax.plot(xs, ys, linestyle="-", color=colour)
    elif type_ == "p":
        ax.plot(xs, ys, linestyle="none", marker="o", markersize=2, color=colour)
    elif type_ == "b":
        ax.plot(xs, ys, linestyle="-", marker="o", markersize=2, color=colour)


def _points(ax, log, x, y, type_, col):
    xs = np.asarray(x, dtype=float).ravel()
    ys = np.asarray(y, dtype=float).ravel()
    colour = canon_col(col)
    if log is not None:
        log.record("P", xs, ys, [type_], [colour])
    _draw_series(ax, xs, ys, type_, colour)


def plot_qss1(x, rug=True, jit=True, add=False, fig=None, log=None, **kwargs):
    """plot.qss1: draw a qss1 knot curve and optionally its x rug.

    ``x`` may be a two-column array or a qss1/QSSFit-like object containing
    ``xyz``.  The ``jit`` argument is accepted for R API compatibility.
    """
    del jit
    if isinstance(x, dict):
        xyz = x.get("xyz")
    else:
        xyz = getattr(x, "xyz", x)
    xyz = np.asarray(xyz, dtype=float)
    if xyz.ndim != 2 or xyz.shape[1] < 2:
        raise ValueError("x should contain at least two columns")
    fig = _new_figure(fig)
    ax = fig.axes[0] if add and fig.axes else fig.add_subplot(1, 1, 1)
    if not add:
        _plot_xy(ax, log, xyz[:, 0], xyz[:, 1], type_="n", **kwargs)
    _points(ax, log, xyz[:, 0], xyz[:, 1], "l", kwargs.get("col", "black"))
    if rug:
        # Matplotlib's rug is equivalent to the plotted x coordinates for
        # jit=False; keep the values available to plot-data proofs.
        ymin, _ = ax.get_ylim()
        ax.plot(xyz[:, 0], np.full(xyz.shape[0], ymin), linestyle="none",
                marker="|", color=canon_col(kwargs.get("col", "black")))
    return None


def _abline_h(ax, log, h, col):
    """abline(h = h): a horizontal line across the current window."""
    colour = canon_col(col)
    left, right = ax.get_xlim()
    if log is not None:
        log.record("P", [left, right], [h, h], ["l"], [colour])
    ax.plot([left, right], [h, h], linestyle="-", color=colour)


def _polygon(ax, log, x, y, col):
    xs = np.asarray(x, dtype=float).ravel()
    ys = np.asarray(y, dtype=float).ravel()
    colour = canon_col(col)
    if log is not None:
        log.record("Y", xs, ys, [colour])
    ax.fill(xs, ys, facecolor=colour, edgecolor="none")


def _new_figure(fig):
    if fig is not None:
        return fig
    import matplotlib.pyplot as plt

    return plt.figure(figsize=(7, 7))


def plot_rq_process(x, nrow=3, ncol=2, fig=None, log=None):
    """Panels of the quantile regression process: each coefficient against tau.

    ``x`` is a dict with ``sol`` (rows tau, Qbar, Obj.Fun, then one row per
    coefficient) and ``sol_names`` (the row names of ``sol``), the parts of an R
    rq.process object that the plot reads.
    """
    sol = np.asarray(x["sol"], dtype=float)
    names = list(x["sol_names"])
    p = sol.shape[0] - 3
    if p > nrow * ncol:
        raise ValueError("more coefficient panels than the layout holds")
    fig = _new_figure(fig)
    _layout(log, nrow, ncol)
    for i in range(1, p + 1):
        ax = fig.add_subplot(nrow, ncol, i)
        _plot_xy(ax, log, sol[0], sol[2 + i], type_="l", xlab="tau", ylab=names[2 + i])
    fig.subplots_adjust(hspace=0.5, wspace=0.35)
    return None


def _select(names: list[str], parm) -> list[int]:
    if parm is None:
        return list(range(len(names)))
    chosen = []
    for item in parm:
        if isinstance(item, (int, np.integer)):
            chosen.append(int(item) - 1)
        else:
            chosen.append(names.index(str(item)))
    return chosen


def plot_rqs(
    x,
    parm=None,
    ols=True,
    mfrow=None,
    ylim=None,
    main=None,
    col=(1, 2),
    cex=0.5,
    pch=20,
    type_="b",
    xlab="",
    ylab="",
    fig=None,
    log=None,
):
    """Coefficient of each parameter at every tau, with the OLS line when ols is true.

    ``x`` is a dict from ``rq`` with several taus: ``tau``, ``names``,
    ``coefficients`` (parameters by taus), and ``x`` and ``y`` for the OLS fit.
    Returns the coefficients, with the OLS column last when ols is true.
    """
    del cex, pch
    taus = np.atleast_1d(np.asarray(x["tau"], dtype=float))
    names = list(x["names"])
    coef = np.asarray(x["coefficients"], dtype=float)
    idx = _select(names, parm)
    parm_names = [names[k] for k in idx]
    cf = coef[idx, :]
    if ols:
        design = np.asarray(x["x"], dtype=float)
        response = np.asarray(x["y"], dtype=float).reshape(-1)
        olscf = np.linalg.lstsq(design, response, rcond=None)[0][idx]
    nr, nc = n2mfrow(len(idx)) if mfrow is None else (int(mfrow[0]), int(mfrow[1]))
    fig = _new_figure(fig)
    _layout(log, nr, nc)
    col_list = [canon_col(c) for c in (col if isinstance(col, (list, tuple)) else [col])]
    col_list = (col_list * 2)[:2]
    mains = parm_names if main is None else list(main)
    ylim0 = ylim
    for i in range(len(idx)):
        cur = ylim0
        if cur is None:
            values = [*cf[i, :], olscf[i]] if ols else list(cf[i, :])
            cur = _range(values)
        ax = fig.add_subplot(nr, nc, i + 1)
        _plot_xy(
            ax,
            log,
            taus,
            cf[i, :],
            type_=type_,
            col=col_list[0],
            xlab=xlab,
            ylab=ylab,
            main=mains[i],
            ylim=cur,
        )
        if ols:
            _abline_h(ax, log, olscf[i], col_list[1])
        _abline_h(ax, log, 0.0, gray(0.3))
    fig.subplots_adjust(hspace=0.5, wspace=0.35)
    if ols:
        return np.column_stack([cf, olscf])
    return cf


def _ols_summary(model, parm_idx: list[int], zalpha: float) -> np.ndarray:
    """summary(lm(y ~ X))$coefficients for the rows in parm_idx, as value, lower, upper."""
    design = np.asarray(model["x"], dtype=float)
    response = np.asarray(model["y"], dtype=float).reshape(-1)
    n, p = design.shape
    beta = np.linalg.lstsq(design, response, rcond=None)[0]
    resid = response - design @ beta
    sigma2 = float(resid @ resid) / (n - p)
    se = np.sqrt(np.diag(sigma2 * np.linalg.inv(design.T @ design)))
    est = beta[parm_idx]
    err = se[parm_idx]
    return np.column_stack([est, est - err * zalpha, est + err * zalpha])


def plot_summary_rqs(
    x,
    parm=None,
    level=0.9,
    ols=True,
    mfrow=None,
    ylim=None,
    main=None,
    col=None,
    border=None,
    lcol=2,
    cex=0.5,
    pch=20,
    type_="b",
    xlab="",
    ylab="",
    fig=None,
    log=None,
):
    """Coefficient bands at every tau, from a summary.rqs object.

    ``x`` is the list of summary.rq dicts. When ols is true, the OLS fit uses
    the x and y that summary_rq carries on ``x[0]``, as R reads the model frame
    of ``x[[1]]``. Returns (array, Ylim): the array has dimensions parameters, 3, and
    tau plus one for OLS, and Ylim has two rows and one column per panel.
    """
    del cex, pch, border
    zalpha = float(norm.ppf(1 - (1 - level) / 2))
    taus = np.array([piece["tau"] for piece in x], dtype=float)
    cf = []
    for piece in x:
        table = np.asarray(piece["coefficients"], dtype=float)
        if table.shape[1] == 4:
            table = np.column_stack(
                [table[:, 0], table[:, 0] - table[:, 1] * zalpha, table[:, 0] + table[:, 1] * zalpha]
            )
        if table.shape[1] != 3:
            raise ValueError("summary.rqs components have wrong dimension")
        cf.append(table)
    names = list(x[0]["names"])
    idx = _select(names, parm)
    parm_names = [names[k] for k in idx]
    cf = [table[idx, :] for table in cf]
    if ols:
        if "x" not in x[0] or "y" not in x[0]:
            raise ValueError("ols needs x and y on the summary, which summary_rq carries")
        olscf = _ols_summary(x[0], idx, zalpha)
    nr, nc = n2mfrow(len(idx)) if mfrow is None else (int(mfrow[0]), int(mfrow[1]))
    fig = _new_figure(fig)
    _layout(log, nr, nc)
    if col is None:
        col = (gray(0.0), gray(0.75))
    col_list = [canon_col(c) for c in col]
    lcol_value = canon_col(lcol)
    mains = parm_names if main is None else list(main)
    ylim0 = None if ylim is None else np.asarray(ylim, dtype=float)
    ylims = []
    for i in range(len(idx)):
        band = np.array([table[i, :] for table in cf])
        cur = ylim0
        if ylim0 is not None and ylim0.ndim == 2:
            cur = ylim0[:, i]
        if ylim0 is None:
            values = [band[:, 1], band[:, 2]]
            if ols:
                values.append(olscf[i, :1])
            cur = _range(np.concatenate(values))
        ax = fig.add_subplot(nr, nc, i + 1)
        _plot_xy(
            ax,
            log,
            np.concatenate([taus, taus]),
            np.concatenate([band[:, 1], band[:, 2]]),
            type_="n",
            xlab=xlab,
            ylab=ylab,
            main=mains[i],
            ylim=cur,
        )
        _polygon(ax, log, np.concatenate([taus, taus[::-1]]), np.concatenate([band[:, 1], band[::-1, 2]]), col_list[1])
        _points(ax, log, taus, band[:, 0], type_, col_list[0])
        if ols:
            for k in range(3):
                _abline_h(ax, log, olscf[i, k], lcol_value)
        _abline_h(ax, log, 0.0, gray(0.3))
        ylims.append(np.asarray(cur, dtype=float))
    fig.subplots_adjust(hspace=0.5, wspace=0.35)
    stacks = list(cf) + ([olscf] if ols else [])
    array = np.stack(stacks, axis=2)
    return [array, np.column_stack(ylims)]


def plot_table_rq(x=None, **kwargs):
    """The defunct message for table.rq. It prints and draws nothing."""
    del x, kwargs
    sys.stdout.write(TABLE_RQ_MESSAGE)
    return None
