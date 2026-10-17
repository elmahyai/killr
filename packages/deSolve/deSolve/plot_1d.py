"""Line plots of a 1-D deSolve profile, one frame per time (``plot.1D``)."""

from __future__ import annotations

import time
from typing import Any

import matplotlib

matplotlib.use("Agg", force=False)

import matplotlib.pyplot as plt
import numpy as np

_PLOT_NAMES = {
    "xlab",
    "ylab",
    "xlim",
    "ylim",
    "main",
    "sub",
    "log",
    "asp",
    "ann",
    "axes",
    "frame.plot",
    "panel.first",
    "panel.last",
    "cex.lab",
    "cex.axis",
    "cex.main",
}

_R_PALETTE = [
    "#000000",
    "#FF0000",
    "#00CD00",
    "#0000FF",
    "#00FFFF",
    "#FF00FF",
    "#FFFF00",
    "#BEBEBE",
]

_LTY = ["solid", "dashed", "dotted", "dashdot", (0, (5, 1)), (0, (3, 1, 1, 1))]


class Plot1DDrawn:
    """Last page, plus every panel in the order ``plot.1D`` draws them."""

    def __init__(self, figure, panels: list[dict[str, Any]]):
        self.figure = figure
        self.panels = panels

    def __str__(self) -> str:
        lines = []
        for panel in self.panels:
            title = panel.get("main")
            lines.append("" if title is None else str(title))
            lines.append("x " + " ".join(f"{value:.7g}" for value in panel["x"]))
            lines.append("y " + " ".join(f"{value:.7g}" for value in panel["y"]))
        return "\n".join(lines)


def _is_desolve(value: Any) -> bool:
    return hasattr(value, "data") and hasattr(value, "colnames") and hasattr(value, "nspec")


def _matrix(value: Any) -> np.ndarray:
    data = getattr(value, "data", value)
    array = np.asarray(data, dtype=np.float64)
    if array.ndim != 2:
        raise ValueError("x must be a matrix")
    return array


def _colnames(value: Any, ncol: int) -> list[Any]:
    names = getattr(value, "colnames", None)
    if names is None:
        return list(range(1, ncol + 1))
    return list(names)


def _dimens_length(dimens: Any) -> int:
    if dimens is None:
        return 0
    if isinstance(dimens, (int, np.integer)):
        return 1
    return int(np.size(dimens))


def _prod_dim(att: dict[str, Any]) -> int:
    if att.get("map") is not None:
        mapped = np.asarray(att["map"], dtype=float)
        return int(np.sum(~np.isnan(mapped)))
    dimens = att["dimens"]
    if isinstance(dimens, (int, np.integer)):
        return int(dimens)
    return int(np.prod(np.atleast_1d(dimens)))


def _na(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(np.isnan(value))
    except (TypeError, ValueError):
        return False


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, np.ndarray):
        return value.reshape(-1).tolist()
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _recycle(value: Any, n: int) -> list[Any]:
    if callable(value):
        return value
    items = _as_list(value)
    if n == 0:
        return []
    if not items:
        return [None] * n
    return [items[i % len(items)] for i in range(n)]


def _expanddots(dots: Any, default: Any, n: int) -> list[Any]:
    return _recycle(default if dots is None else dots, n)


def _expanddotslist(dots: Any, n: int) -> list[Any]:
    if dots is None:
        return [None] * n
    if (
        isinstance(dots, (list, tuple))
        and dots
        and isinstance(dots[0], (list, tuple, np.ndarray))
    ):
        pieces = list(dots)
    else:
        pieces = [dots]
    return [pieces[i % len(pieces)] for i in range(n)]


def _extract(dots: dict[str, Any], index: int) -> dict[str, Any]:
    """``index`` is 1-based, matching ``extractdots``."""
    out: dict[str, Any] = {}
    for key, val in dots.items():
        if callable(val):
            out[key] = val
            continue
        if isinstance(val, list):
            pos = index - 1
            out[key] = val[pos] if 0 <= pos < len(val) else None
        else:
            out[key] = val
    return out


