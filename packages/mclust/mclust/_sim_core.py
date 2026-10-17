"""Helpers for the core mclust sim translations: sim, simE, simV, simEII, simEEI, simEEE, simEEV, simEVI, simVEI.

The draws follow R 4.5 exactly for a fixed ``set.seed``:

- ``r_rnorm`` is R's ``rnorm(n, mean, sd)``. A zero or non-finite sd (or a non-finite mean)
  consumes no uniform, as in R's C code.
- ``r_sample_prob`` is R's ``sample(k, size, replace = TRUE, prob = p)`` for at most 200
  categories with positive probability (R's ``ProbSampleReplace``). Probabilities are sorted
  with R's ``revsort`` heapsort, so ties keep R's order.
- ``r_diag`` is R's ``diag(x)``. For a length-one ``x`` it is the identity of size ``as.integer(x)``.
- ``r_rmul`` / ``r_rmul_like`` are R's recycled ``*``.

``norm_rand`` is the ported generator from extraDistr, and ``unif`` is ``boot.rng.unif``.
Both draw from the same Mersenne-Twister stream.
"""

from __future__ import annotations

import math
import sys
import warnings
from pathlib import Path
from typing import Any, Sequence

import numpy as np

try:
    from boot.rng import set_seed, unif
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
    from boot.rng import set_seed, unif

try:
    from extradistr._rng import norm_rand
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "extraDistr"))
    from extradistr._rng import norm_rand


class SimMatrix(np.ndarray):
    """Numeric matrix that carries R's ``modelName`` attribute and column names."""

    def __new__(cls, data: Any, model_name: str, colnames: Sequence[str]):
        obj = np.asarray(data, dtype=float).view(cls)
        obj.model_name = model_name
        obj.colnames = list(colnames)
        return obj

    def __array_finalize__(self, obj):
        self.model_name = getattr(obj, "model_name", None)
        self.colnames = getattr(obj, "colnames", None)


def seed_if(seed: Any) -> None:
    """R: if (!is.null(seed)) set.seed(seed)."""
    if seed is not None:
        set_seed(int(seed))


def r_rnorm(n: int, mean: Any = 0.0, sd: Any = 1.0) -> np.ndarray:
    """R ``rnorm(n, mean, sd)`` with R's recycling of ``mean`` and ``sd``."""
    mean_v = np.atleast_1d(np.asarray(mean, dtype=float)).ravel()
    sd_v = np.atleast_1d(np.asarray(sd, dtype=float)).ravel()
    out = np.empty(int(n), dtype=float)
    for i in range(int(n)):
        mu = mean_v[i % mean_v.size] if mean_v.size else math.nan
        sigma = sd_v[i % sd_v.size] if sd_v.size else math.nan
        if math.isnan(mu) or not math.isfinite(sigma) or sigma < 0.0:
            out[i] = math.nan
        elif sigma == 0.0 or not math.isfinite(mu):
            out[i] = mu
        else:
            out[i] = mu + sigma * norm_rand()
    return out


def _revsort(a: list[float], ib: list[int]) -> tuple[list[float], list[int]]:
    """R's ``revsort``: heapsort ``a`` into descending order, permuting ``ib`` alongside."""
    n = len(a)
    if n <= 1:
        return a, ib
    A = [0.0] + list(a)
    IB = [0] + list(ib)
    l = (n >> 1) + 1
    ir = n
    while True:
        if l > 1:
            l -= 1
            ra = A[l]
            ii = IB[l]
        else:
            ra = A[ir]
            ii = IB[ir]
            A[ir] = A[1]
            IB[ir] = IB[1]
            ir -= 1
            if ir == 1:
                A[1] = ra
                IB[1] = ii
                break
        i = l
        j = l << 1
        while j <= ir:
            if j < ir and A[j] > A[j + 1]:
                j += 1
            if ra > A[j]:
                A[i] = A[j]
                IB[i] = IB[j]
                i = j
                j += j
            else:
                j = ir + 1
        A[i] = ra
        IB[i] = ii
    return A[1:], IB[1:]


def r_sample_prob(n_pop: int, size: int, prob: Any) -> np.ndarray:
    """R ``sample.int(n_pop, size, replace = TRUE, prob = prob)``. Values are 1-based."""
    p = [float(v) for v in np.asarray(prob, dtype=float).ravel()]
    if len(p) != n_pop:
        raise ValueError("incorrect number of probabilities")
    total = 0.0
    npos = 0
    for v in p:
        if not math.isfinite(v):
            raise ValueError("NA in probability vector")
        if v < 0.0:
            raise ValueError("negative probability")
        if v > 0.0:
            npos += 1
            total += v
    if npos == 0:
        raise ValueError("too few positive probabilities")
    p = [v / total for v in p]
    nc = sum(1 for v in p if n_pop * v > 0.1)
    if nc > 200:
        raise NotImplementedError("walker alias sampling (more than 200 categories) is not translated")

    perm = list(range(1, n_pop + 1))
    p, perm = _revsort(p, perm)
    for i in range(1, n_pop):
        p[i] += p[i - 1]

    nm1 = n_pop - 1
    out = np.empty(int(size), dtype=int)
    for i in range(int(size)):
        ru = unif()
        j = 0
        while j < nm1:
            if ru <= p[j]:
                break
            j += 1
        out[i] = perm[j]
    return out


