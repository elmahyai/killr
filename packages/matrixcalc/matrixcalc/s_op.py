"""Direct-sum operator, from matrixcalc 1.0-6."""

from __future__ import annotations

from matrixcalc.direct_sum import direct_sum


def s_op(x, y):
    """Return the block-diagonal direct sum of two numeric vectors or matrices.

    This is the infix operator ``%s%``. Each vector is promoted to a column
    matrix, as R ``matrix(x)`` does.
    """
    return direct_sum(x, y)
