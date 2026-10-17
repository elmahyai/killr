"""Plot a 3D correspondence analysis map: Python translation of R's plot3d.ca (ca 0.72).

R draws through the rgl package. The data step here reproduces every rgl
primitive that plot3d.ca would send: the axis lines, the axis titles, the symbol
geometry for each pch (rglplot0), and the point labels. ``plot3d_ca_data``
returns those primitives as records. ``plot3d_ca`` draws them with Matplotlib's
3D axes; spheres are drawn as markers and triangles and quads as polygons.
Arrows (arrows = TRUE) are not translated.
"""

from functools import lru_cache

import numpy as np

from ._plotcommon import principal_maps, rep_len, select_side


@lru_cache(maxsize=32)
def _symbol_tables(v):
    """The rglplot0 geometry for pch 1:25, and the per-symbol radius, for size v."""
    segments = 16
    i = np.linspace(0.0, 360.0, segments)
    xc = np.repeat(np.sin(np.pi * i / 180), 2)
    yc = np.repeat(np.cos(np.pi * i / 180), 2)
    xc = xc[1:-1]
    yc = yc[1:-1]
    n_c = len(xc)
    i0 = np.array([0, 109.5, 109.5, 0, 109.5, 109.5, 0, 109.5, 109.5, 109.5, 109.5, 109.5])
    j0 = np.array([0, 0, -120, 0, -120, 120, 0, 120, 0, -120, 0, 120]) + 90
    i1 = np.array([0, 109.5, 0, 109.5, 0, 109.5, 109.5, 109.5, 109.5, 109.5, 109.5, 109.5])
    j1 = np.array([0, 0, 0, -120, 0, 120, 120, 0, 0, -120, -120, 120]) + 90
    i2 = np.concatenate([np.tile([180.0, 81.5], 4), np.repeat(81.5, 8)])
    j2 = np.array([0, -45, 0, 45, 0, 135, 0, -135, -135, -45, -45, 45, 45, 135, 135, -135], float)
    i3 = np.concatenate([i1, 180 - i1])
    j3 = np.concatenate([j1, j1 - 60])
    r = v

    def sph(ii, jj):
        return dict(
            x=r * np.sin(np.pi * ii / 180) * np.cos(np.pi * jj / 180),
            z=r * np.cos(np.pi * ii / 180),
            y=r * np.sin(np.pi * ii / 180) * np.sin(np.pi * jj / 180),
        )

    def cc(x, y, z):
        return dict(x=np.asarray(x, float), y=np.asarray(y, float), z=np.asarray(z, float))

    c01 = cc(np.concatenate([xc, yc, np.zeros(n_c)]),
             np.concatenate([np.zeros(n_c), xc, yc]),
             np.concatenate([yc, np.zeros(n_c), xc]))
    c02 = sph(i1, j1)
    c03 = cc([-1, 1, 0, 0, 0, 0], [0, 0, 0, 0, -1, 1], [0, 0, -1, 1, 0, 0])
    c04 = cc([-1, 1, 1, -1, 1, -1, -1, 1], [1, -1, 1, -1, -1, 1, -1, 1], [1, -1, -1, 1, 1, -1, -1, 1])
    c05 = cc(
        [-1, 0, 0, 0, 1, 0, 0, 0, -1, 0, -1, 0, 1, 0, 1, 0, 0, 0, -1, 0, 0, 0, 1, 0],
        [0, 0, 0, 1, 0, 0, 0, -1, 0, -1, 0, 1, 0, 1, 0, -1, 0, -1, 0, 0, 0, 1, 0, 0],
        [0, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, -1, 0, 0, -1, -1, 0, 0, -1],
    )
    c06 = sph(i2, j2)
    c11 = sph(i3, j3)
    c15 = cc(
        [-1, -1] + [1] * 8 + [-1] * 8 + [1, 1, -1, 1, 1, -1],
        [-1, 1, 1, -1, -1, -1, 1, 1, -1, -1, -1, -1, 1, 1, -1, -1, 1, 1, 1, 1, -1, -1, 1, 1],
        [1, 1, 1, 1] + [-1, 1, 1, -1, 1, -1, -1, 1] * 2 + [-1] * 4,
    )
    c16 = cc([0], [0], [0])
    c17 = sph(i0, j0)
    c18 = cc(
        0.8 * np.array([-1, 0, 1, 1, 0, 1, 1, 0, -1, -1, 0, -1, 1, 0, -1, 1, 0, 1, -1, 0, 1, -1, 0, -1]),
        0.8 * np.array([-1, 0, -1, -1, 0, 1, 1, 0, 1, 1, 0, -1, -1, 0, -1, 1, 0, -1, 1, 0, 1, -1, 0, 1]),
        np.array([0, 1, 0] * 4 + [0, -1, 0] * 4),
    )
    c19 = cc([0], [0], [0])
    c20 = cc([0], [0], [0])
    c22 = cc(
        [-1, 1, 1, 1, -1, 1] + [-1, -1, -1, -1, 1, 1, 1, 1] + [-1] * 5 + [1, 1, 1, -1, 1],
        [-1, -1, -1, 1, 1, 1, -1, 1] + [-1, -1, -1, -1, 1, 1, 1, 1] + [-1, 1, -1, -1, -1, 1, 1, 1],
        [1] * 9 + [-1, 1, -1, 1, -1, 1] + [-1] * 9,
    )

    def join(a, b):
        return cc(np.concatenate([a["x"], b["x"]]), np.concatenate([a["y"], b["y"]]),
                  np.concatenate([a["z"], b["z"]]))

    c07 = join(c22, c04)
    c08 = join(c03, c04)
    c09 = join(c05, c03)
    c10 = join(c01, c03)
    c12 = join(c22, c03)
    c13 = join(c01, c04)
    c14 = cc(
        np.concatenate([c22["x"], [1, 0, 1, 0, -1, 0, -1, 0]]),
        np.concatenate([c22["y"], [-1, 0, 1, 0, 1, 0, -1, 0]]),
        np.concatenate([c22["z"], [1, -1, 1, -1, 1, -1, 1, -1]]),
    )
    c21 = c01
    c23 = c05
    c24 = c02
    c25 = c06
    table = {1: c01, 2: c02, 3: c03, 4: c04, 5: c05, 6: c06, 7: c07, 8: c08, 9: c09,
             10: c10, 11: c11, 12: c12, 13: c13, 14: c14, 15: c15, 16: c16, 17: c17,
             18: c18, 19: c19, 20: c20, 21: c21, 22: c22, 23: c23, 24: c24, 25: c25}
    scale = np.array([
        3 * v / (4 * np.pi), 4 * v / np.sqrt(32), 3 * v / 8, v / 8, 3 * v / 8,
        3 * v / 4, v / 8, v / 8, 3 * v / 8, 3 * v / (4 * np.pi),
        9 * v / (4 * np.sqrt(50)), v / 8, 3 * v / (4 * np.pi), v / 8, v / 8,
        3 * v / (4 * np.pi), 4 * v / np.sqrt(32), 3 * v / 8, 3 * v / (4 * np.pi),
        3 * v / (4 * np.pi), 3 * v / (4 * np.pi), v / 8, v * 3 / 8, 4 * v / np.sqrt(32),
        3 * v / 4,
    ]) ** (1 / 3)
    # fm: primitive and whether the call carries the radius
    fm = (["lines3d"] * 14 + ["quads3d", "spheres3d", "triangles3d", "triangles3d",
          "spheres3d", "spheres3d"] + ["lines3d"] * 5)
    has_scale = [False] * 15 + [True, False, False, True, True] + [False] * 5
    return table, scale, fm, has_scale


