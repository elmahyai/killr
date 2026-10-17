"""Resistant regression (MASS lqs.default)."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from boot.rng import unif as _runif
from boot.series import qnorm as _qnorm

from mass._r_rng import set_seed as _set_r_seed
from mass.cov_rob import _ddot, _dnrm2, _next_set, _sample_noreplace
from mass.errors import MassError


def _dnorm(k: float) -> float:
    return math.exp(-0.5 * k * k) / math.sqrt(2.0 * math.pi)


def _lm_wfit(x: np.ndarray, y: np.ndarray, w: np.ndarray) -> dict[str, Any]:
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float).reshape(-1)
    w = np.asarray(w, dtype=float).reshape(-1)
    scale_w = np.sqrt(w)
    _q, r = np.linalg.qr(x * scale_w[:, None], mode="reduced")
    coef = np.linalg.solve(r, _q.T @ (y * scale_w))
    resid = y - x @ coef
    return {"coefficients": coef, "residuals": resid}


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


def _linpack_qr_aux(x: np.ndarray, tol: float = 1e-7) -> tuple[np.ndarray, np.ndarray, int]:
    """R ``qr(..., LAPACK = FALSE)`` storage with ``qraux``."""
    matrix = np.array(x, dtype=np.float64, copy=True)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    n, p = matrix.shape
    if n == 0 or p == 0:
        return matrix, np.zeros(p), 0
    qraux = np.zeros(p)
    work1 = np.zeros(p)
    work2 = np.zeros(p)
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
    return matrix, qraux, rank


def _apply_reflector(
    x: np.ndarray, col: int, qraux_val: float, target: np.ndarray
) -> None:
    if qraux_val == 0.0:
        return
    n = x.shape[0]
    diag = float(x[col, col])
    x[col, col] = qraux_val
    length = n - col
    reflector = x[col:, col]
    t = -float(np.dot(reflector, target[col:])) / float(x[col, col])
    target[col:] = target[col:] + t * reflector
    x[col, col] = diag


def _dqrsl_coef(x: np.ndarray, rank: int, qraux: np.ndarray, y: np.ndarray) -> np.ndarray:
    """LINPACK ``dqrsl`` with ``job = 100``."""
    n, p = x.shape
    k = rank
    qty = np.array(y, dtype=np.float64, copy=True)
    for j in range(k):
        _apply_reflector(x, j, float(qraux[j]), qty)
    coef = np.zeros(p, dtype=np.float64)
    coef[:k] = qty[:k]
    for j in range(k - 1, -1, -1):
        diag = float(x[j, j])
        if diag == 0.0:
            break
        coef[j] /= diag
        if j > 0:
            coef[:j] -= coef[j] * x[:j, j]
    return coef


def _lmsadj(x: np.ndarray, qn: int) -> tuple[float, float]:
    n = x.shape[0]
    k = qn - 1
    best = float(x[k] - x[0])
    adj = 0.5 * (float(x[k]) + float(x[0]))
    for i in range(1, n - k):
        length = float(x[i + k] - x[i])
        if length < best:
            best = length
            adj = 0.5 * (float(x[i + k]) + float(x[i]))
    return adj, 0.25 * best * best


def _ltsadj(x: np.ndarray, qn: int) -> tuple[float, float]:
    n = x.shape[0]
    k = qn - 1
    m1 = float(np.sum(x[:qn]))
    m2 = float(np.sum(x[:qn] ** 2))
    adj = m1 / qn
    best = m2 - m1 * m1 / qn
    for i in range(1, n - k):
        m1 += float(x[i + k] - x[i - 1])
        m2 += float(x[i + k] ** 2 - x[i - 1] ** 2)
        ss = m2 - m1 * m1 / qn
        if ss < best:
            best = ss
            adj = m1 / qn
    return adj, best


def _chi(u: float, k0: float) -> float:
    x = (u / k0) ** 2
    if x > 1.0:
        return 1.0
    return x * (3.0 + x * (-3.0 + x))


def _psi_s(u: float, k0: float) -> float:
    ratio = min(1.0, abs(u / k0))
    return (1.0 - ratio**2) ** 2


def _r_psort(values: np.ndarray, k: int) -> None:
    part = np.partition(values, k)
    values[:] = part


def _lqs_fitlots(
    x: np.ndarray,
    y: np.ndarray,
    qn: int,
    lts: int,
    adj: bool,
    sample: bool,
    ps: int,
    ntrials: int,
    k0: float,
    beta: float,
    rng_unif: Any = _runif,
) -> dict[str, Any]:
    """Port of ``lqs_fitlots`` from ``MASS/src/lqs.c``."""
    n, p = x.shape
    nnew = ps
    best = float("inf")
    sing = 0
    bestone = np.zeros(nnew, dtype=int)
    bestcoef = np.zeros(p, dtype=np.float64)
    target = (n - p) * beta
    first_trial = True
    a = 0.0
    which = np.arange(nnew, dtype=int)

    for trial in range(ntrials):
        if not sample:
            if trial > 0:
                wl = which.tolist()
                _next_set(wl, n, nnew)
                which = np.asarray(wl, dtype=int)
        else:
            which = _sample_noreplace(n, nnew)

        yr = y[which].copy()
        xr = x[which, :].copy()
        qr_mat, qraux, rank = _linpack_qr_aux(xr)
        if rank < p:
            sing += 1
            continue
        coef = _dqrsl_coef(qr_mat, rank, qraux, yr)
        res = y - x @ coef

        if lts < 2:
            if adj:
                res_sorted = np.sort(res)
                if lts:
                    a, thiscrit = _ltsadj(res_sorted, qn)
                else:
                    a, thiscrit = _lmsadj(res_sorted, qn)
            else:
                res_sq = (res - a) ** 2
                _r_psort(res_sq, qn - 1)
                if not lts:
                    thiscrit = float(res_sq[qn - 1])
                else:
                    thiscrit = float(np.sum(res_sq[:qn]))
        else:
            if first_trial:
                abs_res = np.abs(res)
                _r_psort(abs_res, n // 2)
                old = float(abs_res[n // 2] / 0.6745)
                first_trial = False
            else:
                total = float(np.sum(_chi(res, k0 * best)))
                if total > target:
                    continue
                old = best
            new = old
            for _iter in range(30):
                total = float(np.sum(_chi(res, k0 * old)))
                new = math.sqrt(total / target) * old
                if abs(total / target - 1.0) < 1e-4:
                    break
                old = new
            thiscrit = new

        if thiscrit < best:
            best = thiscrit
            bestone = which.copy()
            bestcoef = coef.copy()
            bestcoef[0] += a

    crit = 0.0 if best < 0.0 else best
    return {
        "crit": crit,
        "sing": sing,
        "coefficients": bestcoef,
        "bestone": bestone + 1,
    }


@dataclass
class LqsFit:
    crit: float
    sing: str
    coefficients: np.ndarray
    bestone: np.ndarray
    fitted_values: np.ndarray
    residuals: np.ndarray
    scale: np.ndarray
    method: str
    call: Any = None
    coef_names: list[str] = field(default_factory=list)


def lqs_control(psamp: float | int | None = None, nsamp: int | str = "best", adjust: bool = True) -> dict:
    """Control parameters for ``lqs`` subsampling."""
    return {"psamp": np.nan if psamp is None else psamp, "nsamp": nsamp, "adjust": adjust}


def lqs(
    x,
    y,
    *,
    intercept: bool = True,
    method: str | None = None,
    quantile: int | None = None,
    control: dict | None = None,
    k0: float = 1.548,
    seed: Any = None,
    psamp: float | int | None = None,
    nsamp: int | str | None = None,
    adjust: bool | None = None,
) -> LqsFit:
    """Fit a regression to good points via resistant subsampling."""
    return _lqs_default(
        x,
        y,
        intercept=intercept,
        method=method,
        quantile=quantile,
        control=control,
        k0=k0,
        seed=seed,
        psamp=psamp,
        nsamp=nsamp,
        adjust=adjust,
    )


def _lqs_default(
    x,
    y,
    *,
    intercept: bool = True,
    method: str | None = None,
    quantile: int | None = None,
    control: dict | None = None,
    k0: float = 1.548,
    seed: Any = None,
    psamp: float | int | None = None,
    nsamp: int | str | None = None,
    adjust: bool | None = None,
) -> LqsFit:
    method = _match_arg(method, ["lts", "lqs", "lms", "S"])
    y = np.asarray(y, dtype=np.float64).reshape(-1)
    n = y.shape[0]
    matrix = np.asarray(x, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    elif matrix.ndim != 2:
        matrix = np.asmatrix(matrix)
        matrix = np.array(matrix, dtype=np.float64)
    p = matrix.shape[1]
    if np.any(np.isnan(matrix)) or np.any(np.isnan(y)):
        raise MassError("missing values are not allowed")
    nm = list(getattr(matrix, "columns", None) or [])
    if not nm and hasattr(x, "dtype") and getattr(x.dtype, "names", None):
        nm = list(x.dtype.names)
    if not nm:
        nm = [f"X{i + 1}" for i in range(p)] if p > 1 else (["X"] if p == 1 else [])
    if intercept:
        matrix = np.column_stack([np.ones(n), matrix])
        nm = ["(Intercept)", *nm]
    p = matrix.shape[1]
    if matrix.shape[0] != n:
        raise MassError("'x' and 'y' must have the same number of rows")

    lts = 0
    beta = 0.0
    if method == "lqs" and quantile is None:
        quantile = int(math.floor((n + p + 1) / 2))
    if method == "lms":
        quantile = int(math.floor((n + 1) / 2))
    if method == "lts":
        lts = 1
        if quantile is None:
            quantile = int(math.floor(n / 2) + math.floor((p + 1) / 2))
    if method == "S":
        lts = 2
        beta = 0.5
        quantile = int(math.ceil(n / 2))
    assert quantile is not None
    if quantile > n - 1:
        raise MassError(f"'quantile' must be at most {n - 1}")

    ctrl = control if control is not None else lqs_control()
    if psamp is not None:
        ctrl = {**ctrl, "psamp": psamp}
    if nsamp is not None:
        ctrl = {**ctrl, "nsamp": nsamp}
    if adjust is not None:
        ctrl = {**ctrl, "adjust": adjust}

    ps_val = ctrl.get("psamp", np.nan)
    if ps_val is None or (isinstance(ps_val, float) and math.isnan(ps_val)):
        ps = p
    else:
        ps = int(ps_val)
    if ps < p:
        ps = p
        warnings.warn("'ps' must be at least 'p'", stacklevel=2)
    use_adj = bool(ctrl.get("adjust", True)) and intercept
    nsamp_ctrl = ctrl.get("nsamp", "best")
    nexact = math.comb(n, ps)
    if isinstance(nsamp_ctrl, str) and nsamp_ctrl == "best":
        nsamp_val: int | str = "exact" if nexact < 5000 else "sample"
    else:
        nsamp_val = nsamp_ctrl
    if isinstance(nsamp_val, (int, float)) and not isinstance(nsamp_val, bool):
        if int(nsamp_val) > nexact:
            warnings.warn(f"only {nexact} sets, so all sets will be tried", stacklevel=2)
            nsamp_val = "exact"
    sample = nsamp_val != "exact"
    if sample:
        if nsamp_val == "sample":
            ntrials = min(500 * ps, 3000)
        else:
            ntrials = int(nsamp_val)
    else:
        ntrials = nexact

    if sample and seed is not None:
        _set_r_seed(int(seed))

    z = _lqs_fitlots(
        matrix,
        y,
        quantile,
        lts,
        use_adj,
        sample,
        ps,
        ntrials,
        k0,
        beta,
    )
    if z["sing"] == ntrials:
        raise MassError("'lqs' failed: all the samples were singular")
    fitted = matrix @ z["coefficients"]
    residuals = y - fitted
    c1 = 1.0 / _qnorm((n + quantile) / (2.0 * n))
    if lts == 1:
        s0 = math.sqrt(z["crit"] / quantile) / math.sqrt(
            1.0 - 2.0 * n * _dnorm(1.0 / c1) / (quantile * c1)
        )
    elif lts == 0:
        s0 = math.sqrt(z["crit"]) * c1
    else:
        s0 = z["crit"]
    res = residuals
    ind = np.abs(res) <= 2.5 * s0
    s2 = float(np.sum(res[ind] ** 2) / (np.sum(ind) - p))
    scale = np.array([s0, math.sqrt(s2)], dtype=np.float64)
    coefficients = z["coefficients"].copy()
    if method == "S":
        resid = residuals
        scale_s = s0
        temp = _lm_wfit(matrix, y, np.ones(n))
        for _ in range(30):
            w = np.array([_psi_s(r / scale_s, k0) for r in resid], dtype=np.float64)
            temp = _lm_wfit(matrix, y, w)
            resid = temp["residuals"]
            s2 = scale_s * math.sqrt(float(np.sum(_chi(resid / scale_s, k0))) / ((n - p) * beta))
            if abs(s2 / scale_s - 1.0) < 1e-5:
                scale_s = s2
                break
            scale_s = s2
        coefficients = temp["coefficients"]
        fitted = matrix @ coefficients
        residuals = resid
        scale = np.array([scale_s], dtype=np.float64)

    sing_msg = f"{z['sing']} singular samples of size {ps} out of {ntrials}"
    bestone = np.sort(z["bestone"])
    return LqsFit(
        crit=z["crit"],
        sing=sing_msg,
        coefficients=coefficients,
        bestone=bestone,
        fitted_values=fitted,
        residuals=residuals,
        scale=scale,
        method=method,
        coef_names=nm,
    )