def _convert2wide(labels: np.ndarray, times: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, list[Any]]:
    """R ``convert2wide``: long (name, x, value) rows become one block per name."""
    seen: list[str] = []
    for label in labels:
        text = str(label)
        if text not in seen:
            seen.append(text)
    blocks = []
    for name in seen:
        mask = np.array([str(label) == name for label in labels])
        blocks.append((times[mask].astype(float), values[mask].astype(float)))
    first_x, first_y = blocks[0]
    mat = np.column_stack([first_x, first_y])
    names: list[Any] = ["x", seen[0]]
    for name, (xs, ys) in zip(seen[1:], blocks[1:]):
        mat = np.column_stack([mat, np.full(mat.shape[0], np.nan)])
        extra = np.column_stack(
            [xs, np.full((xs.size, mat.shape[1] - 2), np.nan), ys]
        )
        mat = np.vstack([mat, extra])
        names.append(name)
    return mat, names


def _frame(obs: Any) -> tuple[np.ndarray, list[Any]]:
    if isinstance(obs, dict) and "data" not in obs and not hasattr(obs, "data"):
        names = list(obs.keys())
        columns = [np.asarray(obs[name], dtype=np.float64).reshape(-1) for name in names]
        return np.column_stack(columns), names
    data = getattr(obs, "data", obs)
    raw = np.asarray(data, dtype=object)
    if raw.ndim != 2:
        raise ValueError("'obs' should be either a 'data.frame' or a 'matrix'")
    names = getattr(obs, "colnames", None)
    first = raw[:, 0]
    if any(isinstance(item, str) for item in first):
        times = np.asarray(raw[:, 1], dtype=np.float64)
        values = np.asarray(raw[:, 2], dtype=np.float64)
        return _convert2wide(first, times, values)
    array = np.asarray(raw, dtype=np.float64)
    if names is None:
        names = [str(i + 1) for i in range(array.shape[1])]
    return array, list(names)


def _set_data(obs: Any) -> dict[str, Any]:
    if obs is None:
        return {"dat": None, "pos": None, "name": None, "length": 0, "par": {}}
    frames = obs if isinstance(obs, (list, tuple)) and obs and not isinstance(obs[0], (int, float, str)) else [obs]
    if isinstance(obs, dict) and not hasattr(obs, "data"):
        frames = [obs]
    dat = None
    names: list[Any] | None = None
    pos_rows = []
    for frame in frames:
        block, block_names = _frame(frame)
        if dat is None:
            dat = block
            names = block_names
            pos_rows.append([1, block.shape[0]])
        else:
            start = dat.shape[0] + 1
            # Columns already aligned for a single frame. Extra frames are
            # appended when they share the same columns.
            if block.shape[1] != dat.shape[1]:
                raise ValueError("the elements in 'obs' should be either a 'data.frame' or a 'matrix'")
            dat = np.vstack([dat, block])
            pos_rows.append([start, dat.shape[0]])
    pos = np.asarray(pos_rows, dtype=int)
    return {"dat": dat, "pos": pos, "name": names, "length": int(pos.shape[0]), "par": {}}


def _which_items(which: Any) -> list[Any]:
    if isinstance(which, (str, bytes)):
        return [which]
    if isinstance(which, (bool, np.bool_)):
        raise ValueError("index in 'which' should be > 0")
    if isinstance(which, (int, np.integer, float, np.floating)):
        return [which]
    return list(which)


def _which_var_obs(which: Any, obs: dict[str, Any], nvar: int, varnames: list[Any]) -> list[Any]:
    if which is None and obs["dat"] is None:
        return list(range(1, nvar + 1))
    if which is None:
        obs_names = obs.get("name") or []
        hits = [i for i, name in enumerate(varnames) if name in obs_names]
        return [varnames[i] for i in hits]
    return _which_items(which)


