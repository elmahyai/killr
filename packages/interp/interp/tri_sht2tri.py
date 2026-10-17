"""triSht2tri from R package interp 1.1-6: triSht to tripack-style adjacency.

Port of R/triSht2tri.R. The R code is kept step for step, including the
pairing of the directed edges and the R colon rule for `1:(length(l) - 1)`.
Indices are 1-based as in R. `on_convex_hull` and `left` are the interp
functions it calls.
"""

from collections import Counter

import numpy as np

from interp.on_convex_hull import on_convex_hull


def _left(x1, y1, x2, y2, x0, y0, eps=1e-16):
    """interp::left for one point, the sign test of the R code."""
    return ((x2 - x1) * (y0 - y1) - (x0 - x1) * (y2 - y1)) >= eps


def _minrot(v):
    """Rotate the three entries so the minimum comes first (0-based positions)."""
    m = int(np.argmin(v))
    return [(m + k) % 3 for k in range(3)]


def _minsort(trlist):
    """minsort(): three cyclic rotations of every triangle, one row each."""
    rows = []
    for t in trlist:
        cur = _minrot(t[0:3])
        for _ in range(3):
            cols = list(cur) + [c + 3 for c in cur] + [c + 6 for c in cur]
            rows.append([t[c] for c in cols])
            cur = [cur[1], cur[2], cur[0]]
    return rows


def _r_colon_1_to(m):
    """R's 1:m. For m = 0 this is c(1, 0)."""
    if m >= 1:
        return list(range(1, m + 1))
    return list(range(1, m - 1, -1))


def _adjacency_for(node, ms):
    """The adjacency list msl[[node]] for one node (1-based node id)."""
    tmp = [[row[1], row[2]] for row in ms if row[0] == node]
    if not tmp:
        raise ValueError(f"triSht2tri: node {node} is in no triangle")
    if len(tmp) == 1:
        # R: is.vector(tmp), so the single pair is c(tmp)
        return list(tmp[0])

    counts = Counter(v for pair in tmp for v in pair)
    if not any(c == 1 for c in counts.values()):
        tmp = tmp[1:]  # interior node: the chain is closed, drop the first row

    lst = list(tmp[0])
    tmp = tmp[1:]
    while len(tmp) > 0:
        lft = [k for k, pair in enumerate(tmp) if pair[1] == lst[0]]
        if len(lft) == 1:
            k = lft[0]
            lst = [tmp[k][0]] + lst
            del tmp[k]
        rgt = [k for k, pair in enumerate(tmp) if pair[0] == lst[-1]]
        if len(rgt) == 1:
            k = rgt[0]
            lst = lst + [tmp[k][1]]
            del tmp[k]
        if len(lft) != 1 and len(rgt) != 1:
            raise RuntimeError("triSht2tri: adjacency chain does not close")
    return lst


def tri_sht2tri(t_tri_sht):
    """Convert a triSht (from tri_mesh) to the tri object of R's triSht2tri.

    Returns a dict with n, x, y, tlist, tlptr, tlend, tlnew, nc, lc, call,
    and adjlist. Lists are 1-based and the hull entries of tlist are negative.
    """
    trlist = np.asarray(t_tri_sht["trlist"], dtype=np.int64)
    ms = _minsort(trlist.tolist())
    nd = int(t_tri_sht["n"])
    x = np.asarray(t_tri_sht["x"], dtype=float)
    y = np.asarray(t_tri_sht["y"], dtype=float)

    msl = []
    for i in range(1, nd + 1):
        lst = _adjacency_for(i, ms)
        # counter-clockwise check, otherwise reverse the list
        a = lst[0]
        b = lst[1]
        if not _left(x[i - 1], y[i - 1], x[a - 1], y[a - 1], x[b - 1], y[b - 1]):
            lst = lst[::-1]
        msl.append(lst)

    tlist = []
    tlptr = []
    tlend = []
    for l in msl:
        last = len(tlist)
        tlist.extend(l)
        tlend.append(len(tlist))
        tlptr.append(last + len(l))
        tlptr.extend(last + k for k in _r_colon_1_to(len(l) - 1))

    end_ids = np.asarray([tlist[e - 1] for e in tlend], dtype=np.int64)
    ch = on_convex_hull(t_tri_sht, x[end_ids - 1], y[end_ids - 1])
    for pos, flag in zip(tlend, ch):
        if flag:
            tlist[pos - 1] = -tlist[pos - 1]

    return dict(
        n=nd,
        x=x,
        y=y,
        tlist=np.asarray(tlist, dtype=np.int64),
        tlptr=np.asarray(tlptr, dtype=np.int64),
        tlend=np.asarray(tlend, dtype=np.int64),
        tlnew=tlend[-1] + 1,
        nc=0,
        lc=0,
        call="converted from interp",
        adjlist=[np.asarray(l, dtype=np.int64) for l in msl],
    )
