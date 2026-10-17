"""Square-root factor of a correlation structure (nlme corFactor)."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from nlme.corstruct import CorDim, Dim
from nlme.corcompsymm import CorCompSymm
from nlme.corsymm import CorSymm

@dataclass(frozen=True, slots=True)
class CorFactor:
    values: np.ndarray
    log_det: float


def corFactor(object, **_ignored) -> CorFactor:
    """Extract the square-root factor (and log determinant) of a correlation structure."""
    if isinstance(object, CorCompSymm):
        return _cor_factor_comp_symm(object)
    if isinstance(object, CorSymm):
        return _cor_factor_symm(object)
    stored = getattr(object, "factor", None)
    if stored is not None:
        log_det = getattr(object, "log_det", None)
        if log_det is None:
            log_det = 0.0
        return CorFactor(np.asarray(stored, dtype=np.float64).copy(), float(-log_det))
    raise TypeError(f"corFactor is not implemented for {type(object)!r}")


def _cor_factor_comp_symm(object: CorCompSymm) -> CorFactor:
    if object.dim is None or object.inf is None:
        raise ValueError("corCompSymm object must be initialized before corFactor")
    dim = object.dim
    assert isinstance(dim, CorDim)
    values, log_det = _comp_symm_factor_list(float(object.value), float(object.inf), dim)
    return CorFactor(values, log_det)


def _cor_factor_symm(object: CorSymm) -> CorFactor:
    if object.dim is None or object.max_cov is None:
        raise ValueError("corSymm object must be initialized before corFactor")
    dim = object.dim
    assert isinstance(dim, CorDim)
    covariate = _covariate_vector(object)
    values, log_det = symm_fact_list(
        np.asarray(object.value, dtype=np.float64),
        covariate,
        int(object.max_cov),
        dim,
    )
    return CorFactor(values, log_det)


def _covariate_vector(object: CorSymm) -> list[int]:
    cov = object.covariate
    if isinstance(cov, dict):
        parts = [np.asarray(v, dtype=np.int64).reshape(-1) for v in cov.values()]
        return np.concatenate(parts).astype(np.int32).tolist()
    return np.asarray(cov, dtype=np.int64).reshape(-1).astype(np.int32).tolist()


def _comp_symm_factor_list(par: float, inf: float, dim: CorDim) -> tuple[np.ndarray, float]:
    rho = (math.exp(par) + inf) / (math.exp(par) + 1.0)
    out = np.zeros(dim.sum_len_sq, dtype=np.float64)
    log_det = 0.0
    offset = 0
    for length in dim.len:
        block, block_ld = _comp_symm_fact(rho, length)
        out[offset : offset + length * length] = block.reshape(-1, order="F")
        log_det += block_ld
        offset += length * length
    return out, log_det


def _comp_symm_fact(rho: float, n: int) -> tuple[np.ndarray, float]:
    mat = np.zeros((n, n), dtype=np.float64, order="F")
    log_det = 0.0
    aux = 1.0 + (n - 1) * rho
    log_det -= math.log(aux) / 2.0
    scale = 1.0 / math.sqrt(aux * n)
    for i in range(n):
        mat[0, i] = scale
    aux2 = 1.0 - rho
    log_det -= (n - 1) * math.log(aux2) / 2.0
    for i in range(1, n):
        aux1 = -1.0 / math.sqrt(aux2 * i * (i + 1))
        for j in range(i):
            mat[i, j] = aux1
        mat[i, i] = -i * aux1
    return mat, log_det


def symm_full_corr(pars: np.ndarray, max_c: int) -> np.ndarray:
    """Map unconstrained corSymm parameters to packed correlations."""
    n = max_c
    work = np.zeros(n * (n + 1) // 2, dtype=np.float64)
    src = 0
    dest = 0
    for i in range(n):
        aux = 1.0
        for j in range(i):
            aux1 = math.exp(float(pars[src]))
            aux1 = math.pi * aux1 / (1.0 + aux1)
            work[dest] = aux * math.cos(aux1)
            aux *= math.sin(aux1)
            dest += 1
            src += 1
        work[dest] = aux
        dest += 1
    crr = np.zeros(n * (n - 1) // 2, dtype=np.float64)
    dest = 0
    for i in range(n - 1):
        ip1 = i + 1
        src_base = i * (i + 1) // 2
        for j in range(ip1, n):
            src = src_base
            src1 = j * (j + 1) // 2
            # R's d_dot_prod is a sequential sum. np.dot may reorder it, which moves the last bit.
            acc = 0.0
            for k in range(ip1):
                acc += work[src + k] * work[src1 + k]
            crr[dest] = acc
            dest += 1
    return crr


def _symm_mat(crr: np.ndarray, time: Sequence[int], n: int, max_c: int) -> np.ndarray:
    mat = np.eye(n, dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            n1 = time[i] if time[i] < time[j] else time[j]
            n2 = time[i] + time[j] - 2 * n1 - 1
            k = n1 * max_c - n1 * (n1 + 1) // 2 + n2
            mat[i, j] = crr[k]
            mat[j, i] = crr[k]
    return mat


def _symm_fact(crr: np.ndarray, time: Sequence[int], n: int, max_c: int) -> tuple[np.ndarray, float]:
    mat = _symm_mat(crr, time, n, max_c)
    chol = np.linalg.cholesky(mat)
    log_det = -float(np.sum(np.log(np.diag(chol))))
    out = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        rhs = np.zeros(n, dtype=np.float64)
        rhs[i] = 1.0
        out[:, i] = np.linalg.solve(chol.T, rhs)
    return out, log_det


def symm_fact_list(
    pars: np.ndarray,
    time: list[int],
    max_c: int,
    dim: CorDim,
) -> tuple[np.ndarray, float]:
    crr = symm_full_corr(pars, max_c)
    out = np.zeros(dim.sum_len_sq, dtype=np.float64)
    log_det = 0.0
    offset = 0
    tpos = 0
    for length in dim.len:
        block, block_ld = _symm_fact(crr, time[tpos : tpos + length], length, max_c)
        out[offset : offset + length * length] = block.reshape(-1, order="F")
        log_det += block_ld
        offset += length * length
        tpos += length
    return out, log_det
