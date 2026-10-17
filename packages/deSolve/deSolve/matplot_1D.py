"""``matplot.1D`` — spatial matplot for ``ode.1D`` output."""

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
    repdots,
    select1dvar,
    set_data,
    setdots,
    setplotpar,
    set_range,
    splitdots,
    update_obs,
    which_var_obs,
)
from deSolve.rk4 import DeSolveMatrix


def _object_attrs(x: Any) -> dict[str, Any]:
    if isinstance(x, DeSolveMatrix):
        return {
            "nspec": getattr(x, "nspec", None),
            "dimens": getattr(x, "dimens", None),
            "ynames": getattr(x, "ynames", None),
            "lengthvar": getattr(x, "lengthvar", None),
            "map": getattr(x, "map", None),
        }
    return {
        "nspec": getattr(x, "nspec", None),
        "dimens": getattr(x, "dimens", None),
        "ynames": getattr(x, "ynames", None),
        "lengthvar": getattr(x, "lengthvar", None),
        "map": getattr(x, "map", None),
    }


def _draw_vertical_axis(ax, dotmain: dict[str, Any], xmin: float) -> None:
    ylim = dotmain.get("ylim") or ax.get_ylim()
    if dotmain.get("xlim") is None:
        v = xmin
    else:
        v = dotmain["xlim"][0]
    ax.axhline(ylim[1], color="black")
    ax.axvline(v, color="black")
    ax.tick_params(axis="y")
    ax.tick_params(axis="top", labelsize=8)


def _plot_obs(ax, obs: dict[str, Any], io: float, xyswap: bool = False) -> None:
    olength = min(obs["pos"].shape[0], obs["length"]) if obs["pos"] is not None else 0
    for j in range(olength):
        row = obs["pos"][j]
        iobs = range(int(row[0]) - 1, int(row[1]))
        if len(iobs) == 0:
            continue
        pp = extractdots(obs.get("par") or {}, j + 1)
        if not xyswap:
            ax.scatter(
                obs["dat"][list(iobs), 0],
                obs["dat"][list(iobs), int(io) - 1],
                color=_r_color(pp.get("col", 1)),
                s=20,
            )
        else:
            ax.scatter(
                obs["dat"][list(iobs), int(io) - 1],
                obs["dat"][list(iobs), 0],
                color=_r_color(pp.get("col", 1)),
                s=20,
            )


