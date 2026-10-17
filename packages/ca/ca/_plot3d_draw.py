"""Matplotlib drawing for the rgl primitive records that plot3d.ca computes."""

import numpy as np
from mpl_toolkits.mplot3d.art3d import Poly3DCollection


def draw_plot3d_ops(ax, ops):
    """Draw each primitive record on a 3D axes.

    ``lines3d`` becomes a polyline, ``texts3d`` text, ``spheres3d`` markers
    (Matplotlib has no sphere primitive in scatter), and ``triangles3d`` /
    ``quads3d`` polygons with 3 or 4 vertices each. Opacity (alpha) is not drawn.
    """
    for op in ops:
        fn = op["fn"]
        if fn == "plot3d":
            continue
        if fn == "lines3d":
            ax.plot(op["x"], op["y"], op["z"], color=op["col"])
        elif fn == "texts3d":
            for x, y, z, text in zip(op["x"], op["y"], op["z"], op["text"]):
                ax.text(x, y, z, text, color=op["col"], fontsize=9 * op["cex"])
        elif fn == "spheres3d":
            ax.scatter(op["x"], op["y"], op["z"], color=op["col"], s=12)
        elif fn in ("triangles3d", "quads3d"):
            n = 3 if fn == "triangles3d" else 4
            verts = np.column_stack([op["x"], op["y"], op["z"]])
            polys = verts.reshape(-1, n, 3)
            ax.add_collection3d(Poly3DCollection(polys, facecolors=op["col"],
                                                 edgecolors=op["col"], linewidths=0.5))
        else:
            raise ValueError(f"unknown rgl primitive {fn!r}")
