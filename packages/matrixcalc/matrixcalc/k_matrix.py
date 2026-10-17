"""Commutation matrix K via H matrices, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.h_matrices import h_matrices


def k_matrix(r, c=None):
    """Return the commutation matrix of order r * c.

    For an r by c matrix ``A``, this matrix ``K`` satisfies
    ``K @ vec(A) == vec(A.T)`` with column-major vectorization like R.

    The matrix is built as the sum of Kronecker products
    ``H[i,j] ⊗ H[i,j].T`` from :func:`matrixcalc.h_matrices.h_matrices`.
    """
    if c is None:
        c = r
    h = h_matrices(r, c)
    r_dim = len(h)
    c_dim = len(h[0])
    p = r_dim * c_dim
    matrix = np.zeros((p, p), dtype=float)
    for i in range(r_dim):
        for j in range(c_dim):
            hij = h[i][j]
            matrix += np.kron(hij, hij.T)
    return matrix
