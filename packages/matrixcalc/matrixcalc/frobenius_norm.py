"""Frobenius matrix norm wrapper, from matrixcalc 1.0-6."""

from __future__ import annotations

from matrixcalc.entrywise_norm import entrywise_norm


def frobenius_norm(x):
    """Return the Frobenius norm of a numeric vector or matrix.

    This is the entrywise norm with exponent ``2``.
    """
    return entrywise_norm(x, 2)
