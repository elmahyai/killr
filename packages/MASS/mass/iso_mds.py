"""Kruskal non-metric MDS (MASS isoMDS)."""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from mass.errors import MassError
from mass.fitdistr import _vmmin

_ABSTOL = 1.0e-2
_REPORT = 5


class MassDist:
    """Condensed distances like R ``dist`` with ``Size`` and ``Labels``."""

    __slots__ = ("data", "_mass_dist_size", "_mass_dist_labels")

    def __init__(self, data: np.ndarray, labels: list[str] | None = None):
        self.data = np.asarray(data, dtype=float).reshape(-1)
        n = int(round((1 + math.sqrt(1 + 8 * self.data.size)) / 2))
        self._mass_dist_size = n
        self._mass_dist_labels = labels if labels is not None else [str(i + 1) for i in range(n)]

    def __array__(self, dtype=None, copy=None):
        return np.asarray(self.data, dtype=dtype, copy=copy)

    def __len__(self) -> int:
        return self.data.size


class _MdsWorkspace:
    ord: np.ndarray
    ord2: np.ndarray
    n: int
    nr: int
    nc: int
    dimx: int
    x: list[float]
    d: list[float]
    y: list[float]
    yf: list[float]
    mink_pow: float


_ws = _MdsWorkspace()


def _cmdscale(d: Any, k: int = 2) -> np.ndarray:
    """Classical scaling like stats::cmdscale(d, k) with default add=FALSE."""
    if hasattr(d, "_mass_dist_size"):
        n = int(d._mass_dist_size)
        raw = np.zeros((n, n), dtype=float)
        vec = np.asarray(getattr(d, "data", d), dtype=float).reshape(-1)
        idx = 0
        for row in range(n):
            for col in range(row + 1, n):
                raw[row, col] = raw[col, row] = vec[idx]
                idx += 1
    else:
        raw = np.asarray(d, dtype=float)
        if raw.ndim != 2 or raw.shape[0] != raw.shape[1]:
            raise MassError("distances must be result of 'dist' or a square matrix")
    n = raw.shape[0]
    squared = raw * raw
    row_mean = squared.mean(axis=1)
    col_mean = squared.mean(axis=0)
    grand = squared.mean()
    centered = squared - row_mean[:, None] - col_mean[None, :] + grand
    evals, evecs = np.linalg.eigh(-centered / 2.0)
    order = np.argsort(evals)[::-1]
    evals = evals[order]
    evecs = evecs[:, order]
    chosen = np.maximum(evals[:k], 0.0)
    vectors = evecs[:, :k]
    for column in range(vectors.shape[1]):
        entries = np.flatnonzero(np.abs(vectors[:, column]) > 0)
        if entries.size and vectors[entries[0], column] < 0:
            vectors[:, column] *= -1.0
    return vectors * np.sqrt(chosen)


def _init_workspace(
    pn: int,
    pc: int,
    pr: int,
    orde: np.ndarray,
    ordee: np.ndarray,
    xx: list[float],
    p: float,
) -> None:
    _ws.n = pn
    _ws.nr = pr
    _ws.nc = pc
    _ws.dimx = pr * pc
    _ws.ord = np.asarray(orde, dtype=int)
    _ws.ord2 = np.asarray(ordee, dtype=int)
    _ws.x = list(xx)
    _ws.d = [0.0] * pn
    _ws.y = [0.0] * pn
    _ws.yf = [0.0] * pn
    _ws.mink_pow = float(p)


def _unload_workspace() -> None:
    _ws.ord = np.array([], dtype=int)
    _ws.ord2 = np.array([], dtype=int)
    _ws.x = []
    _ws.d = []
    _ws.y = []
    _ws.yf = []


def _calc_dist(x: list[float]) -> None:
    euclid = _ws.mink_pow == 2.0
    index = 0
    for r1 in range(_ws.nr):
        for r2 in range(r1 + 1, _ws.nr):
            tmp = 0.0
            for c in range(_ws.nc):
                tmp1 = x[r1 + c * _ws.nr] - x[r2 + c * _ws.nr]
                tmp += tmp1 * tmp1 if euclid else abs(tmp1) ** _ws.mink_pow
            _ws.d[index] = math.sqrt(tmp) if euclid else tmp ** (1.0 / _ws.mink_pow)
            index += 1
    for index in range(_ws.n):
        _ws.y[index] = _ws.d[_ws.ord[index]]


def _mds_fn(y: list[float], yf: list[float], do_derivatives: bool, der: list[float] | None) -> float:
    n = _ws.n
    r = _ws.nr
    ncol = _ws.nc
    mink = _ws.mink_pow
    euclid = mink == 2.0
    pd = _ws.ord2

    yc = [0.0] * (n + 1)
    tmp = 0.0
    for i in range(n):
        tmp += y[i]
        yc[i + 1] = tmp
    known = 0
    while True:
        slope = 1.0e200
        ip = 0
        for i in range(known + 1, n + 1):
            tmp = (yc[i] - yc[known]) / (i - known)
            if tmp < slope:
                slope = tmp
                ip = i
        for i in range(known, ip):
            yf[i] = (yc[ip] - yc[known]) / (ip - known)
        known = ip
        if known >= n:
            break

    sstar = 0.0
    tstar = 0.0
    for i in range(n):
        tmp = y[i] - yf[i]
        sstar += tmp * tmp
        tstar += y[i] * y[i]
    ssq = 100.0 * math.sqrt(sstar / tstar)

    if not do_derivatives:
        return ssq

    assert der is not None
    x = _ws.x
    for u in range(r):
        for i in range(ncol):
            tmp = 0.0
            for s in range(r):
                if s == u:
                    continue
                if s > u:
                    k = r * u - u * (u + 1) // 2 + s - u
                else:
                    k = r * s - s * (s + 1) // 2 + u - s
                k = int(pd[k - 1])
                if k >= n:
                    continue
                tmp1 = x[u + r * i] - x[s + r * i]
                sgn = 1.0 if tmp1 >= 0 else -1.0
                tmp1 = abs(tmp1) / y[k]
                tmp += ((y[k] - yf[k]) / sstar - y[k] / tstar) * sgn * (
                    tmp1 if euclid else tmp1 ** (mink - 1.0)
                )
            der[u + i * r] = tmp * ssq
    return ssq


