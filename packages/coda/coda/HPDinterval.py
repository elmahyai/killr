"""Highest Posterior Density intervals for MCMC samples.

Translated from coda 0.19-4.1 ``HPDinterval.mcmc`` and ``HPDinterval.mcmc.list``.
"""

from __future__ import annotations

import numpy as np


class HPDResult:
    """HPD interval endpoints for one MCMC chain."""

    __slots__ = ("lower", "upper", "rownames", "probability")

    def __init__(self, lower, upper, rownames=None, probability=None):
        self.lower = np.asarray(lower, dtype=np.float64)
        self.upper = np.asarray(upper, dtype=np.float64)
        self.rownames = list(rownames) if rownames is not None else None
        self.probability = float(probability) if probability is not None else None

    def as_matrix(self):
        """Return a (nparam, 2) array with columns lower and upper."""
        return np.column_stack((self.lower, self.upper))


def HPDinterval(obj, prob=0.95):
    """Shortest empirical interval with nominal probability ``prob`` per parameter.

    ``obj`` is one chain as a vector or a matrix with iterations in rows, or a
    list of chains as in an ``mcmc.list``. A list returns one result per chain.
    """
    if _is_mcmc_list(obj):
        return [HPDinterval(chain, prob) for chain in obj]
    return _hpd_mcmc(obj, prob)


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


def _hpd_mcmc(obj, prob):
    matrix, rownames = _as_matrix_with_names(obj)
    if matrix.shape[0] <= 1:
        raise ValueError("obj must have nsamp > 1")

    vals = np.sort(matrix, axis=0)
    nsamp, npar = vals.shape
    gap = int(max(1, min(nsamp - 1, round(nsamp * prob))))
    init = np.arange(nsamp - gap, dtype=np.intp)
    widths = vals[init + gap, :] - vals[init, :]
    inds = np.argmin(widths, axis=0)
    cols = np.arange(npar, dtype=np.intp)
    lower = vals[inds, cols]
    upper = vals[inds + gap, cols]
    return HPDResult(lower, upper, rownames=rownames, probability=gap / nsamp)


def _as_matrix_with_names(value):
    if isinstance(value, np.ndarray) and value.dtype.names is not None:
        names = list(value.dtype.names)
        matrix = np.column_stack([value[name] for name in names])
        return matrix.astype(np.float64, copy=False), names

    param_names = None
    if hasattr(value, "colnames") and getattr(value, "colnames") is not None:
        param_names = [str(name) for name in value.colnames]

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
        raise ValueError("HPDinterval expects a vector, a matrix, or a list of chains")

    if param_names is None and hasattr(value, "columns"):
        try:
            param_names = [str(c) for c in value.columns]
        except TypeError:
            param_names = None

    if param_names is not None and len(param_names) != matrix.shape[1]:
        param_names = None

    return matrix, param_names
