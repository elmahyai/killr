"""Rejection rate for Metropolis--Hastings chains.

Translated from coda 0.19-4.1 ``rejectionRate`` in ``R/rejectionRate.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list


def rejectionRate(x):
    """Fraction of successive iterations with identical values, per variable."""
    if is_mcmc_list(x):
        rates = np.array([_rejection_rate_mcmc(chain) for chain in x.chains])
        if rates.ndim == 1:
            return rates
        return rates.mean(axis=0)
    if is_mcmc(x):
        return _rejection_rate_mcmc(x)
    raise TypeError("rejectionRate expects an mcmc or mcmc.list object")


def _rejection_rate_mcmc(chain):
    matrix = _matrix_mcmc(chain)
    if matrix.shape[0] < 2:
        nvar = matrix.shape[1]
        return np.full(nvar, np.nan, dtype=np.float64)
    same = matrix[:-1, :] == matrix[1:, :]
    return same.mean(axis=0)


def _matrix_mcmc(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data
