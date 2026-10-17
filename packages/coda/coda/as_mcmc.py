"""Coerce objects to MCMC series.

Translated from coda 0.19-4.1 ``as.mcmc`` and ``as.mcmc.default`` (via ``mcmc``).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

@dataclass
class Mcmc:
    """One MCMC chain: iterations in rows, variables in columns (or a vector)."""

    data: np.ndarray
    start: float = 1.0
    end: float = 0.0
    thin: float = 1.0

    @property
    def mcpar(self):
        return np.array([self.start, self.end, self.thin], dtype=np.float64)


def is_mcmc(x):
    """Return True when ``x`` is an ``Mcmc`` object with at most two dimensions."""
    if not isinstance(x, Mcmc):
        return False
    array = np.asarray(x.data)
    if array.ndim == 3:
        raise ValueError(
            "Obsolete mcmc object\nUpdate with a command like\nx <- mcmcUpgrade(x)"
        )
    return True


def as_mcmc(x, **kwargs):
    """Coerce ``x`` to an ``Mcmc`` object (``as.mcmc.default``)."""
    if is_mcmc(x):
        return x
    return mcmc(x, **kwargs)


def mcmc(data=None, start=None, end=None, thin=1):
    """Build an ``Mcmc`` chain (``mcmc`` in coda 0.19-4.1)."""
    if data is None:
        data = np.array([np.nan], dtype=np.float64)

    matrix, is_vector = _coerce_data(data)

    thin_val = int(round(thin))
    if start is not None and np.size(start) > 1:
        raise ValueError("Invalid start")
    if end is not None and np.size(end) > 1:
        raise ValueError("Invalid end")
    if np.size(thin_val) != 1:
        raise ValueError("Invalid thin")

    niter = matrix.shape[0]

    if end is None:
        start_val = 1.0 if start is None else float(start)
        end_val = start_val + (niter - 1) * thin_val
    else:
        end_val = float(end)
        if start is None:
            start_val = end_val - (niter - 1) * thin_val
        else:
            start_val = float(start)

    nobs = int(np.floor((end_val - start_val) / thin_val + 1.0))
    if niter < nobs:
        raise ValueError("Start, end and thin incompatible with data")

    end_val = start_val + thin_val * (nobs - 1)
    if nobs < niter:
        matrix = matrix[:nobs, ...]

    if is_vector and matrix.shape[1] == 1:
        stored = matrix[:, 0]
    else:
        stored = matrix

    return Mcmc(data=stored, start=start_val, end=end_val, thin=float(thin_val))


def _coerce_data(data):
    if hasattr(data, "data") and not isinstance(data, (np.ndarray, list, tuple)):
        data = data.data

    if isinstance(data, dict):
        columns = list(data.values())
        if not columns:
            raise ValueError("Data frame contains non-numeric values")
        if not all(_is_numeric_column(col) for col in columns):
            raise ValueError("Data frame contains non-numeric values")
        matrix = np.column_stack([np.asarray(col, dtype=np.float64).reshape(-1) for col in columns])
        return matrix, False

    array = np.asarray(data, dtype=np.float64)
    if array.ndim == 0:
        return array.reshape(1, 1), False
    if array.ndim == 1:
        return array.reshape(-1, 1), True
    if array.ndim == 2:
        return array, False
    raise ValueError("mcmc data must be a vector or a matrix")


def _is_numeric_column(values):
    array = np.asarray(values)
    return np.issubdtype(array.dtype, np.number)
