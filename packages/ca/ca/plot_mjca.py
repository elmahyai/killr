"""Plot a multiple correspondence analysis map: Python translation of R's plot.mjca (ca 0.72).

The data step mirrors R's plot.mjca up to the drawing calls. Dimensions are
1-based. The R object's ``colnames`` holds the factor names, ``levelnames`` the
"factor:level" labels, and ``levels.n`` the number of levels per factor. The
translated mjca result keeps the levels in ``levels``; the factor names and the
``lambda`` and ``inertia_e`` values are read from the object when present, and
an error is raised when a value the plot needs is missing.
"""

import numpy as np
import matplotlib.pyplot as plt

from ._plotcommon import (
    axes_pin, contrib_colours, principal_maps, rep_len, select_side,
)
from ._rgraphics import PDF_PIN, r_plot_limits, r_rep_times
from .plot_ca import _label_op, _na_side, draw_axes_frame, draw_plot_ops


def _mjca_pct(obj, dim):
    """Axis percentage strings as R's plot.mjca builds them."""
    lam = obj.get("lambda")
    if lam is None:
        raise ValueError(
            "plot.mjca needs obj['lambda'], which the translated mjca result does not return")
    if lam == "JCA":
        return ["" for _ in dim]
    if lam == "adjusted":
        if obj.get("inertia_e") is None:
            raise ValueError(
                "plot.mjca with lambda 'adjusted' needs obj['inertia_e'], "
                "which the translated mjca result does not return")
        values = np.asarray(obj["inertia_e"], dtype=float)
        pct = np.round(100.0 * values, 1)
    else:
        sv = np.asarray(obj["sv"], dtype=float)
        values = sv ** 2
        pct = np.round(100.0 * values / np.sum(values), 1)
    return [" (%s%%)" % ("%.15g" % pct[d - 1]) for d in dim]


