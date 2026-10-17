"""Batch standard error for MCMC samples.

Translated from coda 0.19-4.1 ``batchSE`` in ``R/batchSE.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list
from coda.niter import niter


def batchSE(x, batchSize=100):
    """Standard error of each column from batch means of an MCMC sample."""
    if is_mcmc_list(x):
        return _batch_se_mcmc_list(x, int(batchSize))
    if is_mcmc(x):
        return _batch_se_mcmc(x, int(batchSize))
    raise TypeError("batchSE expects an mcmc or mcmc.list object")


def _batch_se_mcmc(chain, batch_size):
    n_iter = niter(chain)
    n_batch = n_iter // batch_size
    n_use = n_batch * batch_size
    matrix = _matrix_mcmc(chain)[:n_use, :]
    batch_means = _batch_means(matrix, batch_size, n_batch)
    stds = _batch_stds(batch_means, batch_size, n_batch - 1)
    return stds / np.sqrt(float(n_iter))


def _batch_se_mcmc_list(obj, batch_size):
    n_chain = len(obj.chains)
    n_iter = niter(obj)
    n_batch = n_iter // batch_size
    n_use = n_batch * batch_size
    parts = []
    for chain in obj.chains:
        matrix = _matrix_mcmc(chain)[:n_use, :]
        parts.append(_batch_means(matrix, batch_size, n_batch))
    batch_means = np.vstack(parts)
    stds = _batch_stds(batch_means, batch_size, n_chain * n_batch - 1)
    return stds / np.sqrt(float(n_iter * n_chain))


def _matrix_mcmc(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _batch_means(matrix, batch_size, n_batch):
    reshaped = matrix.reshape(n_batch, batch_size, matrix.shape[1])
    return reshaped.mean(axis=1)


def _batch_stds(batch_means, batch_size, df):
    grand_mean = batch_means.mean(axis=0)
    mi2 = (batch_means - grand_mean) ** 2
    return np.sqrt(mi2.sum(axis=0) * batch_size / df)
