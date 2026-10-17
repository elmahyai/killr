"""Diagonal autocorrelations for Markov chains.

Translated from coda 0.19-4.1 ``autocorr.diag`` in ``R/autocorrdiag.R``.
"""

from __future__ import annotations

import numpy as np

from coda.as_mcmc import is_mcmc
from coda.as_mcmc_list import is_mcmc_list
from coda.autocorr import autocorr


def autocorr_diag(mcmc_obj, **kwargs):
    """Autocorrelations only on the diagonal (no cross-correlations)."""
    if is_mcmc_list(mcmc_obj):
        return _autocorr_diag_mcmc_list(mcmc_obj, **kwargs)
    if is_mcmc(mcmc_obj):
        return _autocorr_diag_mcmc(mcmc_obj, **kwargs)
    raise TypeError("autocorr_diag expects an mcmc or mcmc.list object")


def _autocorr_diag_mcmc(mcmc_obj, **kwargs):
    ac = autocorr(mcmc_obj, **kwargs)
    return _matrix_from_autocorr(ac)


def _autocorr_diag_mcmc_list(mcmc_obj, **kwargs):
    parts = [_autocorr_diag_mcmc(chain, **kwargs) for chain in mcmc_obj.chains]
    result = np.array(parts[0], dtype=np.float64, copy=True)
    for part in parts[1:]:
        result = result + part
    return result / len(parts)


def _matrix_from_autocorr(ac):
    nlags, nvar, _ = ac.shape
    result = np.full((nlags, nvar), np.nan, dtype=np.float64)
    for index in range(nvar):
        result[:, index] = ac[:, index, index]
    out = AutocorrDiagMatrix(result)
    out.lag_labels = getattr(ac, "lag_labels", None)
    out.varnames = getattr(ac, "varnames", None)
    return out


class AutocorrDiagMatrix(np.ndarray):
    """Two-dimensional diagonal autocorrelation matrix with R-style dimnames."""

    def __new__(cls, array):
        return np.asarray(array, dtype=np.float64).view(cls)

    def __array_finalize__(self, obj):
        if obj is None:
            return
        self.lag_labels = getattr(obj, "lag_labels", None)
        self.varnames = getattr(obj, "varnames", None)
