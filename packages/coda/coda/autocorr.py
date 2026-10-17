"""Autocorrelation function for Markov chains.

Translated from coda 0.19-4.1 ``autocorr`` in ``R/output.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import as_mcmc
from coda.as_mcmc_list import _nvar_mcmc, _varnames_mcmc, is_mcmc_list


def autocorr(x, lags=(0, 1, 5, 10, 50), relative=True):
    """Autocorrelations of an ``mcmc`` object at selected lags.

    For an ``mcmc.list``, returns one array per chain. With ``relative=True``,
    ``lags`` are multiplied by the chain thinning interval before indexing.
    """
    lags = tuple(int(value) for value in lags)
    if is_mcmc_list(x):
        return [autocorr(chain, lags=lags, relative=relative) for chain in x]

    lag_max = max(lags)
    chain = as_mcmc(x)
    thin_val = int(round(chain.thin))
    work_lags = list(lags)
    if relative:
        work_lags = [lag * thin_val for lag in work_lags]
    else:
        if any(lag % thin_val != 0 for lag in work_lags):
            raise ValueError("Lags do not conform to thinning interval")

    niter = _niter_mcmc(chain)
    work_lags = [lag for lag in work_lags if lag < niter * thin_val]

    matrix = _matrix_mcmc(chain)
    acf_out = _acf_correlation(matrix, lag_max)
    indices = [lag // thin_val for lag in work_lags]
    result = acf_out[indices, :, :]

    lag_labels = [f"Lag {lag}" for lag in work_lags]
    varnames = _varnames_mcmc(chain, allow_null=False)
    result = AutocorrArray(
        result,
        lag_labels=lag_labels,
        varnames=varnames,
    )
    return result


class AutocorrArray(np.ndarray):
    """Three-dimensional autocorrelation array with R-style dimnames."""

    def __new__(cls, array, lag_labels=None, varnames=None):
        obj = np.asarray(array, dtype=np.float64).view(cls)
        obj.lag_labels = list(lag_labels) if lag_labels is not None else None
        obj.varnames = list(varnames) if varnames is not None else None
        return obj

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.lag_labels = getattr(obj, "lag_labels", None)
        self.varnames = getattr(obj, "varnames", None)


def _niter_mcmc(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim >= 2:
        return int(data.shape[0])
    return int(data.size)


def _matrix_mcmc(chain):
    data = np.asarray(chain.data, dtype=np.float64)
    if data.ndim == 1:
        return data.reshape(-1, 1)
    return data


def _acf_correlation(matrix, lag_max):
    """``stats::acf`` correlation matrix for a multivariate series."""
    matrix = np.asarray(matrix, dtype=np.float64)
    nobs, nvar = matrix.shape
    centered = matrix - matrix.mean(axis=0)
    acf = np.empty((lag_max + 1, nvar, nvar), dtype=np.float64)
    cov0 = centered.T @ centered / nobs
    scale = np.sqrt(np.diag(cov0))
    with np.errstate(divide="ignore", invalid="ignore"):
        norm = 1.0 / np.outer(scale, scale)
    for lag in range(lag_max + 1):
        segment = centered[lag:]
        partner = centered[: nobs - lag]
        covariance = segment.T @ partner / nobs
        acf[lag, :, :] = covariance * norm
    return acf
