"""tri.mesh from R package interp 1.1-6: Delaunay triangulation.

interp's tri.mesh is the s-hull sweep of David Sinclair, not tripack. The sweep
is C++ in crates/interp (vendor/s_hull_pro.cpp, unchanged), and interp_kernels
exposes it. This module is the R wrapper: duplicate handling, the jitter retry,
and the triSht object.

The jitter retry draws from NumPy, not R's Mersenne Twister, so a retried
triangulation is a valid one but not the same draw as R's.
"""

import numpy as np

from interp_kernels import shull_deltri

TRLIST_COLNAMES = ("i1", "i2", "i3", "j1", "j2", "j3", "k1", "k2", "k3")
CCLIST_COLNAMES = ("x", "y", "r", "area", "ratio")
ARCS_COLNAMES = ("from", "to")


class TriSht(dict):
    """The R class triSht: a dict with the R list names.

    Indices are 1-based, as in R. `trlist` is nt x 9, `cclist` is nt x 5,
    `arcs` is narcs x 2, `chull` is the hull vertices in order.
    """


def _key(a, b):
    # paste(x1, y1, sep = ",") uses 15 significant digits; -0 prints as 0.
    return f"{a + 0.0:.15g},{b + 0.0:.15g}"


def _match(keys):
    # match(xy, xy): index of the first occurrence, 1-based.
    first = {}
    out = np.empty(len(keys), dtype=np.int64)
    for j, k in enumerate(keys):
        out[j] = first.setdefault(k, j + 1)
    return out


def _jitter(x, rng, factor=1e-3):
    """base::jitter(x, factor) with amount = NULL."""
    x = np.asarray(x, dtype=float)
    if x.size == 0:
        return x
    lo, hi = float(np.min(x)), float(np.max(x))
    z = hi - lo
    if z == 0:
        z = abs(lo)
    if z == 0:
        z = 1.0
    xx = np.unique(np.sort(np.round(x, int(3 - np.floor(np.log10(z))))))
    d_all = np.diff(xx)
    if d_all.size:
        d = float(np.min(d_all))
    elif xx[0] != 0:
        d = float(xx[0]) / 10
    else:
        d = z / 10
    amount = factor / 5 * abs(d)
    return x + rng.uniform(-amount, amount, size=x.size)


def _triangulate(x1, y1, rng):
    ans = shull_deltri(x1.tolist(), y1.tolist())
    if ans["status"] == 1:
        # interp retries once with jitter (nt == -13 or -14), then keeps the
        # unjittered points for the output.
        ans = shull_deltri(_jitter(x1, rng).tolist(), _jitter(y1, rng).tolist())
        if ans["status"] == 1:
            raise RuntimeError("triangulation failed, try rescling your data")
    return ans


def tri_mesh(x, y=None, duplicate="error", jitter=False, rng=None):
    """Delaunay triangulation of the points (x, y), as R's tri.mesh.

    `x` may be a dict with `x` and `y` entries when `y` is None.
    `duplicate` is "error", "remove" (keep the first of each point) or
    "strip" (drop every duplicated point). `jitter` is unused, as in R.
    `rng` is a numpy Generator for the retry jitter.
    """
    if x is None:
        raise ValueError("argument x missing.")
    if y is None:
        if not isinstance(x, dict) or x.get("x") is None or x.get("y") is None:
            raise ValueError("argument y missing and x contains no $x or $y component.")
        x1 = np.asarray(x["x"], dtype=float)
        y1 = np.asarray(x["y"], dtype=float)
    else:
        x1 = np.asarray(x, dtype=float)
        y1 = np.asarray(y, dtype=float)

    n = len(x1)
    if len(y1) != n:
        raise ValueError("length of x and y differ.")

    keys = [_key(a, b) for a, b in zip(x1.tolist(), y1.tolist())]
    i = _match(keys)
    if duplicate != "error":
        if duplicate not in ("remove", "strip"):
            raise ValueError('possible values for \'duplicate\' are "error", "strip" and "remove"')
        if duplicate == "remove":
            dup = i != np.arange(1, n + 1)
            ord_ = ~dup
        else:
            # hist(i, breaks = seq(0.5, max(i) + 0.5, 1))$counts == 1 has length max(i).
            counts = np.bincount(i, minlength=int(i.max()) + 1)[1:]
            ord_ = counts == 1
            # R recycles a short logical subscript to length(x1).
            if len(ord_) < n:
                ord_ = ord_[np.arange(n) % len(ord_)]
        x1 = x1[ord_]
        y1 = y1[ord_]
        n = len(x1)
    else:
        if np.any(i != np.arange(1, n + 1)):
            raise ValueError("duplicate data points")

    if rng is None:
        rng = np.random.default_rng()
    ans = _triangulate(x1, y1, rng)

    nt = ans["nt"]
    nch = ans["nch"]
    na = ans["na"]
    trlist = np.asarray(ans["trlist"], dtype=np.int64).reshape(nt, 9)
    cclist = np.asarray(ans["cclist"], dtype=float).reshape(nt, 5)
    chull = np.asarray(ans["ch"], dtype=np.int64)
    a1 = np.asarray(ans["a1"], dtype=np.int64)
    a2 = np.asarray(ans["a2"], dtype=np.int64)

    return TriSht(
        n=n,
        x=x1,
        y=y1,
        nt=nt,
        trlist=trlist,
        cclist=cclist,
        nchull=nch,
        chull=chull,
        narcs=na,
        arcs=np.column_stack([a1, a2]) if na else np.zeros((0, 2), dtype=np.int64),
    )