def _fminfn(_b: list[float]) -> float:
    _calc_dist(_ws.x)
    return _mds_fn(_ws.y, _ws.yf, False, None)


def _fmingr(_b: list[float], der: list[float]) -> None:
    _calc_dist(_ws.x)
    _mds_fn(_ws.y, _ws.yf, True, der)


def _dovm(maxit: int, trace: bool, tol: float) -> float:
    mask = [1] * _ws.dimx

    def fmin_wrap(b: list[float]) -> float:
        return _fminfn(b)

    def fmingr_wrap(b: list[float], g: list[float]) -> None:
        _fmingr(b, g)

    fmin, _fail = _vmmin(
        _ws.dimx,
        _ws.x,
        fmin_wrap,
        fmingr_wrap,
        maxit,
        trace,
        mask,
        _ABSTOL,
        tol,
        n_report=_REPORT,
    )
    return fmin


def _square_from_d(d: Any) -> tuple[np.ndarray, list[str] | None]:
    size = getattr(d, "_mass_dist_size", None)
    if size is not None:
        n = int(size)
        x = np.zeros((n, n), dtype=float)
        vec = np.asarray(getattr(d, "data", d), dtype=float).reshape(-1)
        idx = 0
        for row in range(n):
            for col in range(row + 1, n):
                x[row, col] = vec[idx]
                x[col, row] = vec[idx]
                idx += 1
        labels = getattr(d, "_mass_dist_labels", None)
        return x, list(labels) if labels is not None else None
    x = np.asarray(d, dtype=float)
    if x.ndim != 2 or x.shape[0] != x.shape[1]:
        raise MassError("distances must be result of 'dist' or a square matrix")
    rn = None
    if isinstance(d, np.ndarray) and d.dtype.names:
        pass
    return x, rn


def iso_mds(
    d: Any,
    y: Any | None = None,
    k: int = 2,
    maxit: int = 50,
    trace: bool = True,
    tol: float = 1e-3,
    p: float = 2,
) -> dict[str, Any]:
    """Non-metric multidimensional scaling."""
    missing_y = y is None
    if missing_y:
        if hasattr(d, "_mass_dist_size"):
            vec = np.asarray(getattr(d, "data", d), dtype=float)
            if not np.all(np.isfinite(vec)):
                raise MassError("an initial configuration must be supplied with NA/Infs in 'd'")
        else:
            mat = np.asarray(d, dtype=float)
            if mat.ndim == 2 and not np.all(np.isfinite(mat)):
                raise MassError("an initial configuration must be supplied with NA/Infs in 'd'")
        y = _cmdscale(d, k=k)
    else:
        y = np.asarray(y, dtype=float)
        if y.ndim != 2:
            raise MassError("'y' must be a matrix")

    x, rn = _square_from_d(d)
    n = int(x.shape[0])
    if np.isnan(n):
        raise MassError("invalid size")

    upper = x[np.triu(np.ones((n, n), dtype=bool), k=1)]
    bad = upper <= 0
    if np.any(bad & ~np.isnan(bad)):
        pairs = np.argwhere(np.triu(np.ones((n, n), dtype=bool), k=1))
        for idx, (i, j) in enumerate(pairs):
            if bad[idx]:
                raise MassError(f"zero or negative distance between objects {i + 1} and {j + 1}")
    nas = np.isnan(x)
    np.fill_diagonal(nas, False)
    if np.any(np.sum(~nas, axis=1) < 2):
        raise MassError("not enough non-missing data")

    y = np.asarray(y, dtype=float)
    if y.shape != (n, k):
        raise MassError("invalid initial configuration")
    if not np.all(np.isfinite(y)):
        raise MassError("initial configuration must be complete")

    dis = x[np.triu(np.ones((n, n), dtype=bool), k=1)]
    ord_idx = np.argsort(dis, kind="mergesort")
    nd = int(np.sum(~np.isnan(ord_idx)))

    y_colmajor = y.reshape(-1, order="F").tolist()
    try:
        _init_workspace(
            nd,
            k,
            n,
            ord_idx.astype(int),
            np.argsort(ord_idx).astype(int),
            y_colmajor,
            float(p),
        )
        stress = _dovm(int(maxit), bool(trace), float(tol))
        points = np.array(_ws.x, dtype=float).reshape((n, k), order="F")
    finally:
        _unload_workspace()

    if rn is not None:
        rownames = rn
    else:
        rownames = None
    return {"points": points, "stress": stress, "rownames": rownames}


def mass_dist(data: np.ndarray) -> MassDist:
    """Condensed Euclidean distances like R ``dist`` on a point matrix."""
    pts = np.asarray(data, dtype=float)
    n = pts.shape[0]
    out = []
    for i in range(n):
        for j in range(i + 1, n):
            out.append(float(np.sqrt(np.sum((pts[i] - pts[j]) ** 2))))
    return MassDist(np.array(out, dtype=float))
