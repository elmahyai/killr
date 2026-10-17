"""R ``unchol``: rebuild a covariance from a triangular Cholesky factor."""

from __future__ import annotations

import numpy as np
from mclustbootstraplrt import uncholf


def _r_diag(values: np.ndarray) -> np.ndarray:
    """R ``diag`` on the vector of squared diagonal entries."""
    values = np.asarray(values, dtype=float).reshape(-1)
    if values.size != 1:
        return np.diag(values)
    number = float(values[0])
    if not np.isfinite(number) or abs(number) > np.iinfo(np.int32).max:
        raise ValueError("invalid 'nrow' value (too large or NA)")
    n = int(number)
    if n < 0:
        raise ValueError("invalid 'nrow' value (too large or NA)")
    return np.eye(n, dtype=float)


def unchol(x, upper=None):
    """Match ``mclust:::unchol``. ``upper=None`` detects which triangle is present."""
    mat = np.asarray(x, dtype=float)
    if mat.ndim != 2:
        raise ValueError("x must be a matrix")
    if upper is None:
        rows, cols = np.indices(mat.shape)
        upper_nz = bool(np.any(mat[rows < cols] != 0))
        lower_nz = bool(np.any(mat[rows > cols] != 0))
        if upper_nz and lower_nz:
            raise ValueError("not a triangular matrix")
        if not upper_nz and not lower_nz:
            return _r_diag(np.diag(mat) ** 2)
        upper = upper_nz
    rebuilt = uncholf(bool(upper), np.asarray(mat, dtype=np.float64))
    return np.asarray(rebuilt, dtype=float)
