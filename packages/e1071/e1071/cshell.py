"""Fuzzy c-shell clustering (e1071 ``cshell``)."""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np

_DIST = ("euclidean", "manhattan")
_METHOD = ("cshell",)
_SQRT_EPS = math.sqrt(float(np.finfo(float).eps))
_STEPREDN = 0.2
_ACCTOL = 0.0001
_RELTEST = 10.0


def _cshell_ext():
    try:
        from cshell import cshell_kernel as impl
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "crates" / "cshell"))
        from cshell import cshell_kernel as impl
    return impl


def _boot_rng():
    try:
        from boot.rng import sample_int, set_seed, unif
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import sample_int, set_seed, unif
    return sample_int, set_seed, unif


def _pmatch(value, choices):
    if value is None:
        return None
    text = str(value)
    hits = [index for index, choice in enumerate(choices) if choice.startswith(text)]
    if not hits:
        return None
    if len(hits) > 1:
        return -1
    return hits[0] + 1


def _as_matrix(x):
    array = np.asarray(x, dtype=float)
    if array.ndim == 1:
        array = array.reshape(-1, 1)
    elif array.ndim != 2:
        raise ValueError("Argument 'x' must be coercible to a matrix")
    return np.asfortranarray(array)


def _rank_average(values):
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=float)
    ranks[order] = np.arange(1, len(values) + 1, dtype=float)
    return ranks


def _system_objective(spar, x, membership, m, cluster_index):
    """Scalar objective from R ``cshell`` ``system`` for ``optim(..., method='CG')``."""
    nparam = spar.shape[0]
    center = spar[: nparam - 1]
    radius = float(spar[nparam - 1])
    distmat = x - center
    normdist = np.sqrt(np.sum(distmat * distmat, axis=1))
    u_col = membership[:, cluster_index] ** m
    op = float(np.sum(u_col * (normdist - radius)) ** 2)
    equation = (u_col * (1.0 - radius / normdist))[:, None] * distmat
    op += float(np.sum(np.sum(equation, axis=0) ** 2))
    return op


def _optim_cg(
    par,
    fn,
    *,
    maxit=100,
    reltol=_SQRT_EPS,
    abstol=0.0,
    ndeps=0.001,
    type_=1,
):
    """``stats::optim(..., method='CG')`` with default controls and numerical gradients."""
    bvec = [float(v) for v in np.asarray(par, dtype=float).reshape(-1)]
    n = len(bvec)

    def fminfn(p):
        return float(fn(np.asarray(p, dtype=float)))

    def fmingr(p, df):
        work = p[:]
        for i in range(n):
            eps = float(ndeps)
            saved = work[i]
            work[i] = saved + eps
            val1 = fminfn(work)
            work[i] = saved - eps
            val2 = fminfn(work)
            df[i] = (val1 - val2) / (2.0 * eps)
            work[i] = saved

    x = [0.0] * n
    c = [0.0] * n
    g = [0.0] * n
    t = [0.0] * n
    setstep = 1.7
    cyclimit = n
    tol = reltol * n * math.sqrt(reltol)
    fmin = fminfn(bvec)
    if not math.isfinite(fmin):
        raise ValueError("function cannot be evaluated at initial parameters")

    def rel_same(a, b):
        return (_RELTEST + a) == (_RELTEST + b)

    gradcount = 0
    g1 = tol + 1.0
    count = 0
    cycle = 0
    while True:
        for i in range(n):
            t[i] = 0.0
            c[i] = 0.0
        cycle = 0
        oldstep = 1.0
        count = 0
        while True:
            cycle += 1
            gradcount += 1
            if gradcount > maxit:
                return np.asarray(x, dtype=float)
            fmingr(bvec, g)
            g1 = 0.0
            g2 = 0.0
            for i in range(n):
                x[i] = bvec[i]
                if type_ == 1:
                    g1 += g[i] * g[i]
                    g2 += c[i] * c[i]
                elif type_ == 2:
                    g1 += g[i] * (g[i] - c[i])
                    g2 += c[i] * c[i]
                else:
                    g1 += g[i] * (g[i] - c[i])
                    g2 += t[i] * (g[i] - c[i])
                c[i] = g[i]
            if g1 > tol:
                g3 = g1 / g2 if g2 > 0.0 else 1.0
                gradproj = 0.0
                for i in range(n):
                    t[i] = t[i] * g3 - g[i]
                    gradproj += t[i] * g[i]
                steplength = oldstep
                accpoint = False
                f = fmin
                while not (count == n or accpoint):
                    count = 0
                    for i in range(n):
                        bvec[i] = x[i] + steplength * t[i]
                        if rel_same(x[i], bvec[i]):
                            count += 1
                    if count < n:
                        f = fminfn(bvec)
                        accpoint = math.isfinite(f) and f <= fmin + gradproj * steplength * _ACCTOL
                        if not accpoint:
                            steplength *= _STEPREDN
                        else:
                            fmin = f
                if count < n:
                    newstep = 2.0 * (f - fmin - gradproj * steplength)
                    if newstep > 0.0:
                        newstep = -(gradproj * steplength * steplength / newstep)
                        for i in range(n):
                            bvec[i] = x[i] + newstep * t[i]
                        fmin_before = fmin
                        fmin = f
                        f_try = fminfn(bvec)
                        if f_try < fmin:
                            fmin = f_try
                        else:
                            for i in range(n):
                                bvec[i] = x[i] + steplength * t[i]
                            fmin = fmin_before
                oldstep = setstep * steplength
                if oldstep > 1.0:
                    oldstep = 1.0
            if not ((count != n) and (g1 > tol) and (cycle != cyclimit)):
                break
        if not ((cycle != 1) or ((count != n) and (g1 > tol) and fmin > abstol)):
            break
    return np.asarray(x, dtype=float)


