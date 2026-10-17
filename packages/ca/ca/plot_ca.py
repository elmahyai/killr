"""Plot a simple correspondence analysis map: Python translation of R's plot.ca (ca 0.72).

``plot_ca_data`` computes everything the R function computes before it draws:
the map coordinates, the profiles selected by ``what``, the symbols, colours,
label offsets, axis limits and axis titles. ``plot_ca`` draws that data with
Matplotlib. Dimensions are 1-based, as in R.
"""

import numpy as np
import matplotlib.pyplot as plt

from ._plotcommon import (
    MAP_TYPES, axes_pin, contrib_colours, percent_labels, principal_maps,
    rep_len, select_side,
)
from ._rgraphics import PDF_PIN, r_plot_limits, r_strheight, r_strwidth
from ._symbols import draw_lines, draw_points, draw_text


def _names(values):
    return [str(v) for v in values]


def plot_ca_data(obj, pin=PDF_PIN, dim=(1, 2), map="symmetric", what=("all", "all"),
                 mass=(False, False), contrib=("none", "none"), col=("blue", "red"),
                 pch=(16, 21, 17, 24), labels=(2, 2), lines=(False, False), lwd=1,
                 xlab="_auto_", ylab="_auto_", col_lab=("blue", "red"),
                 arrows=(False, False)):
    """Compute the data plot.ca would draw, without drawing.

    ``obj`` is a dict from ``ca.ca.ca``. ``rowsup``/``colsup`` are 0-based lists.
    ``pin`` is the plot region in inches (R's par("pin")).
    """
    if any(arrows):
        raise NotImplementedError("plot.ca arrows = TRUE is not translated")
    if map not in MAP_TYPES:
        raise ValueError(f"unknown map type {map!r}")
    what = rep_len(what, 2)
    mass = rep_len(mass, 2)
    contrib = rep_len(contrib, 2)
    col = rep_len(col, 2)
    labels = rep_len(labels, 2)
    pch = rep_len(pch, 4)
    lines = rep_len(lines, 2)
    col_lab = rep_len(col_lab, 2)
    dim = [int(d) for d in dim]

    # R checks x$suprow and x$supcol, which are NULL for a ca object, so these
    # adjustments always apply.
    if map in ("colgab", "colgreen") and what[0] != "none":
        what[0] = "active"
    if map in ("rowgab", "rowgreen") and what[1] != "none":
        what[1] = "active"

    rowcoord = np.array(obj["rowcoord"], dtype=float)
    colcoord = np.array(obj["colcoord"], dtype=float)
    sv = np.asarray(obj["sv"], dtype=float)
    rowmass = np.asarray(obj["rowmass"], dtype=float)
    colmass = np.asarray(obj["colmass"], dtype=float)
    rowinertia = np.asarray(obj["rowinertia"], dtype=float)
    colinertia = np.asarray(obj["colinertia"], dtype=float)

    # sign switching for negative dimensions
    if min(dim) < 0:
        swisign = np.array(rep_len([-1 if d < 0 else 1 for d in dim], rowcoord.shape[1]))
        rowcoord = rowcoord * swisign[None, :]
        colcoord = colcoord * swisign[None, :]
        dim = [abs(d) for d in dim]

    (xfull, yfull), rpc, cpc = principal_maps(
        rowcoord, colcoord, sv, rowmass, colmass, map)
    x_names_full = _names(obj["rownames"])
    y_names_full = _names(obj["colnames"])
    rowsup = list(obj.get("rowsup") or [])
    colsup = list(obj.get("colsup") or [])
    indx = xfull.shape[0]
    indy = yfull.shape[0]

    xs = select_side(xfull, x_names_full, rowsup, pch[0], pch[1], what[0])
    ys = select_side(yfull, y_names_full, colsup, pch[2], pch[3], what[1])
    dcols = [d - 1 for d in dim]
    xs_coords = None if xs["coords"] is None else xs["coords"][:, dcols]
    ys_coords = None if ys["coords"] is None else ys["coords"][:, dcols]

    # point sizes
    if mass[0]:
        cex_x = 0.5 + rowmass ** (1 / 3) / np.max(rowmass ** (1 / 3))
        cex_x = list(cex_x)
    else:
        cex_x = [1.0]
    if mass[1]:
        cex_y = 0.5 + colmass ** (1 / 3) / np.max(colmass ** (1 / 3))
        cex_y = list(cex_y)
    else:
        cex_y = [1.0]

    # colours: the base colour, or a contribution ramp
    col_x = [col[0]]
    col_y = [col[1]]
    if contrib[0] == "relative":
        cind = rowmass * (rpc[:, dcols[0]] ** 2 + rpc[:, dcols[1]] ** 2) / rowinertia
        col_x = contrib_colours(col[0], "relative", cind, indx)
    elif contrib[0] == "absolute":
        cind = rowmass * (rpc[:, dcols[0]] ** 2 + rpc[:, dcols[1]] ** 2) / (
            sv[dim[0] - 1] ** 2 + sv[dim[1] - 1] ** 2)
        col_x = contrib_colours(col[0], "absolute", cind, indx)
    if contrib[1] == "relative":
        cind = colmass * (cpc[:, dcols[0]] ** 2 + cpc[:, dcols[1]] ** 2) / colinertia
        col_y = contrib_colours(col[1], "relative", cind, indy)
    elif contrib[1] == "absolute":
        cind = colmass * (cpc[:, dcols[0]] ** 2 + cpc[:, dcols[1]] ** 2) / (
            sv[dim[0] - 1] ** 2 + sv[dim[1] - 1] ** 2)
        col_y = contrib_colours(col[1], "absolute", cind, indy)

    # limits: plot(c(x[,1], y[,1]), c(x[,2], y[,2]), asp = 1)
    xvals = []
    yvals = []
    for coords in (xs_coords, ys_coords):
        if coords is not None:
            xvals.extend(coords[:, 0])
            yvals.extend(coords[:, 1])
    xlim, ylim = r_plot_limits(xvals, yvals, pin)

    # axis titles
    pct = percent_labels(sv, dim)
    if xlab == "_auto_":
        xlab = "Dimension %d%s" % (dim[0], pct[0])
    if ylab == "_auto_":
        ylab = "Dimension %d%s" % (dim[1], pct[1])

    ops = []
    if xs_coords is not None and labels[0] != 1:
        ops.append({
            "kind": "points", "side": "rows",
            "x": xs_coords[:, 0], "y": xs_coords[:, 1],
            "pch": xs["pch"], "cex": cex_x, "col": col_x,
        })
    if labels[0] > 0:
        ops.append(_label_op(*_na_side(xs_coords, xs["names"]), labels[0], col_lab[0],
                             xlim, ylim, pin, "rows"))
    if ys_coords is not None and labels[1] != 1:
        ops.append({
            "kind": "points", "side": "cols",
            "x": ys_coords[:, 0], "y": ys_coords[:, 1],
            "pch": ys["pch"], "cex": cex_y, "col": col_y,
        })
    if labels[1] > 0:
        ops.append(_label_op(*_na_side(ys_coords, ys["names"]), labels[1], col_lab[1],
                             xlim, ylim, pin, "cols"))
    if lines[0] and xs_coords is not None:
        order = np.argsort(xs_coords[:, 0], kind="stable")
        ops.append({"kind": "lines", "side": "rows",
                    "x": xs_coords[order, 0], "y": xs_coords[order, 1],
                    "col": col_x, "lwd": lwd})
    if lines[1] and ys_coords is not None:
        order = np.argsort(ys_coords[:, 0], kind="stable")
        ops.append({"kind": "lines", "side": "cols",
                    "x": ys_coords[order, 0], "y": ys_coords[order, 1],
                    "col": col_y, "lwd": lwd})

    colnames = ["Dim%d" % d for d in dim]
    rows_out, rows_names = _na_side(xs_coords, xs["names"])
    cols_out, cols_names = _na_side(ys_coords, ys["names"])
    result = {
        "rows": rows_out,
        "rows_names": rows_names,
        "cols": cols_out,
        "cols_names": cols_names,
        "colnames": colnames,
    }
    return {
        "xlim": xlim, "ylim": ylim, "xlab": xlab, "ylab": ylab,
        "ops": ops, "result": result,
    }


