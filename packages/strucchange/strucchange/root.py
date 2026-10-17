"""Symmetric matrix square root, from ``root.matrix``."""

import numpy as np


def root_matrix(X):
    """Symmetric square root of a positive semidefinite matrix.

    A 1 by 1 matrix is ``sqrt``. A larger matrix is ``V diag(sqrt(lambda)) V'``
    from the symmetric eigendecomposition. A negative eigenvalue is an error.
    """
    matrix = np.asarray(X, dtype=float)
    if matrix.ndim != 2:
        raise ValueError("root.matrix expects a matrix")
    nrow, ncol = matrix.shape
    if ncol == 1 and nrow == 1:
        return np.sqrt(matrix)
    values, vectors = np.linalg.eigh(matrix, UPLO="L")
    if np.any(values < 0):
        raise ValueError("matrix is not positive semidefinite")
    scaled = vectors * np.sqrt(values)
    return scaled @ vectors.T
