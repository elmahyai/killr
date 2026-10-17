"""``matplot.0D`` and ``matplot.deSolve`` — time-series matplot for deSolve output."""

from __future__ import annotations

import re
from typing import Any

import matplotlib.pyplot as plt
import numpy as np

from deSolve.matplot_helpers import (
    _as_array,
    _eval_subset,
    _extend_lim,
    _line_style,
    _r_color,
    expanddots,
    expanddotslist,
    extractdots,
    range_merge,
    repdots,
    set_data,
    setdots,
    splitdots,
    update_obs2,
)


def _which_var(xwhich: Any, obs: dict[str, Any], varnames: list[str]) -> list[int]:
    if xwhich is None and obs["dat"] is None:
        return list(range(2, len(varnames) + 1))
    if xwhich is None:
        which = [i + 1 for i, name in enumerate(varnames) if name in (obs.get("name") or [])]
        return [w for w in which if w > 1]
    if isinstance(xwhich, str):
        which = [i + 1 for i, name in enumerate(varnames) if name == xwhich]
        if len(which) != 1:
            raise ValueError(f"unknown variable{xwhich}")
        return which
    if isinstance(xwhich, (list, tuple)) and xwhich and isinstance(xwhich[0], str):
        which = [i + 1 for i, name in enumerate(varnames) if name in xwhich]
        if len(which) != len(xwhich):
            missing = [v for v in xwhich if v not in varnames]
            raise ValueError(f"unknown variable{','.join(missing)}")
        return which
    return [int(xwhich) + 1]