def _rglplot0(x, y, z, v, pch, col, alpha, size=1.0):
    """Records of the rgl calls rglplot0 makes for these points."""
    table, scale, fm, has_scale = _symbol_tables(v)
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    z = np.asarray(z, float)
    pch = np.asarray(pch, float)
    records = []
    for k in sorted(set(pch.tolist())):
        code = int(k)
        coord = table[code]
        s = scale[code - 1]
        idx = np.where(pch == k)[0]
        n_c = len(coord["x"])
        x0 = np.repeat(x[idx], n_c) + np.tile(coord["x"], len(idx)) * s
        y0 = np.repeat(y[idx], n_c) + np.tile(coord["y"], len(idx)) * s
        z0 = np.repeat(z[idx], n_c) + np.tile(coord["z"], len(idx)) * s
        records.append({
            "fn": fm[code - 1], "x": x0, "y": y0, "z": z0,
            "radius": float(s) if has_scale[code - 1] else None,
            "size": size, "col": col, "alpha": alpha,
        })
    return records


def _line(x, y, z, col):
    return {"fn": "lines3d", "x": np.asarray(x, float), "y": np.asarray(y, float),
            "z": np.asarray(z, float), "radius": None, "size": None, "col": col,
            "alpha": None}


def _text(x, y, z, labels, cex, col):
    return {"fn": "texts3d", "x": np.asarray(x, float), "y": np.asarray(y, float),
            "z": np.asarray(z, float), "text": [str(t) for t in labels],
            "cex": cex, "col": col}