def matplot_1D(
    x: Any,
    select: Any = None,
    which: Any = None,
    ask: bool | None = None,
    obs: Any = None,
    obspar: dict[str, Any] | None = None,
    grid: Any = None,
    xyswap: bool = False,
    vertical: bool = False,
    subset: Any = None,
    _figure: Any = None,
    _savefig: str | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    if which is None:
        which = select
    att = _object_attrs(x)
    nspec = att["nspec"]
    dimens = att["dimens"]
    if dimens is None or nspec is None:
        raise ValueError("matplot.1D only works for models solved with 'ode.1D'")
    proddim = int(np.prod(dimens))
    xarr, _ = _as_array(x)
    if (xarr.shape[1] - nspec * proddim) < 1:
        raise ValueError("ncol of 'x' should be > 'nspec' * dimens if x is a vector")

    obs = set_data(obs)
    if att["ynames"] is not None:
        varnames = list(att["ynames"])
    else:
        varnames = [str(i) for i in range(1, nspec + 1)]
    lengthvar = att.get("lengthvar")
    if lengthvar is not None:
        lv = np.asarray(lengthvar, dtype=int).reshape(-1)
        if lv.size > 1:
            names = getattr(x, "lengthvar_names", None) or []
            for i in range(1, lv.size):
                if i < len(names):
                    varnames.append(str(names[i]))
                else:
                    varnames.append(str(i))

    which_sel = which_var_obs(which, obs, nspec, varnames, remove1st=False)
    npanels = len(which_sel)
    att_dict = {
        "nspec": nspec,
        "dimens": dimens,
        "lengthvar": lengthvar,
        "map": att.get("map"),
    }
    sel = select1dvar(which_sel, varnames, att_dict)
    xwhich = sel["Which"]
    obs = update_obs(obs, varnames, xwhich)
    obspar = obspar or {}
    obs["par"] = {k: repdots(v, obs["length"]) for k, v in obspar.items()}

    ldots = dict(kwargs)
    ask = setplotpar(ldots, npanels, ask)
    dots = splitdots(ldots, varnames)
    dotpoints = dots["points"]
    dotmain = setdots(dots["main"], npanels)
    dotmain["xlab"] = expanddots(ldots.get("xlab"), "x", npanels)
    dotmain["ylab"] = expanddots(ldots.get("ylab"), "", npanels)
    dotmain["main"] = expanddots(
        ldots.get("main"),
        [varnames[w - 1] for w in xwhich],
        npanels,
    )
    xxlim = expanddotslist(ldots.get("xlim"), npanels)
    yylim = expanddotslist(ldots.get("ylim"), npanels)
    xyswap_list = repdots(xyswap, npanels)
    vertical_list = repdots(vertical, npanels)

    if subset is None:
        isub = np.arange(xarr.shape[0])
    else:
        colnames = getattr(x, "colnames", None) or [str(i + 1) for i in range(xarr.shape[1])]
        mask = _eval_subset(subset, xarr, list(colnames))
        if mask.dtype == bool:
            isub = np.where(mask)[0]
        else:
            isub = mask

    grid_list = expanddotslist(grid, npanels)

    nmdots = set(ldots.keys())
    if not nmdots.intersection({"mfrow", "mfcol"}):
        nc = min(int(np.ceil(np.sqrt(npanels))), 3)
        nr = min(int(np.ceil(npanels / nc)), 3)
        mfrow = (nr, nc)
    elif "mfcol" in nmdots:
        mfrow = tuple(reversed(tuple(ldots["mfcol"])))
    else:
        mfrow = tuple(ldots["mfrow"])

    if _figure is None:
        fig, axes = plt.subplots(mfrow[0], mfrow[1], squeeze=False)
    else:
        fig = _figure
        axes = np.array([[fig.gca()]])

    usr = None
    for ip in range(npanels):
        istart = int(sel["istart"][ip])
        istop = int(sel["istop"][ip])
        io = obs["Which"][ip]
        block = xarr[isub, istart - 1 : istop]
        out = block.T
        if len(isub) > 1 and np.sum(isub >= 0) == 1:
            out = np.atleast_2d(out)
        grid_val = grid_list[ip]
        if grid_val is None:
            grid_arr = np.arange(1, out.shape[0] + 1, dtype=float)
        else:
            grid_arr = np.asarray(grid_val, dtype=float)

        ax = axes.flat[ip]
        dmain = extractdots(dotmain, ip + 1)
        ylog = bool(dmain.get("log") and re.search("y", str(dmain.get("log"))))
        xlog = bool(dmain.get("log") and re.search("x", str(dmain.get("log"))))

        if vertical_list[ip]:
            xyswap_list[ip] = True
            dmain["axes"] = False
            dmain["xlab"] = ""
            dmain["xaxs"] = "i"
            dmain["yaxs"] = "i"

        ix_slice = slice(istart - 1, istop)
        if not xyswap_list[ip]:
            if xxlim[ip] is not None:
                dmain["xlim"] = xxlim[ip]
            ylim_raw = set_range(yylim[ip], xarr, None, isub, ix_slice, obs, io, ylog)
            dmain["ylim"] = _extend_lim(ylim_raw, dmain.get("yaxs", "r"))
            if dmain.get("xlim") is not None:
                xlim = _extend_lim(tuple(dmain["xlim"]), dmain.get("xaxs", "r"))
            else:
                xlim = _extend_lim((float(np.min(grid_arr)), float(np.max(grid_arr))), "r")
            for j in range(out.shape[1]):
                ax.plot(
                    grid_arr,
                    out[:, j],
                    color=_r_color(j + 1),
                    linestyle=_line_style(1),
                )
            ax.set_xlim(xlim)
            ax.set_ylim(dmain["ylim"])
            if io is not None and not (isinstance(io, float) and np.isnan(io)):
                _plot_obs(ax, obs, io, xyswap=False)
        else:
            if yylim[ip] is not None:
                dmain["ylim"] = yylim[ip]
            xlim_raw = set_range(xxlim[ip], xarr, None, isub, ix_slice, obs, io, xlog)
            dmain["xlim"] = _extend_lim(xlim_raw, dmain.get("xaxs", "r"))
            if yylim[ip] is None and xyswap_list[ip]:
                dmain["ylim"] = (float(np.max(grid_arr)), float(np.min(grid_arr)))
            for j in range(out.shape[1]):
                ax.plot(
                    out[:, j],
                    grid_arr,
                    color=_r_color(j + 1),
                    linestyle=_line_style(1),
                )
            ax.set_xlim(dmain["xlim"])
            ax.set_ylim(dmain["ylim"])
            if vertical_list[ip]:
                _draw_vertical_axis(ax, dmain, float(np.min(out)))
            if io is not None and not (isinstance(io, float) and np.isnan(io)):
                _plot_obs(ax, obs, io, xyswap=True)

        ax.set_xlabel(dmain.get("xlab", ""))
        ax.set_ylabel(dmain.get("ylab", ""))
        ax.set_title(dmain.get("main", ""))
        usr = ax.get_xlim() + ax.get_ylim()

    if _savefig:
        fig.savefig(_savefig, format="svg")
    return {"figure": fig, "usr": list(usr) if usr else None}