def _select1d(which: list[Any], var: list[Any], att: dict[str, Any]) -> dict[str, Any]:
    proddim = _prod_dim(att)
    lengthvar = att.get("lengthvar")
    if lengthvar is None:
        csum = np.asarray([], dtype=int)
    else:
        csum = np.cumsum(np.asarray(lengthvar, dtype=int).reshape(-1)) + 2
    if which and isinstance(which[0], str):
        select = []
        for item in which:
            hits = [i + 1 for i, name in enumerate(var) if name == item]
            if not hits:
                raise ValueError(f"variable {item} not in variable names")
            select.append(hits[0])
    else:
        select = [int(item) for item in which]
        if max(select) > len(var):
            raise ValueError("index in 'which' too large")
        if min(select) < 1:
            raise ValueError("index in 'which' should be > 0")
    nspec = int(att["nspec"])
    istart = np.zeros(len(select), dtype=int)
    istop = np.zeros(len(select), dtype=int)
    for i, sel in enumerate(select):
        if sel <= nspec:
            istart[i] = (sel - 1) * proddim + 2
            istop[i] = istart[i] + proddim - 1
        else:
            ii = sel - nspec
            istart[i] = int(csum[ii - 1])
            istop[i] = int(csum[ii] - 1)
        if istart[i] == istop[i]:
            raise ValueError(f"variable {which[i]} is not a 1-D variable")
    return {"Which": select, "istart": istart, "istop": istop}


def _select_name(which_name: Any, var: list[Any]) -> float:
    hits = [i + 1 for i, name in enumerate(var) if name == which_name]
    if not hits:
        return float("nan")
    return float(hits[0])


def _update_obs(obs: dict[str, Any], varnames: list[Any], xwhich: list[int]) -> dict[str, Any]:
    if obs["length"] > 0:
        chosen = []
        ncol = 0 if obs["dat"] is None else obs["dat"].shape[1]
        for index in xwhich:
            found = _select_name(varnames[index - 1], list(obs["name"]))
            if not _na(found) and found > ncol:
                found = float("nan")
            chosen.append(found)
        obs["Which"] = chosen
    else:
        obs["Which"] = [float("nan")] * len(xwhich)
    return obs


def _range_merge(current: tuple[float, float] | None, values: Any, use_log: bool) -> tuple[float, float]:
    vals = np.asarray(values, dtype=np.float64).reshape(-1)
    vals = vals[~np.isnan(vals)]
    if use_log and vals.size:
        positive = vals[vals > 0]
        if positive.size:
            vals = np.where(vals <= 0, np.min(positive), vals)
        else:
            vals = np.where(vals <= 0, np.inf, vals)
    if vals.size == 0:
        if current is None:
            return (float("inf"), float("-inf"))
        return current
    lo = float(np.min(vals))
    hi = float(np.max(vals))
    if current is None:
        return (lo, hi)
    return (min(current[0], lo), max(current[1], hi))


def _set_range(lim, data, others, isub, istart, istop, obs, io, use_log) -> tuple[float, float]:
    if lim is not None:
        pair = np.asarray(lim, dtype=np.float64).reshape(-1)
        return (float(pair[0]), float(pair[1]))
    rows = np.asarray(isub, dtype=int) - 1
    cols = slice(istart - 1, istop)
    yrange = _range_merge(None, data[rows][:, cols], use_log)
    for other in others:
        yrange = _range_merge(yrange, other[rows][:, cols], use_log)
    if not _na(io):
        yrange = _range_merge(yrange, obs["dat"][:, int(io) - 1], use_log)
    return yrange


