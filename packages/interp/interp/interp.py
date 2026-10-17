"""interp from R package interp 1.1-6: linear interpolation over a triangulation.

Port of R/interp.R on the default path: method = "linear" (or "akima" with
linear = TRUE), deltri = "shull", input = "points" or "grid", output = "grid"
or "points", and duplicate = "error", "strip", "mean", "median" or "user".
The triangulation is the s-hull sweep in crates/interp (interp_kernels). The
linear evaluation is the interpShull loop of interp.cpp, with the same
bounding-box rule and the same last-triangle-wins rule on shared edges.

Not translated:
- linear = FALSE with method = "akima" (the cubic path of interp.cpp, which
  needs the local polynomial fit pD and the neighbour search nN);
- method = "bilinear" (R/bilinear.R, a separate C++ routine);
- deltri = "deldir" (needs the R package deldir, which is not in registry.json);
- sp data frames, and the h, kernel, solver, degree, baryweight, autodegree,
  adtol, smoothpde, akimaweight, nweight, and na.rm arguments of the cubic path.

extrap is accepted and ignored: interp 1.1-6 does not read it on any path.

Output grid is a matrix of shape (len(xo), len(yo)), as R's matrix(z, nx, ny).
Points outside the triangulation are NaN, as NA in R.
"""

import numpy as np
from interp_kernels import shull_deltri

from interp.tri_mesh import _jitter, _key, _match


def _any_duplicate_rows(x, y):
    # anyDuplicated(cbind(x, y), MARGIN = 1): exact equality of the two numbers.
    return len(set(zip(x.tolist(), y.tolist()))) < len(x)


def _triangulate_points(x, y, rng):
    """Sweep triangulation of the data. On a status-1 result, jitter both coordinates once."""
    ans = shull_deltri(x.tolist(), y.tolist())
    if ans["status"] == 1:
        if rng is None:
            rng = np.random.default_rng()
        x = _jitter(x, rng, 1e-3)
        y = _jitter(y, rng, 1e-3)
        ans = shull_deltri(x.tolist(), y.tolist())
        if ans["status"] == 1:
            raise RuntimeError("triangulation failed, try rescaling your data.")
    return x, y, ans


def _barycentric(xT, yT, zT, X, Y):
    """interp.cpp's barycentric test and linear value for points (X, Y).

    xT, yT, zT hold the three vertices of each triangle on the last axis, in
    the order (i1, i2, i3). Returns (inside, value), broadcast over the other axes.
    """
    x0, x1, x2 = xT[..., 0], xT[..., 1], xT[..., 2]
    y0, y1, y2 = yT[..., 0], yT[..., 1], yT[..., 2]
    den = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
    a = ((y1 - y2) * (X - x2) + (x2 - x1) * (Y - y2)) / den
    b = ((y2 - y0) * (X - x2) + (x0 - x2) * (Y - y2)) / den
    c = 1 - a - b
    inside = (0 <= a) & (a <= 1) & (0 <= b) & (b <= 1) & (0 <= c) & (c <= 1)
    val = a * zT[..., 0] + b * zT[..., 1] + c * zT[..., 2]
    return inside, val


def _last_below(v, t):
    """C++ `for j: if (v[j] < t) out = j`: the largest such j, or 0."""
    m = v[None, :] < t[:, None]
    idx = len(v) - 1 - np.argmax(m[:, ::-1], axis=1)
    return np.where(m.any(axis=1), idx, 0)


def _first_above(v, t, default):
    """C++ `for j: if (v[n-j-1] > t) out = n-j-1`: the smallest such index, or default."""
    m = v[None, :] > t[:, None]
    return np.where(m.any(axis=1), np.argmax(m, axis=1), default)


