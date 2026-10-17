"""Cross-correlations between MCMC variables.

Translated from coda 0.19-4.1 ``crosscorr`` in ``R/output.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import _varnames_mcmc, is_mcmc_list
from coda.niter import niter


def crosscorr(x):
    """Pearson correlations between variables in MCMC output.

    For an ``mcmc.list``, all chains are stacked before ``cor`` is applied.
    """
    if is_mcmc_list(x):
        matrix = _as_matrix_mcmc_list(x)
        varnames = _varnames_mcmc(x.chains[0], allow_null=False)
    elif is_mcmc(x):
        matrix = _matrix_mcmc(x)
        varnames = _varnames_mcmc(x, allow_null=False)
    else:
        raise TypeError("crosscorr expects an mcmc or mcmc.list object")

    if matrix.shape[1] == 1:
        corr = np.array([[1.0]], dtype=np.float64)
    else:
        corr = np.corrcoef(matrix, rowvar=False)
        corr = _cor_constant_columns(matrix, corr)
    return CrosscorrMatrix(corr, varnames=varnames)


def _cor_constant_columns(matrix, corr):
    """Match ``stats::cor`` when a column has zero sample variance."""
    std = np.std(matrix, axis=0, ddof=1)
    out = np.asarray(corr, dtype=np.float64).copy()
    for index, spread in enumerate(std):
        if spread == 0.0 or not np.isfinite(spread):
            out[index, :] = np.nan
            out[:, index] = np.nan
            out[index, index] = 1.0
    return out


class CrosscorrMatrix(np.ndarray):
    """Correlation matrix with R-style dimnames."""

    def __new__(cls, array, varnames=None):
        obj = np.asarray(array, dtype=np.float64).view(cls)
        obj.varnames = list(varnames) if varnames is not None else None
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.varnames = getattr(obj, "varnames", None)


def _matrix_mcmc(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _as_matrix_mcmc_list(obj):
    n_iter = niter(obj)
    parts = [_matrix_mcmc(chain) for chain in obj.chains]
    return np.vstack(parts)
