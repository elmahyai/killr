"""convex.hull from R package interp 1.1-6: the hull polygon of a triangulation.

Port of R/convex.hull.R with plot.it = FALSE. The polygon is the points
x[chull], y[chull] in the order stored in the triSht object, and `i` is the
1-based index of each vertex, as in R. The drawing branch (plot.it = TRUE) is
not translated; it calls R's graphics device through plot.new and lines.
"""

import numpy as np


def convex_hull(tri_obj):
    """Hull polygon of the triSht `tri_obj`: a dict with x, y and the 1-based index i."""
    if not isinstance(tri_obj, dict) or "chull" not in tri_obj or "x" not in tri_obj:
        raise ValueError('tri.obj must be of class "triSht"')
    ch = np.asarray(tri_obj["chull"], dtype=np.int64)
    xd = np.asarray(tri_obj["x"], dtype=float)
    yd = np.asarray(tri_obj["y"], dtype=float)
    return {"x": xd[ch - 1], "y": yd[ch - 1], "i": ch}