def cshell(
    x,
    centers,
    iter_max=100,
    verbose=False,
    dist="euclidean",
    method="cshell",
    m=2,
    radius=None,
):
    """Run fuzzy c-shell clustering on a data matrix."""
    del verbose
    matrix = _as_matrix(x)
    xrows, xcols = matrix.shape

    dist_code = _pmatch(dist, _DIST)
    if dist_code is None:
        raise ValueError("invalid distance")
    if dist_code == -1:
        raise ValueError("ambiguous distance")

    method_code = _pmatch(method, _METHOD)
    if method_code is None:
        raise ValueError("invalid clustering method")
    if method_code == -1:
        raise ValueError("ambiguous clustering method")
    del method_code

    sample_int, _, unif = _boot_rng()

    if centers is None:
        raise ValueError("Argument 'centers' must be a number or a matrix.")

    if np.isscalar(centers) or (isinstance(centers, (list, tuple)) and len(centers) == 1):
        ncenters = int(np.asarray(centers).reshape(-1)[0])
        runif_vals = np.array([unif() for _ in range(xrows)], dtype=float)
        rank_vals = _rank_average(runif_vals)
        picks = rank_vals[:ncenters].astype(int) - 1
        center_matrix = matrix[picks, :] + 0.001
    else:
        center_matrix = _as_matrix(centers)
        ncenters = center_matrix.shape[0]

    if xcols != center_matrix.shape[1]:
        raise ValueError("Must have same number of columns in 'x' and 'centers'.")

    if radius is None:
        radius_vec = np.full(ncenters, 0.2, dtype=float)
    else:
        radius_vec = np.asarray(radius, dtype=float).reshape(-1)
        if radius_vec.shape[0] != ncenters:
            raise ValueError("length of 'radius' must equal number of centers")

    perm = np.asarray(sample_int(xrows), dtype=int) - 1
    matrix = matrix[perm, :]

    kernel = _cshell_ext()
    x_flat = matrix.reshape(-1, order="F")
    centers_flat = np.asfortranarray(center_matrix.copy()).reshape(-1, order="F")
    u = np.zeros(xrows * ncenters, dtype=float)
    uant = np.zeros_like(u)
    flag = 0
    iter_count = 0

    (
        centers_flat,
        radius_vec,
        u,
        uant,
        withinerror,
        iter_count,
        flag,
    ) = kernel(
        x_flat,
        centers_flat,
        radius_vec,
        u,
        uant,
        xrows,
        xcols,
        ncenters,
        m=float(m),
        dist=dist_code - 1,
        iter_max=int(iter_max),
        iter=int(iter_count),
        verbose=0,
        flag=int(flag),
    )

    membership = np.asarray(u, dtype=float).reshape(xrows, ncenters, order="F")

    while (flag == 1 or flag == 4) and iter_count <= iter_max:
        flag = 3
        center_matrix = np.asarray(centers_flat, dtype=float).reshape(ncenters, xcols, order="F")
        for i in range(ncenters):
            spar = np.concatenate([center_matrix[i, :], [radius_vec[i]]])
            par = _optim_cg(
                spar,
                lambda p: _system_objective(p, matrix, membership, float(m), i),
            )
            center_matrix[i, :] = par[:-1]
            radius_vec[i] = par[-1]

        centers_flat = np.asfortranarray(center_matrix.copy()).reshape(-1, order="F")
        (
            centers_flat,
            radius_vec,
            u,
            uant,
            withinerror,
            iter_count,
            flag,
        ) = kernel(
            x_flat,
            centers_flat,
            radius_vec,
            u,
            uant,
            xrows,
            xcols,
            ncenters,
            m=float(m),
            dist=dist_code - 1,
            iter_max=int(iter_max),
            iter=int(iter_count - 1),
            verbose=0,
            flag=int(flag),
        )
        if flag != 2:
            flag = 1
        membership = np.asarray(u, dtype=float).reshape(xrows, ncenters, order="F")

    centers_final = np.asarray(centers_flat, dtype=float).reshape(ncenters, xcols, order="F")
    membership = np.asarray(u, dtype=float).reshape(xrows, ncenters, order="F")

    inv_perm = np.empty_like(perm)
    inv_perm[perm] = np.arange(xrows)
    membership = membership[inv_perm, :]

    cluster = np.argmax(membership, axis=1) + 1
    size = np.bincount(cluster - 1, minlength=ncenters).astype(int)

    return {
        "centers": centers_final,
        "radius": np.asarray(radius_vec, dtype=float),
        "size": size,
        "cluster": cluster,
        "iter": int(iter_count) - 1,
        "membership": membership,
        "withinerror": float(withinerror),
    }