def interp(
    x,
    y=None,
    z=None,
    xo=None,
    yo=None,
    linear=None,
    extrap=False,
    duplicate="error",
    dupfun=None,
    nx=40,
    ny=40,
    input="points",
    output="grid",
    method="linear",
    deltri="shull",
    rng=None,
):
    """Interpolate z at the grid xo x yo (or at the points xo, yo) over the triangulation of (x, y).

    Returns a dict with x, y and z, as the R list. `rng` is a numpy Generator
    for the jitter retry, used only when the sweep fails on the data.
    """
    # R: linear = (method == "linear"), and method "linear" forces linear = TRUE.
    if linear is None:
        linear = method == "linear"
    if method == "linear":
        linear = True
    if y is None:
        raise ValueError("y is missing: sp data frames are not translated")
    if z is None:
        raise ValueError('argument "z" is missing, with no default')

    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    z_in = np.asarray(z, dtype=float)
    if not (np.all(np.isfinite(x)) and np.all(np.isfinite(y)) and np.all(np.isfinite(z_in))):
        raise ValueError("missing values and Infs not allowed")

    drx = float(np.max(x) - np.min(x))
    dry = float(np.max(y) - np.min(y))
    if drx == 0 or dry == 0:
        raise ValueError("all data collinear")
    if drx / dry > 10000 or drx / dry < 0.0001:
        raise ValueError("scales of x and y are too dissimilar")

    n = len(x)
    # The default xo and yo are seq(min, max, length = nx) on the data as given.
    if xo is None:
        xo = np.linspace(np.min(x), np.max(x), nx)
    if yo is None:
        yo = np.linspace(np.min(y), np.max(y), ny)
    xo = np.asarray(xo, dtype=float).ravel()
    yo = np.asarray(yo, dtype=float).ravel()

    z_vec = z_in.ravel(order="F")
    if input == "points":
        if len(y) != n or len(z_vec) != n:
            raise ValueError("Lengths of x, y, and z do not match")
        if _any_duplicate_rows(x, y):
            if duplicate == "error":
                raise ValueError("duplicate data points: need to set 'duplicate = ..' ")
            if duplicate not in ("strip", "mean", "median", "user"):
                raise ValueError(f'duplicate = "{duplicate}" is not one of "strip", "mean", "median", "user"')
            if duplicate == "user" and not callable(dupfun):
                raise ValueError("dupfun must be a function when duplicate = \"user\"")
            keys = [_key(a, b) for a, b in zip(x.tolist(), y.tolist())]
            i = _match(keys)  # 1-based index of the first occurrence
            ord_ = i == np.arange(1, n + 1)
            if duplicate != "strip":
                # One value per distinct point, in order of first occurrence.
                gid = (np.cumsum(ord_) - 1)[i - 1]
                ngroups = int(ord_.sum())
                counts = np.bincount(gid, minlength=ngroups)
                o = np.argsort(gid, kind="stable")
                parts = np.split(z_vec[o], np.cumsum(counts)[:-1])
                centre = {"mean": np.mean, "median": np.median, "user": dupfun}[duplicate]
                z_vec = np.array([float(centre(p)) for p in parts])
            else:
                z_vec = z_vec[ord_]
            x = x[ord_]
            y = y[ord_]
            n = len(x)
    else:
        # input == "grid": x and y are the grid axes, z is the matrix nx x ny.
        nxi = len(x)
        nyi = len(y)
        x = np.tile(x, nyi)
        y = np.repeat(y, nxi)

    if method == "bilinear":
        raise NotImplementedError('method = "bilinear" (R/bilinear.R) is not translated')
    if method not in ("linear", "akima"):
        raise ValueError(f'method="{method}" not implemented!')
    if not linear:
        raise NotImplementedError(
            'linear = FALSE (the cubic path of interp.cpp) is not translated'
        )
    if deltri == "deldir":
        raise NotImplementedError(
            'deltri = "deldir" needs the R package deldir, which is not in registry.json'
        )
    if deltri != "shull":
        raise ValueError(f"unknown triangulation method {deltri}")

    xd, yd, tri = _triangulate_points(x, y, rng)
    nt = int(tri["nt"])
    trl = np.asarray(tri["trlist"], dtype=np.int64).reshape(nt, 9)[:, 0:3] - 1
    xT = xd[trl]
    yT = yd[trl]
    zT = z_vec[trl]

    nG = len(xo)
    mG = len(yo)
    if output not in ("grid", "points"):
        raise ValueError("invalid output specification!")

    if output == "grid":
        N = nG * mG
        zout = np.full(N, np.nan)
        # Bounding boxes of the triangles, in grid indices (interp.cpp part 0).
        jsw = _last_below(xo, xT.min(axis=1))
        jne = _first_above(xo, xT.max(axis=1), nG - 1)
        ksw = _last_below(yo, yT.min(axis=1))
        kne = _first_above(yo, yT.max(axis=1), mG - 1)
        cj = np.maximum(jne - jsw + 1, 0)
        ck = np.maximum(kne - ksw + 1, 0)
        cnt = cj * ck
        total = int(cnt.sum())
        if total:
            # Candidate (triangle, grid cell) pairs, in triangle order, cells inside each box.
            tri = np.repeat(np.arange(nt), cnt)
            starts = np.cumsum(cnt) - cnt
            m = np.arange(total) - np.repeat(starts, cnt)
            ckt = ck[tri]
            j = jsw[tri] + m // ckt
            k = ksw[tri] + m % ckt
            with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
                inside, val = _barycentric(xT[tri], yT[tri], zT[tri], xo[j], yo[k])
            p = j * mG + k
            p_in = p[inside]
            # Later triangles overwrite earlier ones: keep the last candidate per cell.
            up, first_rev = np.unique(p_in[::-1], return_index=True)
            zout[up] = val[inside][::-1][first_rev]
        return {"x": xo, "y": yo, "z": zout.reshape(nG, mG)}

    # output == "points": every triangle is tested against every point, no box.
    N = nG
    zout = np.full(N, np.nan)
    cols = np.arange(N)
    block = max(1, 4_000_000 // max(N, 1))
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        for s in range(0, nt, block):
            e = min(nt, s + block)
            inside, val = _barycentric(
                xT[s:e, None, :], yT[s:e, None, :], zT[s:e, None, :], xo[None, :], yo[None, :]
            )
            any_in = inside.any(axis=0)
            # Later triangles overwrite earlier ones, so take the last that holds the point.
            last = (e - s - 1) - np.argmax(inside[::-1], axis=0)
            zout = np.where(any_in, val[last, cols], zout)
    return {"x": xo, "y": yo, "z": zout}
