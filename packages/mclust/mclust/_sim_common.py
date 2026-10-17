"""Shared steps for the mclust simulation functions (mclust 6.1.3).

The R functions simVEV, simVII, simVVI, simVVV (R/mclust.R) and simEVV, simVEE,
simEVE, simVVE (R/mclust2.R) do the same steps: ``set.seed(seed)`` when a seed
is given, check the parameters, draw the component labels with
``sample(1:G, size = n, replace = TRUE, prob = pro)``, then for each component k
draw ``matrix(rnorm(m * d), nrow = m, ncol = d)``, multiply by the component
factor, and add the mean. This module holds those steps.

The random stream is R's. ``boot.rng`` is the port of R's Mersenne-Twister
(``set.seed`` and ``unif_rand``). ``rnorm`` is R's default Inversion kind
(``norm_rand``: two uniforms packed into 27 bits, then ``qnorm``). ``sample``
with ``prob`` is R's ``ProbSampleReplace``. R switches to Walker alias sampling
only when more than 200 categories have ``G * p > 0.1``. That case is not
translated and raises ``NotImplementedError``.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Callable, Sequence

import numpy as np

__all__ = [
    "SimMatrix",
    "as_mean_matrix",
    "draw_rows",
    "is_missing_parameters",
    "labelled",
    "norm_rand",
    "pro_vector",
    "rnorm_matrix",
    "sample_labels",
    "seed_if_given",
    "unif",
]

_BIG = 134217728.0  # 2^27, R's norm_rand
_WALKER_LIMIT = 200  # R: walker alias sampling when more than 200 categories have n * p > 0.1


def _load_boot():
    try:
        from boot.rng import set_seed, unif
        from boot.series import qnorm
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boot"))
        from boot.rng import set_seed, unif
        from boot.series import qnorm
    return set_seed, unif, qnorm


_set_seed, unif, _qnorm = _load_boot()


class SimMatrix(np.ndarray):
    """The matrix that R's sim functions return.

    ``modelName`` is the R attribute of the same name. ``colnames`` is the R
    column dimnames, or None when R sets no dimnames (the missing-parameter case).
    """

    def __new__(cls, data: Any, model_name: str | None = None, colnames: Sequence[str] | None = None):
        obj = np.asarray(data, dtype=float).view(cls)
        obj.modelName = model_name
        obj.colnames = None if colnames is None else list(colnames)
        return obj

    def __array_finalize__(self, obj):
        self.modelName = getattr(obj, "modelName", None)
        self.colnames = getattr(obj, "colnames", None)


def seed_if_given(seed: int | None) -> None:
    """R: ``if (!is.null(seed)) set.seed(seed)``."""
    if seed is not None:
        _set_seed(int(seed))


def norm_rand() -> float:
    """One standard normal, R's default Inversion kind."""
    u1 = unif()
    u1 = int(_BIG * u1) + unif()
    return _qnorm(u1 / _BIG)


def rnorm_matrix(m: int, d: int) -> np.ndarray:
    """R ``matrix(rnorm(m * d), nrow = m, ncol = d)``: the draws fill by column."""
    draws = np.fromiter((norm_rand() for _ in range(m * d)), dtype=float, count=m * d)
    return draws.reshape((m, d), order="F")


def _revsort(values: list[float], index: list[int]) -> None:
    """R ``revsort``: heapsort into descending order, permuting ``index`` with ``values``."""
    n = len(values)
    if n <= 1:
        return
    a = [0.0] + list(values)
    ib = [0] + list(index)
    left = (n >> 1) + 1
    right = n
    while True:
        if left > 1:
            left -= 1
            ra = a[left]
            ii = ib[left]
        else:
            ra = a[right]
            ii = ib[right]
            a[right] = a[1]
            ib[right] = ib[1]
            right -= 1
            if right == 1:
                a[1] = ra
                ib[1] = ii
                values[:] = a[1:]
                index[:] = ib[1:]
                return
        i = left
        j = left << 1
        while j <= right:
            if j < right and a[j] > a[j + 1]:
                j += 1
            if ra > a[j]:
                a[i] = a[j]
                ib[i] = ib[j]
                i = j
                j += i
            else:
                j = right + 1
        a[i] = ra
        ib[i] = ii


