"""Sammon's non-linear mapping (MASS sammon)."""

from __future__ import annotations

from typing import Any

import numpy as np

from mass.errors import MassError


def _cmdscale(d: np.ndarray, k: int) -> np.ndarray:
    """Classical scaling with ``k`` dimensions, matching ``stats::cmdscale(d, k)``."""
    n = d.shape[0]
    squared = np.asarray(d, dtype=float) ** 2
    row_mean = squared.mean(axis=1, keepdims=True)
    col_mean = squared.mean(axis=0, keepdims=True)
    grand = squared.mean()
    centered = squared - row_mean - col_mean + grand
    evals, evecs = np.linalg.eigh(-centered / 2.0)
    order = np.argsort(evals)[::-1]
    evals = evals[order]
    evecs = evecs[:, order]
    chosen = evals[:k]
    vectors = evecs[:, :k]
    keep = chosen > 0
    if not np.all(keep):
        chosen = chosen[keep]
        vectors = vectors[:, keep]
    for column in range(vectors.shape[1]):
        entries = np.flatnonzero(np.abs(vectors[:, column]) > 0)
        if entries.size and vectors[entries[0], column] < 0:
            vectors[:, column] *= -1
    if chosen.size < k:
        pad = np.zeros((n, k - chosen.size))
        vectors = np.hstack((vectors * np.sqrt(chosen), pad))
    else:
        vectors = vectors * np.sqrt(chosen)
    return vectors


def _vr_sammon(
    dd: np.ndarray,
    y: np.ndarray,
    niter: int,
    trace: bool,
    magic: float,
    tol: float,
) -> tuple[np.ndarray, float]:
    """Port of ``VR_sammon`` from MASS ``src/MASS.c``."""
    n, nd = y.shape
    y = np.array(y, dtype=float, order="F", copy=True)
    xu = np.zeros((n, nd), order="F")
    xv = np.zeros(nd)
    e1 = np.zeros(nd)
    e2 = np.zeros(nd)

    epast = 1.0
    eprev = 1.0
    e = 0.0
    tot = 0.0
    for j in range(1, n):
        for k in range(j):
            d = dd[k, j]
            if np.isnan(d):
                continue
            tot += d
            d1 = 0.0
            for m in range(nd):
                xd = y[j, m] - y[k, m]
                d1 += xd * xd
            ee = d - np.sqrt(d1)
            if d1 == 0:
                raise MassError("initial configuration has duplicates")
            e += ee * ee / d
    e /= tot
    if trace:
        print(f"Initial stress        : {e:7.5f}")
    epast = eprev = e

    i = 1
    while i <= niter:
        while True:
            for j in range(n):
                e1.fill(0.0)
                e2.fill(0.0)
                for k in range(n):
                    if j == k:
                        continue
                    dt = dd[k, j]
                    if np.isnan(dt):
                        continue
                    d1 = 0.0
                    for m in range(nd):
                        xd = y[j, m] - y[k, m]
                        d1 += xd * xd
                        xv[m] = xd
                    dpj = np.sqrt(d1)
                    dq = dt - dpj
                    dr = dt * dpj
                    for m in range(nd):
                        e1[m] += xv[m] * dq / dr
                        e2[m] += (dq - xv[m] * xv[m] * (1.0 + dq / dpj) / dpj) / dr
                for m in range(nd):
                    xu[j, m] = y[j, m] + magic * e1[m] / abs(e2[m])

            e = 0.0
            for j in range(1, n):
                for k in range(j):
                    d = dd[k, j]
                    if np.isnan(d):
                        continue
                    d1 = 0.0
                    for m in range(nd):
                        xd = xu[j, m] - xu[k, m]
                        d1 += xd * xd
                    ee = d - np.sqrt(d1)
                    e += ee * ee / d
            e /= tot

            if e > eprev:
                e = eprev
                magic *= 0.2
                if magic > 1.0e-3:
                    continue
                if trace:
                    print(f"stress after {i - 1:3d} iters: {e:7.5f}")
                i = niter + 1
            break

        if i > niter:
            break

        magic *= 1.5
        if magic > 0.5:
            magic = 0.5
        eprev = e

        for m in range(nd):
            xx = float(xu[:, m].sum()) / n
            for j in range(n):
                y[j, m] = xu[j, m] - xx

        if i % 10 == 0:
            if trace:
                print(f"stress after {i:3d} iters: {e:7.5f}, magic = {magic:5.3f}")
            if e > epast - tol:
                break
            epast = e
        i += 1

    return y, e


def _dist_matrix(d: Any) -> tuple[np.ndarray, list[str] | None]:
    labels = None
    if isinstance(d, dict) and "Size" in d:
        n = int(d["Size"])
        labels = list(d.get("Labels") or [])
        lower = np.asarray(d["x"], dtype=float).reshape(-1)
        x = np.zeros((n, n))
        idx = np.triu_indices(n, k=1)
        x[idx] = lower
        x = x + x.T
        return x, labels
    x = np.asarray(d, dtype=float)
    if x.ndim != 2 or x.shape[0] != x.shape[1]:
        raise MassError("distances must be result of 'dist' or a square matrix")
    labels = None
    if hasattr(d, "index"):
        labels = [str(item) for item in d.index]
    elif isinstance(d, dict) and "rownames" in d:
        labels = [str(item) for item in d["rownames"]]
    return x, labels


def sammon(
    d,
    y=None,
    k: int = 2,
    niter: int = 100,
    trace: bool = True,
    magic: float = 0.2,
    tol: float = 1e-4,
):
    """Sammon's non-linear mapping."""
    x, rn = _dist_matrix(d)
    if np.any(np.isinf(x)):
        raise MassError("Infs not allowed in 'd'")
    if y is None:
        if np.any(np.isnan(x)):
            raise MassError(
                "an initial configuration must be supplied if there are NAs in 'd'"
            )
        y = _cmdscale(x, k)
    y = np.asarray(y, dtype=float)
    if y.ndim != 2:
        raise MassError("'y' must be a matrix")
    n = x.shape[0]
    if int(n) != n:
        raise MassError("invalid size")
    n = int(n)
    upper = x[np.triu_indices(n, k=1)]
    bad = upper <= 0
    if np.any(bad & ~np.isnan(bad)):
        pairs = np.argwhere(np.triu(np.ones((n, n), dtype=bool), k=1))
        for row, col in pairs:
            if not np.isnan(x[row, col]) and x[row, col] <= 0:
                raise MassError(
                    f"zero or negative distance between objects {row + 1} and {col + 1}"
                )
    nas = np.isnan(x)
    np.fill_diagonal(nas, False)
    if np.any(np.sum(~nas, axis=1) < 2):
        raise MassError("not enough non-missing data")
    if y.shape != (n, k):
        raise MassError("invalid initial configuration")
    if not np.all(np.isfinite(y)):
        raise MassError("initial configuration must be complete")
    points, stress = _vr_sammon(x, y, int(niter), bool(trace), float(magic), float(tol))
    if rn is not None and len(rn) == n:
        rownames = rn
    else:
        rownames = [str(i + 1) for i in range(n)]
    return {"points": points, "stress": float(stress)}