def _splitdots(ldots: dict[str, Any], varnames: list[Any]) -> dict[str, Any]:
    others = []
    dots: dict[str, Any] = {}
    for key, item in ldots.items():
        if _is_desolve(item):
            others.append(item)
        elif isinstance(item, (list, tuple)) and item and _is_desolve(item[0]):
            others.extend(item)
        elif item is not None:
            dots[key] = item
    for item in others:
        if list(item.colnames) != list(varnames):
            raise ValueError(
                "'x' is not compatible with other deSolve objects - colnames not the same"
            )
    main = {key: value for key, value in dots.items() if key in _PLOT_NAMES}
    points = {key: value for key, value in dots.items() if key not in _PLOT_NAMES}
    return {"points": points, "main": main, "x2": others}


def _mfrow(ldots: dict[str, Any], nv: int) -> tuple[int, int]:
    if "mfrow" not in ldots and "mfcol" not in ldots:
        nc = min(int(np.ceil(np.sqrt(nv))), 3)
        nr = min(int(np.ceil(nv / nc)), 3) if nc else 1
        return (max(nr, 1), max(nc, 1))
    if "mfcol" in ldots and ldots["mfcol"] is not None:
        pair = tuple(int(v) for v in ldots["mfcol"])
        return (pair[1], pair[0])
    if ldots.get("mfrow") is None:
        return (1, 1)
    pair = tuple(int(v) for v in ldots["mfrow"])
    return (pair[0], pair[1])


def _log_flag(log_value: Any, axis: str) -> bool:
    if log_value is None:
        return False
    return axis in str(log_value)


def _time_label(value: float) -> str:
    if np.isfinite(value) and float(value).is_integer():
        return f"time {int(value)}"
    text = np.format_float_positional(float(value), trim="-")
    return f"time {text}"


def _subset_rows(subset: Any, data: np.ndarray, colnames: list[Any]) -> list[int]:
    if subset is None:
        return list(range(1, data.shape[0] + 1))
    if isinstance(subset, str):
        env = {str(name): data[:, i] for i, name in enumerate(colnames)}
        env["c"] = lambda *args: np.array(args, dtype=float)
        evaluated = eval(subset, {"__builtins__": {}}, env)  # noqa: S307 — R subset expression
        return _subset_rows(evaluated, data, colnames)
    array = np.asarray(subset)
    if array.dtype == bool or array.dtype == np.bool_:
        mask = array.reshape(-1)
        if mask.size == 1:
            mask = np.full(data.shape[0], bool(mask[0]))
        keep = mask & ~np.isnan(mask.astype(float))
        return [i + 1 for i, flag in enumerate(keep) if flag]
    if np.issubdtype(array.dtype, np.number):
        return [int(item) for item in array.reshape(-1)]
    raise ValueError("'subset' must evaluate to logical or be a vector with integers")


def _color(value: Any) -> str:
    if value is None:
        return "#000000"
    if isinstance(value, (int, np.integer)) and not isinstance(value, bool):
        return _R_PALETTE[(int(value) - 1) % len(_R_PALETTE)]
    return str(value)


def _linestyle(value: Any):
    if value is None:
        return "solid"
    if isinstance(value, str) and not value.isdigit():
        return value
    return _LTY[(int(value) - 1) % len(_LTY)]


def _style(dots: dict[str, Any]) -> dict[str, Any]:
    kind = dots.get("type", "p")
    if kind is None:
        kind = "p"
    width = dots.get("lwd", 1)
    if width is None:
        width = 1
    return {
        "type": str(kind),
        "color": _color(dots.get("col", 1)),
        "lw": float(width),
        "ls": _linestyle(dots.get("lty", 1)),
    }


def _r_limits(lo: float, hi: float, interior: bool) -> tuple[float, float]:
    reverse = lo > hi
    if reverse:
        lo, hi = hi, lo
    if lo == hi:
        if lo == 0:
            lo, hi = -1.0, 1.0
        else:
            span = abs(lo)
            lo = lo - 0.4 * span
            hi = hi + 0.4 * span
    if not interior:
        pad = 0.04 * (hi - lo)
        lo -= pad
        hi += pad
    if reverse:
        return hi, lo
    return lo, hi


