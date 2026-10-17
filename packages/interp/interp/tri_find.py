"""tri.find from R package interp 1.1-6: the triangle that holds each point.

Port of R/tri.find.R and the C++ triFind in interp's shullDeltri.cpp. For each
point the triangles are scanned in order, and the first one whose barycentric
coordinates all lie in [0, 1] is used. A point in no triangle gets 0 for i1,
i2, i3 and tr, and the barycentric values of the last triangle scanned.

Indices i1, i2, i3 are 1-based, as in the triSht object. tr is the 0-based row
of the triangle, as in the C++ loop, so tr is 0 both for triangle 1 and for a
point outside the triangulation; i1 == 0 tells the two apart.
"""

import numpy as np


def _check_tri(tri_obj):
    if not isinstance(tri_obj, dict) or "trlist" not in tri_obj or "nt" not in tri_obj:
        raise ValueError('tri.obj must be of class "triSht"')


def tri_find(tri_obj, x, y):
    """Locate points (x, y) in the triangulation `tri_obj` (a triSht from tri_mesh).

    Returns a dict with i1, i2, i3 (1-based vertex indices, 0 if outside), tr
    (0-based triangle row, 0 if outside), and bc (n x 3 barycentric
    coordinates), as the R list.
    """
    _check_tri(tri_obj)
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if len(x) != len(y):
        raise ValueError("x and y must be of same length")

    n = len(x)
    nt = int(tri_obj["nt"])
    xd = np.asarray(tri_obj["x"], dtype=float)
    yd = np.asarray(tri_obj["y"], dtype=float)
    tl = np.asarray(tri_obj["trlist"], dtype=np.int64).reshape(nt, 9)[:, 0:3]

    i1 = tl[:, 0]
    i2 = tl[:, 1]
    i3 = tl[:, 2]
    if nt == 0:
        zero = np.zeros(n, dtype=np.int64)
        return {"i1": zero, "i2": zero.copy(), "i3": zero.copy(), "tr": zero.copy(),
                "bc": np.zeros((n, 3), dtype=float)}

    # Vertex coordinates per triangle, column vectors for broadcasting.
    x1 = xd[i1 - 1][:, None]
    y1 = yd[i1 - 1][:, None]
    x2 = xd[i2 - 1][:, None]
    y2 = yd[i2 - 1][:, None]
    x3 = xd[i3 - 1][:, None]
    y3 = yd[i3 - 1][:, None]
    den = (y2 - y3) * (x1 - x3) + (x3 - x2) * (y1 - y3)

    found = np.zeros(n, dtype=bool)
    first = np.zeros(n, dtype=np.int64)
    bc = np.empty((n, 3), dtype=float)

    # Chunk the points so the nt x chunk arrays stay small.
    block = max(1, 4_000_000 // nt)
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        for s in range(0, n, block):
            e = min(n, s + block)
            xq = x[s:e][None, :]
            yq = y[s:e][None, :]
            a = ((y2 - y3) * (xq - x3) + (x3 - x2) * (yq - y3)) / den
            b = ((y3 - y1) * (xq - x3) + (x1 - x3) * (yq - y3)) / den
            c = 1 - a - b
            inside = (0 <= a) & (a <= 1) & (0 <= b) & (b <= 1) & (0 <= c) & (c <= 1)
            any_in = inside.any(axis=0)
            hit = np.argmax(inside, axis=0)
            # The C++ loop keeps the last values computed, which are for triangle nt - 1.
            idx = np.where(any_in, hit, nt - 1)
            cols = np.arange(e - s)
            found[s:e] = any_in
            first[s:e] = hit
            bc[s:e, 0] = a[idx, cols]
            bc[s:e, 1] = b[idx, cols]
            bc[s:e, 2] = c[idx, cols]

    zero = np.zeros(n, dtype=np.int64)
    return {
        "i1": np.where(found, i1[first], zero),
        "i2": np.where(found, i2[first], zero),
        "i3": np.where(found, i3[first], zero),
        "tr": np.where(found, first, zero),
        "bc": bc,
    }
