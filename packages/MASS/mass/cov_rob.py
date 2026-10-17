"""Resistant multivariate location and scatter (MASS cov.rob)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any

import numpy as np

from boot.rng import unif as _runif

from mass._r_rng import set_seed as _set_r_seed
from mass.errors import MassError


def _match_arg(value: str | None, choices: list[str]) -> str:
    if value is None:
        return choices[0]
    text = str(value)
    exact = [item for item in choices if item == text]
    if len(exact) == 1:
        return exact[0]
    hits = [item for item in choices if item.startswith(text)]
    if len(hits) == 1:
        return hits[0]
    if not hits:
        raise MassError("'arg' should be one of " + ", ".join(repr(item) for item in choices))
    raise MassError("'arg' matched more than one choice: " + ", ".join(hits))


def _dnrm2(values) -> float:
    scale = 0.0
    ssq = 1.0
    for value in values:
        value = float(value)
        if value != 0.0:
            absxi = abs(value)
            if scale < absxi:
                ratio = scale / absxi
                ssq = 1.0 + ssq * ratio * ratio
                scale = absxi
            else:
                ratio = absxi / scale
                ssq = ssq + ratio * ratio
    return scale * math.sqrt(ssq)


def _ddot(left, right) -> float:
    total = 0.0
    for a, b in zip(left, right, strict=False):
        total += float(a) * float(b)
    return total


def _linpack_qr(x: np.ndarray, tol: float = 1e-7) -> tuple[np.ndarray, int]:
    """R default qr (LAPACK=FALSE) storage and rank."""
    matrix = np.array(x, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    if n == 0 or p == 0:
        return matrix, 0
    qraux = [0.0] * p
    work1 = [0.0] * p
    work2 = [0.0] * p
    for j in range(p):
        qraux[j] = _dnrm2(matrix[:, j])
        work1[j] = qraux[j]
        work2[j] = qraux[j] if qraux[j] != 0.0 else 1.0
    lup = min(n, p)
    k = p + 1
    for col in range(lup):
        while (col + 1) < k and qraux[col] < work2[col] * tol:
            block = matrix[:, col:p].copy()
            matrix[:, col : p - 1] = block[:, 1:]
            matrix[:, p - 1] = block[:, 0]
            saved_q, saved_1, saved_2 = qraux[col], work1[col], work2[col]
            for j in range(col, p - 1):
                qraux[j] = qraux[j + 1]
                work1[j] = work1[j + 1]
                work2[j] = work2[j + 1]
            qraux[p - 1] = saved_q
            work1[p - 1] = saved_1
            work2[p - 1] = saved_2
            k -= 1
        if (col + 1) != n:
            nrmxl = _dnrm2(matrix[col:, col])
            if nrmxl != 0.0:
                pivot = float(matrix[col, col])
                if pivot != 0.0:
                    nrmxl = math.copysign(nrmxl, pivot)
                matrix[col:, col] = matrix[col:, col] / nrmxl
                matrix[col, col] = 1.0 + float(matrix[col, col])
                if p >= col + 2:
                    for j in range(col + 1, p):
                        dot = _ddot(matrix[col:, col], matrix[col:, j])
                        scale = -dot / float(matrix[col, col])
                        matrix[col:, j] = matrix[col:, j] + scale * matrix[col:, col]
                        if qraux[j] != 0.0:
                            entry = abs(float(matrix[col, j])) / qraux[j]
                            tt = 1.0 - entry * entry
                            if tt < 0.0:
                                tt = 0.0
                            if abs(tt) >= 1e-6:
                                qraux[j] = qraux[j] * math.sqrt(tt)
                            else:
                                qraux[j] = _dnrm2(matrix[col + 1 :, j])
                                work1[j] = qraux[j]
                qraux[col] = float(matrix[col, col])
                matrix[col, col] = -nrmxl
    rank = int(min(k - 1, n))
    return matrix, rank


def _mah(xr: np.ndarray, nnew: int, p: int, point: np.ndarray, work: list[float]) -> float:
    ss = 0.0
    for j in range(p):
        s = float(point[j])
        if j > 0:
            for i in range(j):
                s -= work[i] * float(xr[i, j])
        work[j] = s / float(xr[j, j])
        ss += work[j] * work[j]
    return ss * (nnew - 1)


def _do_one(
    x: np.ndarray,
    which: np.ndarray,
    n: int,
    p: int,
    work: list[float],
) -> tuple[bool, float, np.ndarray]:
    nnew = len(which)
    xr = np.array(x[which, :], dtype=np.float64, copy=True)
    means = xr.mean(axis=0)
    xr -= means
    matrix, rank = _linpack_qr(xr)
    if rank < p:
        return True, 0.0, np.zeros(n, dtype=np.float64)
    det = 0.0
    for k in range(p):
        det += math.log(abs(float(matrix[k, k])))
    d2 = np.empty(n, dtype=np.float64)
    centered = x - means
    for i in range(n):
        d2[i] = _mah(matrix, nnew, p, centered[i], work)
    return False, det, d2


def _next_set(which: list[int], n: int, k: int) -> None:
    j = k - 1
    tmp = which[j] + 1
    which[j] = tmp
    while j > 0 and which[j] >= n - (k - 1 - j):
        tmp = which[j - 1] + 1
        which[j - 1] = tmp
        j -= 1
    for i in range(j + 1, k):
        which[i] = which[i - 1] + 1


def _sample_noreplace(n: int, k: int) -> np.ndarray:
    ind = list(range(n))
    nn = n
    out = [0] * k
    for i in range(k):
        j = int(nn * _runif())
        out[i] = ind[j]
        ind[j] = ind[nn - 1]
        nn -= 1
    return np.asarray(out, dtype=int)


def _qchisq(p: float, df: float) -> float:
    if df <= 0 or p <= 0 or p >= 1:
        return math.nan
    lo, hi = 0.0, df + 10.0 * math.sqrt(2.0 * df)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        x = mid / 2.0
        a = df / 2.0
        term = 1.0 / a
        total = term
        for k in range(1, 10000):
            term *= x / (a + k)
            total += term
            if abs(term) < abs(total) * 1e-16:
                break
        cdf = math.exp(-x + a * math.log(x)) * total / math.gamma(a) if x > 0 else 0.0
        if cdf < p:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def _iqr_col(x: np.ndarray) -> np.ndarray:
    q75 = np.quantile(x, 0.75, axis=0, method="linear")
    q25 = np.quantile(x, 0.25, axis=0, method="linear")
    return q75 - q25


def _r_var(x: np.ndarray) -> np.ndarray:
    n = x.shape[0]
    if n < 2:
        return np.full((x.shape[1], x.shape[1]), np.nan)
    centered = x - x.mean(axis=0)
    return (centered.T @ centered) / (n - 1)


def _mahalanobis(x: np.ndarray, center: np.ndarray, cov: np.ndarray) -> np.ndarray:
    centered = x - center
    inv = np.linalg.inv(cov)
    return np.einsum("ij,jk,ik->i", centered, inv, centered)


@dataclass
class CovRob:
    center: np.ndarray
    cov: np.ndarray
    n_obs: int
    cor: np.ndarray | None = None
    sing: str | None = None
    crit: float | None = None
    best: np.ndarray | None = None


def cov_rob(
    x,
    cor: bool = False,
    quantile_used: int | None = None,
    method: str | None = None,
    nsamp: int | str = "best",
    seed: Any = None,
) -> CovRob:
    """Resistant estimation of multivariate location and scatter."""
    method = _match_arg(method, ["mve", "mcd", "classical"])
    matrix = np.asarray(x, dtype=float)
    if matrix.ndim != 2:
        matrix = np.atleast_2d(matrix)
    if not np.all(np.isfinite(matrix)):
        raise MassError("missing or infinite values are not allowed")
    n, p = matrix.shape
    if n < p + 1:
        raise MassError(f"at least {p + 1} cases are needed")

    if method == "classical":
        ans = CovRob(center=matrix.mean(axis=0), cov=_r_var(matrix), n_obs=n)
        if cor:
            sd = np.sqrt(np.diag(ans.cov))
            ans.cor = (ans.cov / sd[:, None]) / sd[None, :]
        return ans

    qn = int(math.floor((n + p + 1) / 2)) if quantile_used is None else int(quantile_used)
    if qn < p + 1:
        raise MassError(f"'quantile' must be at least {p + 1}")
    if qn > n - 1:
        raise MassError(f"'quantile' must be at most {n - 1}")

    divisor = _iqr_col(matrix)
    if np.any(divisor == 0):
        raise MassError("at least one column has IQR 0")
    xs = matrix / divisor
    ps = p + 1
    nexact = math.comb(n, ps)
    nsamp_val = nsamp
    if isinstance(nsamp_val, str) and nsamp_val == "best":
        nsamp_val = "exact" if nexact < 5000 else "sample"
    if isinstance(nsamp_val, (int, float)) and not isinstance(nsamp_val, bool):
        if int(nsamp_val) > nexact:
            warnings.warn(
                f"only {nexact} sets, so all sets will be tried",
                stacklevel=2,
            )
            nsamp_val = "exact"
    sample = nsamp_val != "exact"
    if sample:
        if nsamp_val == "sample":
            ntrials = min(500 * ps, 3000)
        else:
            ntrials = int(nsamp_val)
    else:
        ntrials = nexact
    if ntrials > 2147483647:
        if sample:
            raise MassError(f"Too many samples ({ntrials:.3g})")
        raise MassError(f'Too many combinations ({ntrials:.3g}) for nsamp = "exact"')

    if sample and seed is not None:
        _set_r_seed(int(seed))

    mcd = method == "mcd"
    best = float("inf")
    sing = 0
    bestone = np.zeros(n, dtype=bool)
    work = [0.0] * p
    d2 = np.zeros(n, dtype=np.float64)
    d2copy = np.zeros(n, dtype=np.float64)

    which = list(range(ps))
    for trial in range(ntrials):
        if not sample:
            if trial > 0:
                _next_set(which, n, ps)
            which_arr = np.asarray(which, dtype=int)
        else:
            which_arr = _sample_noreplace(n, ps)

        this_sing, det, d2 = _do_one(xs, which_arr, n, p, work)
        if this_sing:
            sing += 1
            continue

        d2copy[:] = d2
        lim = float(np.partition(d2copy, qn - 1)[qn - 1])
        if not mcd:
            thiscrit = p * math.log(lim) + 2.0 * det
        else:
            thiscrit = 0.0
            for iter_idx in range(4):
                if iter_idx > 0:
                    d2copy[:] = d2
                    lim = float(np.partition(d2copy, qn - 1)[qn - 1])
                which2 = np.nonzero(d2 <= lim)[0]
                this_sing, det, d2 = _do_one(xs, which2[:qn], n, p, work)
                if this_sing:
                    thiscrit = float("inf")
                    break
                if iter_idx > 0 and 2.0 * det >= 0.999 * thiscrit:
                    break
                thiscrit = 2.0 * det

        if thiscrit < best:
            best = thiscrit
            bestone = d2 <= lim

    crit = best + 2.0 * float(np.sum(np.log(divisor)))
    if mcd:
        crit -= p * math.log(qn - 1)

    best_idx = np.where(bestone)[0]
    if best_idx.size == 0:
        raise MassError("'x' is probably collinear")

    sing_msg = f"{sing} singular samples of size {ps} out of {ntrials}"

    means = xs[best_idx].mean(axis=0)
    rcov = _r_var(xs[best_idx]) * (1.0 + 15.0 / (n - p)) ** 2
    dist = _mahalanobis(xs, means, rcov)
    cut = _qchisq(0.975, p) * float(np.quantile(dist, qn / n, method="linear")) / _qchisq(qn / n, p)
    mask = dist < cut
    cov = _r_var(xs[mask]) * divisor[:, None] * divisor[None, :]
    center = xs[mask].mean(axis=0) * divisor

    ans = CovRob(
        center=center,
        cov=cov,
        n_obs=n,
        sing=sing_msg,
        crit=crit,
        best=best_idx + 1,
    )
    if cor:
        sd = np.sqrt(np.diag(cov))
        ans.cor = (cov / sd[:, None]) / sd[None, :]
    return ans