def _draw_series(ax, xs, ys, style: dict[str, Any]) -> None:
    kind = style["type"]
    if kind == "n":
        return
    line = kind in {"l", "b", "o", "s", "S", "h"}
    point = kind in {"p", "b", "o"}
    if line:
        ax.plot(xs, ys, color=style["color"], lw=style["lw"], ls=style["ls"])
    if point:
        ax.plot(
            xs,
            ys,
            linestyle="none",
            marker="o",
            color=style["color"],
            markersize=4,
        )


def _draw_vertical(ax, dotmain: dict[str, Any], xmin: float) -> None:
    xlim = dotmain.get("xlim")
    ylim = dotmain.get("ylim")
    v = xmin if xlim is None else xlim[0]
    if ylim is not None:
        ax.axhline(ylim[1], color="black", lw=0.8)
    ax.axvline(v, color="black", lw=0.8)


def _apply_axes(ax, xs, ys, dotmain: dict[str, Any]) -> None:
    interior = str(dotmain.get("xaxs", "r")) == "i"
    if dotmain.get("xlim") is not None:
        lo, hi = dotmain["xlim"]
    else:
        finite = np.asarray(xs, dtype=float)
        finite = finite[np.isfinite(finite)]
        lo, hi = (float(np.min(finite)), float(np.max(finite))) if finite.size else (0.0, 1.0)
    ax.set_xlim(*_r_limits(lo, hi, interior or _log_flag(dotmain.get("log"), "x")))
    interior_y = str(dotmain.get("yaxs", "r")) == "i"
    if dotmain.get("ylim") is not None:
        lo, hi = dotmain["ylim"]
    else:
        finite = np.asarray(ys, dtype=float)
        finite = finite[np.isfinite(finite)]
        lo, hi = (float(np.min(finite)), float(np.max(finite))) if finite.size else (0.0, 1.0)
    ax.set_ylim(*_r_limits(lo, hi, interior_y or _log_flag(dotmain.get("log"), "y")))
    if _log_flag(dotmain.get("log"), "x"):
        ax.set_xscale("log")
    if _log_flag(dotmain.get("log"), "y"):
        ax.set_yscale("log")
    show_axes = dotmain.get("axes", True)
    if show_axes is None:
        show_axes = True
    if not show_axes:
        ax.set_axis_off()
    ax.set_xlabel("" if dotmain.get("xlab") is None else str(dotmain.get("xlab")))
    ax.set_ylabel("" if dotmain.get("ylab") is None else str(dotmain.get("ylab")))
    title = dotmain.get("main")
    ax.set_title("" if title is None else str(title))


class _Page:
    def __init__(self, mfrow: tuple[int, int]):
        self.mfrow = mfrow
        self.figure, self.axes = plt.subplots(
            mfrow[0],
            mfrow[1],
            squeeze=False,
            figsize=(7, 5),
        )
        self.used = 0

    def axis(self):
        nr, nc = self.mfrow
        flat = self.used
        row, col = divmod(flat, nc)
        self.used += 1
        return self.axes[row, col]


