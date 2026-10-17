"""Geweke MCMC convergence diagnostic (Z-score).

Translated from coda 0.19-4.1 ``geweke.diag`` in ``R/geweke.R``.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from coda.as_mcmc import Mcmc, as_mcmc
from coda.as_mcmc_list import is_mcmc_list
from coda.effectiveSize import _r_mean, _spectrum0_ar
from coda.niter import niter


@dataclass
class GewekeDiag:
    """Result of ``geweke_diag`` (R class ``geweke.diag``)."""

    z: np.ndarray
    frac: np.ndarray


def geweke_diag(x, frac1=0.1, frac2=0.5):
    """Compare early and late chain segments using Geweke's Z-scores."""
    frac1 = float(frac1)
    frac2 = float(frac2)
    if frac1 < 0 or frac1 > 1:
        raise ValueError("frac1 invalid")
    if frac2 < 0 or frac2 > 1:
        raise ValueError("frac2 invalid")
    if frac1 + frac2 > 1:
        raise ValueError("start and end sequences are overlapping")
    if is_mcmc_list(x):
        return [geweke_diag(chain, frac1=frac1, frac2=frac2) for chain in x.chains]
    chain = as_mcmc(x)
    return _geweke_diag_mcmc(chain, frac1, frac2)


def _geweke_diag_mcmc(chain: Mcmc, frac1: float, frac2: float) -> GewekeDiag:
    xstart = float(chain.start)
    xend = float(chain.end)
    span = xend - xstart
    win_starts = (
        xstart,
        math.floor(xend - frac2 * span),
    )
    win_ends = (
        math.ceil(xstart + frac1 * span),
        xend,
    )

    means: list[np.ndarray] = []
    variances: list[np.ndarray] = []
    for index in range(2):
        segment = _window_mcmc(
            chain, start=win_starts[index], end=win_ends[index]
        )
        matrix = _as_matrix(segment)
        means.append(np.array([_r_mean(matrix[:, col]) for col in range(matrix.shape[1])]))
        spec = _spectrum0_ar_matrix(matrix)
        variances.append(spec / float(niter(segment)))

    with np.errstate(invalid="ignore", divide="ignore"):
        z = (means[0] - means[1]) / np.sqrt(variances[0] + variances[1])
    return GewekeDiag(z=np.asarray(z, dtype=np.float64), frac=np.array([frac1, frac2]))


def _spectrum0_ar_matrix(matrix: np.ndarray) -> np.ndarray:
    ncol = matrix.shape[1]
    spec = np.zeros(ncol, dtype=np.float64)
    for col in range(ncol):
        spec[col] = _spectrum0_ar(matrix[:, col])
    return spec


def _as_matrix(chain: Mcmc) -> np.ndarray:
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _mcmc_time(chain: Mcmc) -> np.ndarray:
    count = niter(chain)
    start = float(chain.start)
    step = float(chain.thin)
    return start + np.arange(count, dtype=np.float64) * step


def _window_mcmc(chain: Mcmc, start=None, end=None) -> Mcmc:
    xstart = float(chain.start)
    xend = float(chain.end)
    xthin = int(round(chain.thin))
    if start is None:
        start = xstart
    else:
        start = float(start)
    if end is None:
        end = xend
    else:
        end = float(end)

    xtime = _mcmc_time(chain)
    ts_eps = float(np.finfo(np.float64).eps) ** 0.75
    if np.all(np.abs(xtime - start) > abs(start) * ts_eps):
        mask = (xtime > start) & ((start + xthin) > xtime)
        start = float(xtime[mask][0])
    if np.all(np.abs(end - xtime) > abs(end) * ts_eps):
        mask = (xtime < end) & ((end - xthin) < xtime)
        end = float(xtime[mask][-1])

    use = np.arange(1, niter(chain) + 1, dtype=np.int64)
    lo = int(math.trunc((start - xstart) / xthin + 1.5))
    hi = int(math.trunc((end - xstart) / xthin + 1.5))
    keep = use[(use >= lo) & (use <= hi)]
    data = _as_matrix(chain)[keep - 1]
    new_start = xstart + xthin * (lo - 1)
    new_end = xstart + xthin * (hi - 1)
    return as_mcmc(data, start=new_start, end=new_end, thin=float(xthin))