def plot3d_ca_data(obj, dim=(1, 2, 3), map="symmetric", what=("all", "all"),
                   contrib=("none", "none"), col=("#6666FF", "#FF6666"),
                   labcol=("#0000FF", "#FF0000"), pch=(16, 1, 18, 9), labels=(2, 2),
                   sf=0.00001, arrows=(False, False), axiscol="#333333",
                   axislcol="#333333", laboffset=None, pin=None, **_):
    """Compute the rgl primitives plot3d.ca would send, without drawing."""
    if any(arrows):
        raise NotImplementedError("plot3d.ca arrows = TRUE is not translated")
    if laboffset is None:
        laboffset = {"x": 0.0, "y": 0.075, "z": 0.05}
    what = rep_len(what, 2)
    contrib = rep_len(contrib, 2)
    col = rep_len(col, 2)
    labels = rep_len(labels, 2)
    pch = rep_len(pch, 4)
    labcol = rep_len(labcol, 2)
    dim = [int(d) for d in dim]

    rowcoord = np.array(obj["rowcoord"], dtype=float)
    colcoord = np.array(obj["colcoord"], dtype=float)
    sv = np.asarray(obj["sv"], dtype=float)
    rowmass = np.asarray(obj["rowmass"], dtype=float)
    colmass = np.asarray(obj["colmass"], dtype=float)
    (xfull, yfull), rpc, cpc = principal_maps(rowcoord, colcoord, sv, rowmass, colmass, map)
    x_names = [str(v) for v in obj["rownames"]]
    y_names = [str(v) for v in obj["colnames"]]
    rowsup = list(obj.get("rowsup") or [])
    colsup = list(obj.get("colsup") or [])
    indx = xfull.shape[0]
    indy = yfull.shape[0]

    xs = select_side(xfull, x_names, rowsup, pch[0], pch[1], what[0])
    ys = select_side(yfull, y_names, colsup, pch[2], pch[3], what[1])
    dcols = [d - 1 for d in dim]
    x = None if xs["coords"] is None else xs["coords"][:, dcols]
    y = None if ys["coords"] is None else ys["coords"][:, dcols]
    cex_x = cex_y = sf

    calpha_x = 1.0
    calpha_y = 1.0
    if contrib[0] == "relative":
        rowinertia = np.asarray(obj["rowinertia"], dtype=float)
        calpha_x = rowmass * (rpc[:, dcols[0]] ** 2 + rpc[:, dcols[1]] ** 2) / rowinertia
    elif contrib[0] == "absolute":
        calpha_x = rowmass * (rpc[:, dcols[0]] ** 2 + rpc[:, dcols[1]] ** 2) / (
            sv[dim[0] - 1] ** 2 + sv[dim[1] - 1] ** 2)
    if contrib[1] == "relative":
        colinertia = np.asarray(obj["colinertia"], dtype=float)
        calpha_y = colmass * (cpc[:, dcols[0]] ** 2 + cpc[:, dcols[1]] ** 2) / colinertia
    elif contrib[1] == "absolute":
        calpha_y = colmass * (cpc[:, dcols[0]] ** 2 + cpc[:, dcols[1]] ** 2) / (
            sv[dim[0] - 1] ** 2 + sv[dim[1] - 1] ** 2)

    ops = [{"fn": "plot3d"}]
    def _range(parts):
        vals = np.concatenate([p for p in parts if p is not None])
        vals = vals[np.isfinite(vals)]
        return float(vals.min()), float(vals.max())

    x001 = _range([None if x is None else x[:, 0], None if y is None else y[:, 0]])
    x002 = _range([None if x is None else x[:, 1], None if y is None else y[:, 1]])
    x003 = _range([None if x is None else x[:, 2], None if y is None else y[:, 2]])
    off = {
        "x": laboffset["x"] * abs(x001[1] - x001[0]),
        "y": laboffset["y"] * abs(x002[1] - x002[0]),
        "z": laboffset["z"] * abs(x003[1] - x003[0]),
    }
    span1 = abs(x001[1] - x001[0])
    ops.append(_line([x001[0], x001[1]], [0, 0], [0, 0], axiscol))
    ops.append(_line([0, 0], [x002[0], x002[1]], [0, 0], axiscol))
    ops.append(_line([0, 0], [0, 0], [x003[0], x003[1]], axiscol))
    ops.append(_text([x001[1] + 0.01 * span1], [0], [0], [dim[0]], 0.75, axislcol))
    ops.append(_text([0], [x002[1] + 0.01 * span1], [0], [dim[1]], 0.75, axislcol))
    ops.append(_text([0], [0], [x003[1] + 0.01 * span1], [dim[2]], 0.75, axislcol))

    if x is not None:
        if labels[0] != 1:
            ops.extend(_rglplot0(x[:, 0], x[:, 1], x[:, 2], cex_x, xs["pch"],
                                 col[0], calpha_x))
        if labels[0] > 0:
            ops.append(_text(x[:, 0] + off["x"], x[:, 1] + off["y"], x[:, 2] + off["z"],
                             xs["names"], 0.95, labcol[0]))
    if y is not None:
        if labels[1] != 1:
            ops.extend(_rglplot0(y[:, 0], y[:, 1], y[:, 2], cex_y, ys["pch"],
                                 col[1], calpha_y))
        if labels[1] > 0:
            ops.append(_text(y[:, 0] + off["x"], y[:, 1] + off["y"], y[:, 2] + off["z"],
                             ys["names"], 0.95, labcol[1]))

    return {"ops": ops, "xlim": x001, "ylim": x002, "zlim": x003}


def plot3d_ca(obj, ax=None, **kwargs):
    """Draw the 3D map with Matplotlib's 3D axes and return the computed data."""
    import matplotlib.pyplot as plt
    from ._plot3d_draw import draw_plot3d_ops

    if ax is None:
        fig = plt.figure()
        ax = fig.add_subplot(projection="3d")
    data = plot3d_ca_data(obj, **kwargs)
    ax.set_xlim(*data["xlim"])
    ax.set_ylim(*data["ylim"])
    ax.set_zlim(*data["zlim"])
    draw_plot3d_ops(ax, data["ops"])
    return data