def plot_1d(
    x,
    *others,
    select=None,
    which=None,
    ask=None,
    obs=None,
    obspar=None,
    grid=None,
    xyswap=False,
    delay=0,
    vertical=False,
    subset=None,
    **kwargs,
):
    """Plot each selected 1-D variable at each output time.

    ``which`` is a 1-based species index or a name, as in R. A missing grid
    is ``1, 2, ..., n``. ``xyswap=True`` puts the profile on the horizontal
    axis and the grid, from high to low, on the vertical axis.
    """
    if which is None:
        which = select
    dimens = getattr(x, "dimens", None)
    if _dimens_length(dimens) != 1:
        raise ValueError("plot.1D only works for models solved with 'ode.1D'")
    nspec = getattr(x, "nspec", None)
    if nspec is None:
        raise ValueError("plot.1D only works for models solved with 'ode.1D'")
    nspec = int(nspec)
    data = _matrix(x)
    att = {
        "nspec": nspec,
        "dimens": dimens,
        "map": getattr(x, "map", None),
        "lengthvar": getattr(x, "lengthvar", None),
    }
    proddim = _prod_dim(att)
    if (data.shape[1] - nspec * proddim) < 1:
        raise ValueError("ncol of 'x' should be > 'nspec' * dimens if x is a vector")

    observed = _set_data(obs)
    ynames = getattr(x, "ynames", None)
    if ynames is None:
        varnames: list[Any] = list(range(1, nspec + 1))
    else:
        varnames = list(ynames)
    length_names = getattr(x, "lengthvar_names", None)
    if att["lengthvar"] is not None and length_names:
        varnames.extend(list(length_names)[1:])

    chosen = _which_var_obs(which, observed, nspec, varnames)
    npanels = len(chosen)
    selected = _select1d(chosen, varnames, att)
    xwhich = selected["Which"]
    observed = _update_obs(observed, varnames, xwhich)
    if obspar:
        observed["par"] = {key: _recycle(val, observed["length"]) for key, val in obspar.items()}

    named_others = [item for item in others if _is_desolve(item)]
    colnames = _colnames(x, data.shape[1])
    dots = _splitdots(dict(kwargs), colnames)
    dots["x2"] = named_others + dots["x2"]
    for item in named_others:
        if list(item.colnames) != colnames:
            raise ValueError(
                "'x' is not compatible with other deSolve objects - colnames not the same"
            )

    layout = _mfrow(kwargs, npanels)
    per_page = layout[0] * layout[1]
    empty = per_page - npanels if npanels < per_page else 0

    main_dots = {key: _recycle(val, npanels) for key, val in dots["main"].items()}
    nx = len(dots["x2"]) + 1
    point_dots = {key: _recycle(val, nx) for key, val in dots["points"].items()}
    main_dots["xlab"] = _expanddots(kwargs.get("xlab"), "x", npanels)
    main_dots["ylab"] = _expanddots(
        kwargs.get("ylab"),
        [varnames[index - 1] for index in xwhich],
        npanels,
    )
    xxlim = _expanddotslist(kwargs.get("xlim"), npanels)
    yylim = _expanddotslist(kwargs.get("ylim"), npanels)
    swapped = _recycle(xyswap, npanels)
    upright = _recycle(vertical, npanels)
    grids = _expanddotslist(grid, npanels)

    isub = _subset_rows(subset, data, colnames)
    times = data[np.asarray(isub, dtype=int) - 1, 0]
    main_source = main_dots.get("main")
    titles = _expanddots(None if main_source is None else main_source, [_time_label(t) for t in times], len(times))

    other_data = [_matrix(item) for item in dots["x2"]]
    panels: list[dict[str, Any]] = []
    pages: list[_Page] = []
    page: _Page | None = None
    slot = 0

    def _next_axis():
        nonlocal page, slot
        if page is None or slot % per_page == 0:
            page = _Page(layout)
            pages.append(page)
            slot = 0
        ax = page.axis()
        slot += 1
        return ax

    for j in isub:
        for ip in range(npanels):
            istart = int(selected["istart"][ip])
            istop = int(selected["istop"][ip])
            io = observed["Which"][ip]
            out = data[j - 1, istart - 1 : istop]
            grid_val = grids[ip]
            if grid_val is None:
                grid_arr = np.arange(1, out.size + 1, dtype=float)
            else:
                grid_arr = np.asarray(grid_val, dtype=np.float64).reshape(-1)
            dotmain = _extract(main_dots, ip + 1)
            dotpoints = _extract(point_dots, 1)
            title_pos = j - 1
            dotmain["main"] = titles[title_pos] if 0 <= title_pos < len(titles) else None
            if upright[ip]:
                swapped[ip] = True
                dotmain["axes"] = False
                dotmain["xlab"] = ""
                dotmain["xaxs"] = "i"
                dotmain["yaxs"] = "i"
            xlog = _log_flag(dotmain.get("log"), "x")
            ylog = _log_flag(dotmain.get("log"), "y")
            if not swapped[ip]:
                if xxlim[ip] is not None:
                    pair = np.asarray(xxlim[ip], dtype=float).reshape(-1)
                    dotmain["xlim"] = (float(pair[0]), float(pair[1]))
                dotmain["ylim"] = _set_range(
                    yylim[ip], data, other_data, isub, istart, istop, observed, io, ylog
                )
                xs, ys = grid_arr, out
            else:
                if yylim[ip] is not None:
                    pair = np.asarray(yylim[ip], dtype=float).reshape(-1)
                    dotmain["ylim"] = (float(pair[0]), float(pair[1]))
                dotmain["xlim"] = _set_range(
                    xxlim[ip], data, other_data, isub, istart, istop, observed, io, xlog
                )
                if yylim[ip] is None and swapped[ip]:
                    dotmain["ylim"] = (float(np.max(grid_arr)), float(np.min(grid_arr)))
                xs, ys = out, grid_arr
            ax = _next_axis()
            style = _style(dotpoints)
            _draw_series(ax, xs, ys, style)
            _apply_axes(ax, xs, ys, dotmain)
            line_rows = []
            for jj, other in enumerate(other_data, start=2):
                extra_style = _style(_extract(point_dots, jj))
                extra_x = other[j - 1, istart - 1 : istop]
                if swapped[ip]:
                    lx, ly = extra_x, grid_arr
                else:
                    lx, ly = grid_arr, extra_x
                _draw_series(ax, lx, ly, extra_style)
                line_rows.append({"x": np.asarray(lx, dtype=float), "y": np.asarray(ly, dtype=float)})
            point_rows = []
            if not _na(io) and observed["dat"] is not None:
                column = int(io) - 1
                for block in range(min(observed["pos"].shape[0], observed["length"])):
                    start, stop = observed["pos"][block]
                    rows = slice(int(start) - 1, int(stop))
                    if swapped[ip]:
                        px = observed["dat"][rows, column]
                        py = observed["dat"][rows, 0]
                    else:
                        px = observed["dat"][rows, 0]
                        py = observed["dat"][rows, column]
                    ax.scatter(px, py, c="black", s=18, zorder=3)
                    point_rows.append(
                        {"x": np.asarray(px, dtype=float), "y": np.asarray(py, dtype=float)}
                    )
            if upright[ip]:
                _draw_vertical(ax, dotmain, float(np.min(out)))
            panels.append(
                {
                    "x": np.asarray(xs, dtype=float),
                    "y": np.asarray(ys, dtype=float),
                    "xlim": dotmain.get("xlim"),
                    "ylim": dotmain.get("ylim"),
                    "main": dotmain.get("main"),
                    "xlab": dotmain.get("xlab"),
                    "ylab": dotmain.get("ylab"),
                    "lines": line_rows,
                    "points": point_rows,
                }
            )
        for _ in range(empty):
            ax = _next_axis()
            ax.set_axis_off()
            panels.append(
                {
                    "x": np.array([1.0]),
                    "y": np.array([0.0]),
                    "xlim": None,
                    "ylim": None,
                    "main": None,
                    "xlab": "",
                    "ylab": "",
                    "lines": [],
                    "points": [],
                    "empty": True,
                }
            )
        if delay and delay > 0:
            time.sleep(0.001 * float(delay))

    for old in pages[:-1]:
        plt.close(old.figure)
    figure = pages[-1].figure if pages else None
    if figure is not None:
        figure.tight_layout()
    return Plot1DDrawn(figure, panels)