def _na_side(coords, names):
    """A hidden side is R's 1 x 2 NA matrix with one NA name."""
    if coords is None:
        return np.full((1, 2), np.nan), [None]
    return coords, names


def _label_op(coords, names, label_code, colour, xlim, ylim, pin, side):
    xoff1 = np.zeros(len(names))
    xoff2 = np.zeros(len(names))
    if label_code > 1:
        o_w = r_strwidth(["o"], 0.75, xlim, pin[0])[0]
        o_h = r_strheight(0.75, ylim, pin[1])
        xoff1 = 0.5 * r_strwidth(names, 0.75, xlim, pin[0]) + 0.5 * o_w
        xoff2 = np.full(len(names), 0.5 * r_strheight(0.75, ylim, pin[1]) + 0.5 * o_h)
    return {
        "kind": "text", "side": side,
        "x": coords[:, 0] + xoff1, "y": coords[:, 1] + xoff2,
        "labels": list(names), "col": [colour],
    }


def draw_plot_ops(ax, data):
    """Draw the operations of a computed plot onto a Matplotlib axes."""
    for op in data["ops"]:
        if op["kind"] == "points":
            draw_points(ax, op["x"], op["y"], op["pch"], op["cex"], op["col"])
        elif op["kind"] == "text":
            draw_text(ax, op["x"], op["y"], op["labels"], op["col"])
        elif op["kind"] == "lines":
            draw_lines(ax, op["x"], op["y"], op["col"], op["lwd"])


def draw_axes_frame(ax, data):
    """Limits, axis titles, and the dotted zero lines of plot.ca."""
    ax.set_xlim(*data["xlim"])
    ax.set_ylim(*data["ylim"])
    ax.set_xlabel(data["xlab"])
    ax.set_ylabel(data["ylab"])
    ax.axhline(0, linestyle=":", color="black", linewidth=1)
    ax.axvline(0, linestyle=":", color="black", linewidth=1)


def plot_ca(obj, ax=None, **kwargs):
    """Draw a ca map on ``ax`` (default: the current axes) and return rows/cols."""
    if ax is None:
        ax = plt.gca()
    data = plot_ca_data(obj, pin=axes_pin(ax), **kwargs)
    draw_axes_frame(ax, data)
    draw_plot_ops(ax, data)
    return data["result"]

