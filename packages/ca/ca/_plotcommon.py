"""Computations shared by the 2D correspondence plots (R's plot.ca and plot.mjca).

Each helper reproduces one block of the R code: the map choice, the profile
selection by ``what``, and the contribution colour ramps. Nothing here draws.
"""

import numpy as np

from ._rgraphics import contrib_palette, r_index_colours

MAP_TYPES = (
    "symmetric", "rowprincipal", "colprincipal", "symbiplot",
    "rowgab", "colgab", "rowgreen", "colgreen",
)
WHAT_TYPES = ("none", "active", "supplementary", "all")
NC0 = 50


def rep_len(values, n):
    """rep(values, length = n) for an R vector given as a list or scalar."""
    if not isinstance(values, (list, tuple, np.ndarray)):
        values = [values]
    values = list(values)
    return [values[i % len(values)] for i in range(n)]


def principal_maps(rowcoord, colcoord, sv, rowmass, colmass, map_type):
    """Return the (x, y) coordinate matrices for one map type (R's mtlut)."""
    rowcoord = np.asarray(rowcoord, dtype=float)
    colcoord = np.asarray(colcoord, dtype=float)
    sv = np.asarray(sv, dtype=float)
    rowmass = np.asarray(rowmass, dtype=float)
    colmass = np.asarray(colmass, dtype=float)
    k = rowcoord.shape[1]
    svk = sv[:k]
    rpc = rowcoord * svk[None, :]
    cpc = colcoord * svk[None, :]
    symrpc = rowcoord * np.sqrt(svk)[None, :]
    symcpc = colcoord * np.sqrt(svk)[None, :]
    maps = {
        "symmetric": (rpc, cpc),
        "rowprincipal": (rpc, colcoord),
        "colprincipal": (rowcoord, cpc),
        "symbiplot": (symrpc, symcpc),
        "rowgab": (rpc, colcoord * colmass[:, None]),
        "colgab": (rowcoord * rowmass[:, None], cpc),
        "rowgreen": (rpc, colcoord * np.sqrt(colmass)[:, None]),
        "colgreen": (rowcoord * np.sqrt(rowmass)[:, None], cpc),
    }
    if map_type not in maps:
        raise ValueError(f"unknown map type {map_type!r}")
    return maps[map_type], rpc, cpc


def select_side(full, names, sup, pch_active, pch_sup, what):
    """Select the rows (or columns) to draw for one side, as plot.ca does.

    Returns a dict with ``coords`` (None for NA), ``names``, ``index``
    (0-based, None for NA) and ``pch`` (the raw vector R passes to points()).
    """
    n = full.shape[0]
    sup = list(sup or [])
    pch_full = [pch_active] * n
    for i in sup:
        pch_full[i] = pch_sup
    if what == "none":
        return {"coords": None, "names": None, "index": None, "pch": None}
    if what == "active":
        index = [i for i in range(n) if i not in sup]
        pch_raw = [pch_active] * n
    elif what == "supplementary":
        if not sup:
            return {"coords": None, "names": None, "index": None, "pch": None}
        index = sup
        pch_raw = [pch_sup] * n
    elif what == "all":
        index = list(range(n))
        pch_raw = pch_full
    else:
        raise ValueError(f"unknown what {what!r}")
    return {
        "coords": full[index, :],
        "names": [names[i] for i in index],
        "index": index,
        "pch": pch_raw,
    }


def contrib_colours(base, mode, cind, n_rows):
    """Colour vector for one side from a contribution index (R's collut[xtemp])."""
    lut = contrib_palette(base, n_rows, mode, nc0=NC0)
    return r_index_colours(lut, NC0 * np.asarray(cind, dtype=float))


def axes_pin(ax):
    """Plot region size in inches for a Matplotlib axes (R's par("pin"))."""
    pos = ax.get_position()
    width, height = ax.get_figure().get_size_inches()
    return (pos.width * width, pos.height * height)


def percent_labels(sv, dims):
    """pct <- round(100 * sv^2 / sum(sv^2), 1), then " (x%)" for each dimension."""
    sv = np.asarray(sv, dtype=float)
    pct = np.round(100.0 * sv ** 2 / np.sum(sv ** 2), 1)
    out = []
    for d in dims:
        out.append(" (%s%%)" % ("%.15g" % pct[d - 1]))
    return out
