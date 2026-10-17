"""Duplication matrix wrapper, from matrixcalc 1.0-6."""

from __future__ import annotations

from matrixcalc.d_matrix import d_matrix


def duplication_matrix(n=1):
    """Return the duplication matrix that maps ``vech(A)`` to ``vec(A)`` for symmetric ``A``.

    The result has shape ``(n * n, n * (n + 1) // 2)``. This function is a wrapper for
    :func:`matrixcalc.d_matrix.d_matrix`.
    """
    return d_matrix(n)
