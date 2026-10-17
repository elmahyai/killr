"""Effective sample size for an MCMC series.

Translated from coda 0.19-4.1. ``spectrum0.ar`` fits a straight line in the
iteration index and returns a spectral density of zero when that residual
standard deviation is within R's ``all.equal`` tolerance of zero. Any other
column uses the Yule-Walker autoregression selected by AIC. An ``mcmc.list``
is a list of chains, and the sizes are summed across those chains.
"""

from __future__ import annotations

import math

import numpy as np

from coda.spectrum0_ar import _r_mean, _spectrum0_ar


def effectiveSize(x):
    """Effective sample size of each column of an MCMC series.

    ``x`` is one chain: a vector, or a matrix with one row per iteration and
    one column per variable. A list or tuple whose elements are themselves
    series is an ``mcmc.list``, and the sizes are summed across chains.
    """
    if _is_mcmc_list(x):
        rows = [_one_chain(chain) for chain in x]
        width = rows[0].size
        for row in rows[1:]:
            if row.size != width:
                raise ValueError("Different number of variables in each chain")
        return np.sum(np.vstack(rows), axis=0)
    return _one_chain(x)


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


def _one_chain(value):
    matrix = _as_matrix(value)
    if matrix.shape[1] == 0:
        raise ValueError("matrix has no columns")
    result = np.empty(matrix.shape[1], dtype=np.float64)
    for column in range(matrix.shape[1]):
        result[column] = _column_size(matrix[:, column])
    return result


def _as_matrix(value):
    array = np.asarray(value, dtype=np.float64)
    if array.ndim == 0:
        return array.reshape(1, 1)
    if array.ndim == 1:
        return array.reshape(-1, 1)
    if array.ndim == 2:
        return array
    raise ValueError("effectiveSize expects a vector, a matrix, or a list of chains")


def _column_size(series):
    spec = _spectrum0_ar(series)
    if spec == 0.0:
        return 0.0
    variance = _sample_variance(series)
    return series.size * variance / spec


def _sample_variance(series):
    n = series.size
    if n < 2:
        return math.nan
    center = _r_mean(series)
    total = np.longdouble(0)
    for value in series:
        delta = np.longdouble(value) - np.longdouble(center)
        total += delta * delta
    return float(total / (n - 1))