def tabulate(x: np.ndarray, nbins: int) -> np.ndarray:
    """R ``tabulate(x, nbins)``."""
    return np.bincount(np.asarray(x, dtype=int), minlength=nbins + 1)[1 : nbins + 1]


def r_diag(x: Any) -> np.ndarray:
    """R ``diag(x)``. A length-one ``x`` gives the identity of size ``as.integer(x)``."""
    v = np.atleast_1d(np.asarray(x, dtype=float)).ravel()
    if v.size == 1:
        k = int(v[0])
        if k < 0:
            raise ValueError("invalid 'nrow' value (< 0)")
        return np.eye(k)
    return np.diag(v)


def r_rmul(a: Any, b: Any) -> np.ndarray:
    """R ``a * b`` on vectors: the shorter operand is recycled."""
    av = np.atleast_1d(np.asarray(a, dtype=float)).ravel()
    bv = np.atleast_1d(np.asarray(b, dtype=float)).ravel()
    if av.size == 0 or bv.size == 0:
        return np.empty(0)
    m = max(av.size, bv.size)
    idx = np.arange(m)
    return av[idx % av.size] * bv[idx % bv.size]


def r_rmul_like(a: Any, b: Any) -> np.ndarray:
    """R ``a * b`` where ``b`` is an array: ``a`` is recycled along the column-major order of ``b``."""
    barr = np.asarray(b, dtype=float)
    flat = r_rmul(a, barr.ravel(order="F"))
    return flat.reshape(barr.shape, order="F")


def as_matrix(x: Any) -> np.ndarray:
    """R ``as.matrix`` for a numeric vector or matrix."""
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 0:
        return arr.reshape(1, 1)
    if arr.ndim == 1:
        return arr.reshape(-1, 1)
    return arr


def _list_element_is_na(val: Any) -> bool:
    """R ``is.na`` on one element of a list: TRUE only for a length-one atomic NA."""
    if val is None or isinstance(val, dict):
        return False
    try:
        arr = np.asarray(val, dtype=float)
    except (TypeError, ValueError):
        return False
    return arr.size == 1 and bool(np.isnan(arr.reshape(())))


def parameters_missing(parameters: dict) -> bool:
    """R: ``any(is.na(parameters[c("mean", "variance")]))``.

    R applies ``is.null()`` to the whole list, which is always FALSE, so a NULL element does
    not count here. A NULL variance is not a missing-parameter result: R then fails in
    ``sqrt(NULL)``, and this translation fails at the same point.
    """
    return any(_list_element_is_na(parameters.get(key)) for key in ("mean", "variance"))


def mixing_proportions(parameters: dict, G: int) -> np.ndarray:
    """R: ``pro <- parameters$pro``; if NULL, ``rep(1/G, G)``."""
    pro = parameters.get("pro")
    if pro is None:
        return np.full(G, 1.0 / G)
    return np.asarray(pro, dtype=float).ravel()


def gaussian_rows(z: np.ndarray, chol: np.ndarray, mu_col: np.ndarray) -> np.ndarray:
    """R ``sweep(Z %*% chol, MARGIN = 2, STATS = mu_col, FUN = "+")``."""
    return z @ chol + mu_col[np.newaxis, :]


def draw_matrix(m: int, d: int) -> np.ndarray:
    """R ``matrix(rnorm(m * d), nrow = m, ncol = d)``: column-major fill."""
    flat = r_rnorm(m * d)
    return flat.reshape(d, m).T


def mean_matrix(parameters: dict) -> tuple[np.ndarray, int, int]:
    """R: ``mu <- as.matrix(parameters$mean); d <- nrow(mu); G <- ncol(mu)``.

    R's ``as.matrix(NULL)`` is an error, so a NULL mean is an error here too.
    """
    if parameters.get("mean") is None:
        raise ValueError("'data' must be of a vector type, was 'NULL'")
    mu = as_matrix(parameters["mean"])
    return mu, mu.shape[0], mu.shape[1]


def multivariate_sim(
    model_name: str,
    n: int,
    clabels: np.ndarray,
    G: int,
    d: int,
    mu: np.ndarray,
    chol_for: Any,
) -> SimMatrix:
    """Body shared by the sim functions that draw each component with a Cholesky factor.

    ``chol_for(k)`` returns the d-by-d factor for component k (1-based).
    """
    ctabel = tabulate(clabels, G)
    x = np.zeros((int(n), d))
    for k in range(1, G + 1):
        m = int(ctabel[k - 1])
        z = draw_matrix(m, d)
        x[clabels == k, :] = gaussian_rows(z, chol_for(k), mu[:, k - 1])
    colnames = ["group"] + [f"x{i}" for i in range(1, d + 1)]
    return SimMatrix(np.column_stack([clabels.astype(float), x]), model_name, colnames)


def missing_result(model_name: str, n: int, ncols: int) -> SimMatrix:
    """The NA matrix R returns, with a warning, when parameters are missing. R sets no colnames."""
    warnings.warn("parameters are missing")
    return SimMatrix(np.full((int(n), ncols), np.nan), model_name, [])