def matplot_0D(
    x: Any,
    *args: Any,
    select: Any = None,
    which: Any = None,
    obs: Any = None,
    obspar: dict[str, Any] | None = None,
    subset: Any = None,
    legend: dict[str, Any] | None = None,
    _figure: Any = None,
    _savefig: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Plot deSolve 0-D output (matrix with time in column 1)."""
    if which is None:
        which = select
    t = 1
    obs = set_data(obs)
    xarr, varnames = _as_array(x)
    obspar = obspar or {}
    ldots = dict(kwargs)
    for i, arg in enumerate(args):
        ldots[f"arg{i}"] = arg

    lw = 0 if which is None else (len(which) if isinstance(which, (list, tuple)) else 1)
    xwhich: list[list[int]] | None = None
    if lw and isinstance(which, list) and which and isinstance(which[0], list):
        xwhich = [_which_var(w, obs, varnames) for w in which]
    elif lw:
        xwhich = [_which_var(which, obs, varnames)]
    else:
        xwhich = [list(range(2, len(varnames) + 1))]

    vn = [",".join(varnames[i - 1] for i in group) for group in xwhich]
    vn2 = [varnames[i - 1] for group in xwhich for i in group]
    npanels = len(xwhich)
    nx = sum(len(g) for g in xwhich)
    flat_ix = [i for g in xwhich for i in g]
    obs = update_obs2(obs, varnames, flat_ix)

    dots = splitdots(ldots, varnames)
    if dots["nother"] > 1:
        raise ValueError("can plot only one deSolve output object at a time with matplot")

    dotmain = setdots(dots["main"], npanels)
    dotmain["xlab"] = expanddots(ldots.get("xlab"), varnames[t - 1], npanels)
    dotmain["ylab"] = expanddots(ldots.get("ylab"), vn, npanels)
    dotmain["main"] = expanddots(ldots.get("main"), "x", npanels)
    yylim = expanddotslist(ldots.get("ylim"), npanels)
    xxlim = expanddotslist(ldots.get("xlim"), npanels)

    dotpoints = setdots(dots["points"], nx)
    dotpoints["type"] = expanddots(ldots.get("type"), "l", nx)
    dotpoints["lty"] = expanddots(ldots.get("lty"), list(range(1, nx + 1)), nx)
    dotpoints["pch"] = expanddots(ldots.get("pch"), list(range(1, nx + 1)), nx)
    dotpoints["col"] = expanddots(ldots.get("col"), list(range(1, nx + 1)), nx)
    dotpoints["bg"] = expanddots(ldots.get("bg"), list(range(1, nx + 1)), nx)

    if obs["length"] > 0:
        ii = [j for j, w in enumerate(flat_ix) if w in obs.get("Which", [])]
        ii = [j for j in ii if j is not None]
        if obs.get("par") is None:
            obs["par"] = {}
        else:
            obs["par"] = {k: repdots(v, obs["length"]) for k, v in obspar.items()}
        par = obs["par"]
        if par.get("pch") is None:
            par["pch"] = [dotpoints["pch"][j] for j in ii]
        if par.get("cex") is None and "cex" in dotpoints:
            par["cex"] = [dotpoints["cex"][j] for j in ii]
        if par.get("col") is None:
            par["col"] = [dotpoints["col"][j] for j in ii]
        if par.get("bg") is None:
            par["bg"] = [dotpoints["bg"][j] for j in ii]

    isub = _eval_subset(subset, xarr, varnames)

    if _figure is None:
        fig = plt.figure()
    else:
        fig = _figure
    if npanels > 1:
        fig.subplots_adjust(left=0.12 + 0.08 * (npanels - 1))

    ii = 1
    overlay_axes: list[Any] = []
    usr = None
    for ip in range(npanels):
        ix = xwhich[ip]
        il = len(ix)
        iip = list(range(ii, ii + il))
        ii += il
        io = [obs["Which"][j - 1] for j in iip]
        dmain = extractdots(dotmain, ip + 1)
        if dmain.get("axes") is None:
            dmain["axes"] = False
        if dmain.get("frame_plot") is None and dmain.get("frame.plot") is None:
            dmain["frame.plot"] = True
        dpoints = extractdots(dotpoints, iip)

        ylog = bool(dmain.get("log") and re.search("y", str(dmain.get("log"))))
        xlog = bool(dmain.get("log") and re.search("x", str(dmain.get("log"))))

        def set_range_mat(lim, cols, io_cols, log):
            if lim is None:
                yrange = range_merge(None, xarr[isub, :][:, [c - 1 for c in cols]].reshape(-1), log)
                if io_cols and not (isinstance(io_cols[0], float) and np.isnan(io_cols[0])):
                    for j in io_cols:
                        if not np.isnan(j):
                            yrange = range_merge(yrange, obs["dat"][:, int(j) - 1], log)
            else:
                yrange = tuple(lim)
            return yrange

        ylim_raw = set_range_mat(yylim[ip], ix, io, ylog)
        xlim_raw = set_range_mat(xxlim[ip], [t], io, xlog)
        xaxs = dmain.get("xaxs", "r")
        yaxs = dmain.get("yaxs", "r")
        xlim = _extend_lim(xlim_raw, xaxs)
        ylim = _extend_lim(ylim_raw, yaxs)
        ylab = dmain.get("ylab", "")

        if ip == 0:
            ax = fig.add_subplot(111)
            overlay_axes.append(ax)
        else:
            ax = fig.add_axes(overlay_axes[0].get_position())
            ax.set_facecolor("none")
            for spine in ax.spines.values():
                spine.set_visible(False)
            overlay_axes.append(ax)

        xvals = xarr[isub, t - 1]
        for j, col in enumerate(ix):
            yvals = xarr[isub, col - 1]
            typ = dpoints["type"][j] if isinstance(dpoints["type"], list) else dpoints["type"]
            lty = dpoints["lty"][j] if isinstance(dpoints["lty"], list) else dpoints["lty"]
            colr = dpoints["col"][j] if isinstance(dpoints["col"], list) else dpoints["col"]
            lwdt = dpoints.get("lwd", 1)
            if isinstance(lwdt, list):
                lwdt = lwdt[j]
            if typ in ("l", "b", "o"):
                ax.plot(
                    xvals,
                    yvals,
                    color=_r_color(colr),
                    linestyle=_line_style(lty),
                    linewidth=lwdt,
                )
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)
        if not dmain.get("axes", True):
            ax.set_xticks([])
            ax.set_yticks([])
        if ip > 0:
            ax.set_xlabel("")
            ax.set_title("")
        else:
            ax.set_xlabel(dmain.get("xlab", ""))
            ax.set_title(dmain.get("main", ""))

        if ip == 0:
            ax.tick_params(axis="x", labelsize=10 * float(dmain.get("cex.axis") or 1))
        bl = 4 * ip
        ax.yaxis.set_label_position("left")
        ax.yaxis.tick_left()
        if bl:
            ax.spines["left"].set_position(("outward", 40 * bl))
        ax.set_ylabel(ylab, rotation=90, labelpad=20 + 40 * bl)
        ax.tick_params(axis="y", labelsize=10 * float(dmain.get("cex.axis") or 1))

        if io and not (isinstance(io[0], float) and np.isnan(io[0])):
            for j, ioc in enumerate(io):
                if np.isnan(ioc):
                    continue
                matches = [k for k, w in enumerate(obs["Which"]) if w == ioc]
                for i in matches:
                    row = obs["pos"][i]
                    iobs = range(int(row[0]) - 1, int(row[1]))
                    if len(iobs) > 0:
                        px = obs["dat"][list(iobs), 0]
                        py = obs["dat"][list(iobs), int(ioc) - 1]
                        pp = extractdots(obs.get("par") or {}, j + 1)
                        ax.scatter(px, py, color=_r_color(pp.get("col", 1)), s=20)

        usr = (xlim[0], xlim[1], ylim[0], ylim[1])

    if legend is None:
        legend = {"x": "topright"}
    if isinstance(legend, dict):
        leg_text = legend.get("legend") or vn2
        if isinstance(leg_text, str):
            leg_text = [leg_text]
        lty = list(dotpoints["lty"])
        pch = list(dotpoints["pch"])
        types = dotpoints["type"]
        for j, typ in enumerate(types if isinstance(types, list) else [types] * nx):
            if typ == "p":
                lty[j] = np.nan
            if typ == "l":
                pch[j] = np.nan
        handles = []
        labels = []
        for j in range(nx):
            labels.append(str(leg_text[j]))
            handles.append(
                plt.Line2D(
                    [0],
                    [0],
                    color=_r_color(dotpoints["col"][j]),
                    linestyle=_line_style(lty[j]) if not np.isnan(lty[j]) else "None",
                    marker="o" if not np.isnan(pch[j]) else None,
                )
            )
        loc = legend.get("x", "topright")
        fig.legend(handles, labels, loc=loc.replace("topright", "upper right"))

    if _savefig:
        fig.savefig(_savefig, format="svg")
    return {"figure": fig, "usr": list(usr) if usr else None}


def matplot_deSolve(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Identical to ``matplot.0D`` in deSolve 1.42."""
    return matplot_0D(*args, **kwargs)