def sample_labels(G: int, n: int, prob: Sequence[float]) -> np.ndarray:
    """R ``sample(1:G, size = n, replace = TRUE, prob = prob)``. Labels are 1-based ints."""
    p = [float(v) for v in prob]
    if len(p) != G:
        raise ValueError("incorrect number of probabilities")
    if any(math.isnan(v) or math.isinf(v) or v < 0 for v in p):
        raise ValueError("NA or negative probability in 'prob'")
    total = 0.0
    for v in p:  # FixupProb: sequential sum, then divide
        total += v
    if total <= 0:
        raise ValueError("too few positive probabilities")
    p = [v / total for v in p]
    if sum(1 for v in p if G * v > 0.1) > _WALKER_LIMIT:
        raise NotImplementedError("walker alias sampling (R, more than 200 categories) is not translated")
    perm = list(range(1, G + 1))
    _revsort(p, perm)
    for i in range(1, G):
        p[i] += p[i - 1]
    nm1 = G - 1
    out = np.empty(n, dtype=int)
    for i in range(n):
        u = unif()
        j = 0
        while j < nm1 and not (u <= p[j]):
            j += 1
        out[i] = perm[j]
    return out


def _is_na_scalar(x: Any) -> bool:
    return np.ndim(x) == 0 and isinstance(x, (int, float, np.number)) and math.isnan(float(x))


def is_missing_parameters(parameters: dict[str, Any]) -> bool:
    """R: ``any(is.na(parameters[c("mean", "variance")])) || any(is.null(...))``."""
    mean = parameters.get("mean")
    variance = parameters.get("variance")
    if mean is None or variance is None:
        return True
    return _is_na_scalar(mean) or _is_na_scalar(variance)


def as_mean_matrix(mean: Any) -> np.ndarray:
    """R ``as.matrix(parameters$mean)``: a vector becomes one column."""
    if mean is None:
        raise TypeError("parameters$mean is NULL")
    a = np.asarray(mean, dtype=float)
    if a.ndim == 0:
        return a.reshape(1, 1)
    if a.ndim == 1:
        return a.reshape(-1, 1)
    return a


def pro_vector(parameters: dict[str, Any], G: int) -> list[float]:
    """R: ``pro <- parameters$pro``, or ``rep(1/G, G)`` when it is NULL."""
    pro = parameters.get("pro")
    if pro is None:
        return [1.0 / G] * G
    return [float(v) for v in np.asarray(pro, dtype=float).reshape(-1)]


def draw_rows(mu: np.ndarray, clabels: np.ndarray, G: int, d: int,
              chol_for: Callable[[int], np.ndarray]) -> np.ndarray:
    """The R component loop: for k in 1..G, rows with label k get ``rnorm`` draws.

    ``chol_for(k)`` (0-based k) returns the d x d factor for component k. The draws
    for component k are ``matrix(rnorm(m * d), m, d) %*% factor``, plus ``mu[, k]``.
    """
    n = clabels.shape[0]
    x = np.zeros((n, d))
    counts = np.bincount(clabels, minlength=G + 1)  # R tabulate(clabels, nbins = G)
    for k in range(G):
        m = int(counts[k + 1])
        z = rnorm_matrix(m, d) @ chol_for(k)
        x[clabels == k + 1] = z + mu[:, k]
    return x


def labelled(clabels: np.ndarray, x: np.ndarray) -> np.ndarray:
    """R ``cbind(group = clabels, x)``."""
    return np.column_stack([clabels.astype(float), x])