def plot_mjca_data(obj, pin=PDF_PIN, dim=(1, 2), map="symmetric", what=("none", "all"),
                   mass=(False, False), contrib=("none", "none"),
                   col=("#000000", "#FF0000"), pch=(16, 1, 17, 24), labels=(2, 2),
                   collabels="both", arrows=(False, False), xlab="_auto_", ylab="_auto_",
                   centroids=False):
    """Compute the data plot.mjca would draw, without drawing.

    ``centroids`` is accepted for signature parity; the R body does not use it.
    """
    if any(arrows):
        raise NotImplementedError("plot.mjca arrows = TRUE is not translated")
    what = rep_len(what, 2)
    mass = rep_len(mass, 2)
    contrib = rep_len(contrib, 2)
    labels = rep_len(labels, 2)
    pch = rep_len(pch, 4)
    dim = [int(d) for d in dim]

    levels = [list(lv) for lv in obj["levels"]]
    levels_n = [len(lv) for lv in levels]
    q = len(levels_n)
    fn_names = [str(f) for f in obj.get("factor_names", [str(j + 1) for j in range(q)])]

    # col: recycled to one colour for the rows and one per factor for the columns
    col = list(col)
    if len(col) < q + 1:
        col = [col[0]] + rep_len(col[1:], q)
    col = col[: 1 + q]
    col_y_base = col[1]

    if map in ("colgab", "colgreen") and what[0] != "none":
        what[0] = "active"
    if map in ("rowgab", "rowgreen") and what[1] != "none":
        what[1] = "active"

    rowcoord = np.array(obj["rowcoord"], dtype=float)
    colcoord = np.array(obj["colcoord"], dtype=float)
    sv = np.asarray(obj["sv"], dtype=float)
    rowmass = np.asarray(obj["rowmass"], dtype=float)
    colmass = np.asarray(obj["colmass"], dtype=float)

    (xfull, yfull), rpc, cpc = principal_maps(
        rowcoord, colcoord, sv, rowmass, colmass, map)
    x_names_full = [str(v) for v in obj.get("rownames", range(1, len(rowmass) + 1))]
    if collabels == "both":
        y_names_full = [f"{fn_names[j]}:{lev}" for j in range(q) for lev in levels[j]]
    elif collabels == "level":
        y_names_full = [lev for j in range(q) for lev in levels[j]]
    elif collabels == "factor":
        y_names_full = [fn_names[j] for j in range(q) for _ in levels[j]]
    else:
        raise ValueError("collabels must be 'both', 'level' or 'factor'")
    rowsup = []  # plot.mjca has no supplementary rows: its row sup is always NA
    colsup = list(obj.get("colsup") or [])
    indx = xfull.shape[0]
    indy = yfull.shape[0]

    xs = select_side(xfull, x_names_full, rowsup, pch[0], pch[1], what[0])
    ys = select_side(yfull, y_names_full, colsup, pch[2], pch[3], what[1])
    dcols = [d - 1 for d in dim]
    xs_coords = None if xs["coords"] is None else xs["coords"][:, dcols]
    ys_coords = None if ys["coords"] is None else ys["coords"][:, dcols]

    if mass[0]:
        cex_x = list(0.5 + rowmass ** (1 / 3) / np.max(rowmass ** (1 / 3)))
    else:
        cex_x = [0.5]
    if mass[1]:
        cex_y = list(0.5 + colmass ** (1 / 3) / np.max(colmass ** (1 / 3)))
    else:
        cex_y = [1.0]

    col_x = [col[0]]
    col_y = r_rep_times(col[1:], levels_n)
    if contrib[0] == "relative":
        rowinertia = np.asarray(obj["rowinertia"], dtype=float)
        cind = rowmass * (rpc[:, dcols[0]] ** 2 + rpc[:, dcols[1]] ** 2) / rowinertia
        col_x = contrib_colours(col[0], "relative", cind, indx)
    elif contrib[0] == "absolute":
        cind = rowmass * (rpc[:, dcols[0]] ** 2 + rpc[:, dcols[1]] ** 2) / (
            sv[dim[0] - 1] ** 2 + sv[dim[1] - 1] ** 2)
        col_x = contrib_colours(col[0], "absolute", cind, indx)
    if contrib[1] == "relative":
        colinertia = np.asarray(obj["colinertia"], dtype=float)
        cind = colmass * (cpc[:, dcols[0]] ** 2 + cpc[:, dcols[1]] ** 2) / colinertia
        col_y = contrib_colours(col_y_base, "relative", cind, indy)
    elif contrib[1] == "absolute":
        cind = colmass * (cpc[:, dcols[0]] ** 2 + cpc[:, dcols[1]] ** 2) / (
            sv[dim[0] - 1] ** 2 + sv[dim[1] - 1] ** 2)
        col_y = contrib_colours(col_y_base, "absolute", cind, indy)

    xvals = []
    yvals = []
    for coords in (xs_coords, ys_coords):
        if coords is not None:
            xvals.extend(coords[:, 0])
            yvals.extend(coords[:, 1])
    xlim, ylim = r_plot_limits(xvals, yvals, pin)

    pct = _mjca_pct(obj, dim)
    if xlab == "_auto_":
        xlab = "Dimension %d%s" % (dim[0], pct[0])
    if ylab == "_auto_":
        ylab = "Dimension %d%s" % (dim[1], pct[1])

    cex_x_raw = cex_x
    ops = []
    if xs_coords is not None and labels[0] != 1:
        ops.append({
            "kind": "points", "side": "rows",
            "x": xs_coords[:, 0], "y": xs_coords[:, 1],
            "pch": xs["pch"], "cex": cex_x_raw, "col": col_x,
        })
    if labels[0] > 0:
        ops.append(_label_op(*_na_side(xs_coords, xs["names"]), labels[0], "black",
                             xlim, ylim, pin, "rows"))
    if ys_coords is not None and labels[1] != 1:
        ops.append({
            "kind": "points", "side": "cols",
            "x": ys_coords[:, 0], "y": ys_coords[:, 1],
            "pch": ys["pch"], "cex": cex_y, "col": col_y,
        })
    if labels[1] > 0:
        ops.append(_label_op(*_na_side(ys_coords, ys["names"]), labels[1], "black",
                             xlim, ylim, pin, "cols"))

    rows_out, rows_names = _na_side(xs_coords, xs["names"])
    cols_out, cols_names = _na_side(ys_coords, ys["names"])
    result = {
        "rows": rows_out,
        "rows_names": rows_names,
        "cols": cols_out,
        "cols_names": cols_names,
        "colnames": ["Dim%d" % d for d in dim],
    }
    return {
        "xlim": xlim, "ylim": ylim, "xlab": xlab, "ylab": ylab,
        "ops": ops, "result": result,
    }


def plot_mjca(obj, ax=None, **kwargs):
    """Draw an mjca map on ``ax`` (default: the current axes) and return rows/cols."""
    if ax is None:
        ax = plt.gca()
    data = plot_mjca_data(obj, pin=axes_pin(ax), **kwargs)
    draw_axes_frame(ax, data)
    draw_plot_ops(ax, data)
    return data["result"]
