"""Frobenius inner product wrapper, from matrixcalc 1.0-6."""

from __future__ import annotations

import numpy as np

from matrixcalc.hadamard_prod import hadamard_prod


def frobenius_prod(x, y):
    """Return the Frobenius inner product of two numeric matrices or vectors.

    This is the sum of the element-wise Hadamard product of ``x`` and ``y``.
    """
    return np.sum(hadamard_prod(x, y))
