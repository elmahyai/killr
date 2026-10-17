"""on.convex.hull from R package interp 1.1-6: points on the convex hull edges.

Port of R/on.convex.hull.R and the C++ onHull in interp's shullDeltri.cpp: a
point is on the hull when, for some hull edge, |cross| < eps. Indices of the
hull are 1-based, as stored in the triSht object.
"""

import numpy as np


def on_convex_hull(tri_obj, x, y, eps=1e-16):
    """Logical vector: is each point (x, y) on an edge of the convex hull?

    `tri_obj` is a triSht from tri_mesh, with `x`, `y`, `nchull`, and `chull`.
    """
    if not isinstance(tri_obj, dict) or "chull" not in tri_obj or "nchull" not in tri_obj:
        raise ValueError('tri.obj must be of class "triSht"')
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if len(x) != len(y):
        raise ValueError("x and y must be of same length")
    if len(x) == 0:
        raise ValueError("length of x (resp. y) is 0")

    xd = np.asarray(tri_obj["x"], dtype=float)
    yd = np.asarray(tri_obj["y"], dtype=float)
    ch = np.asarray(tri_obj["chull"], dtype=np.int64)
    n_ch = int(tri_obj["nchull"])

    if n_ch == 0:
        return np.zeros(len(x), dtype=bool)
    # Hull edges: (ch[j], ch[j + 1]) and the closing edge (ch[last], ch[0]).
    a = ch[:n_ch] - 1
    b = np.append(ch[1:n_ch], ch[0]) - 1
    x1 = xd[a][:, None]
    y1 = yd[a][:, None]
    x2 = xd[b][:, None]
    y2 = yd[b][:, None]
    cross = (x2 - x1) * (y[None, :] - y1) - (x[None, :] - x1) * (y2 - y1)
    return np.any(np.abs(cross) < eps, axis=0)
