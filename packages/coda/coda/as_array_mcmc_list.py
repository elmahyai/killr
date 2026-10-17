"""Coerce an ``mcmc.list`` to a three-dimensional array.

Translated from coda 0.19-4.1 ``as.array.mcmc.list``.
"""

from __future__ import annotations

import numpy as np


def as_array_mcmc_list(x, drop=True):
    """Stack MCMC chains into an array with dimensions iter, var, and chain.

    ``x`` is a list or tuple of chains (each a vector or matrix with iterations
    in rows). With ``drop=True``, length-one dimensions are removed after
    stacking, matching R ``drop()``.
    """
    chains = _coerce_chains(x)
    nchain = len(chains)
    if nchain == 0:
        raise ValueError("mcmc.list must contain at least one chain")

    first = chains[0]
    niter, nvar = first.shape
    for chain in chains[1:]:
        if chain.shape != (niter, nvar):
            raise ValueError("Chains must have the same number of iterations and variables")

    result = np.empty((niter, nvar, nchain), order="F", dtype=np.float64)
    for index, chain in enumerate(chains):
        result[:, :, index] = chain

    if drop:
        result = np.squeeze(result)
    return result


def _coerce_chains(value):
    if not _is_mcmc_list(value):
        raise TypeError("expected an mcmc.list (a non-empty list of chains)")
    return [_chain_matrix(chain) for chain in value]


def _is_mcmc_list(value):
    if isinstance(value, (str, bytes, np.ndarray)):
        return False
    if not isinstance(value, (list, tuple)) or len(value) == 0:
        return False
    first = value[0]
    if isinstance(first, (bool, np.bool_)):
        return False
    if isinstance(first, (int, float, np.integer, np.floating)):
        return False
    return True


def _chain_matrix(value):
    if hasattr(value, "data") and not isinstance(value, (np.ndarray, list, tuple)):
        value = value.data

    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        matrix = array.reshape(1, 1)
    elif array.ndim == 1:
        matrix = array.reshape(-1, 1)
    elif array.ndim == 2:
        matrix = array
    else:
        raise ValueError("each chain must be a vector or a matrix")

    return matrix
