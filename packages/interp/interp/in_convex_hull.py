"""in.convex.hull from R package interp 1.1-6: is each point inside the hull?

Port of R/in.convex.hull.R with the C++ inHull and onHull of interp's
shullDeltri.cpp. A point is inside when, for every hull edge, the cross
product is at least eps (the `left` test). With strict = FALSE, a point on a
hull edge (|cross| < eps for some edge) also counts as inside.

Hull vertices are the 1-based `chull` of the triSht object.
"""

import numpy as np

from interp.on_convex_hull import on_convex_hull


def in_convex_hull(tri_obj, x, y, eps=1e-16, strict=True):
    """Logical vector: is each point (x, y) inside the convex hull of `tri_obj`?"""
    if not isinstance(tri_obj, dict) or "chull" not in tri_obj or "nchull" not in tri_obj:
        raise ValueError('tri.obj must be of class "triSht"')
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if len(x) != len(y):
        raise ValueError("x and y must be of same length")
    if len(x) == 0:
        raise ValueError("length of x (resp. y) is 0")

    n_ch = int(tri_obj["nchull"])
    xd = np.asarray(tri_obj["x"], dtype=float)
    yd = np.asarray(tri_obj["y"], dtype=float)
    ch = np.asarray(tri_obj["chull"], dtype=np.int64)

    inside = np.ones(len(x), dtype=bool)
    if n_ch > 0:
        # Edges (ch[j], ch[j + 1]) and the closing edge (ch[last], ch[0]).
        a = ch[:n_ch] - 1
        b = np.append(ch[1:n_ch], ch[0]) - 1
        x1 = xd[a][:, None]
        y1 = yd[a][:, None]
        x2 = xd[b][:, None]
        y2 = yd[b][:, None]
        cross = (x2 - x1) * (y[None, :] - y1) - (x[None, :] - x1) * (y2 - y1)
        inside = np.all(cross >= eps, axis=0)

    if not strict:
        inside = inside | on_convex_hull(tri_obj, x, y, eps)
    return inside
