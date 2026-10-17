"""Logarithm of the sum of exponentials, from matrixStats `logSumExp`."""

from __future__ import annotations

from logsumexp import logSumExp as _log_sum_exp


def logSumExp(lx, idxs=None, na_rm=False):
    """Accurately compute the logarithm of the sum of exponentials.

    This is ``log(sum(exp(lx)))``. The sum subtracts the maximum of ``lx``
    before exponentiating, which is the matrixStats algorithm. ``idxs`` is
    1-based, as in R; ``None`` uses every element. ``na_rm`` drops missing
    values, the same switch as R's ``na.rm``. A missing double is ``NaN``.
    """
    return _log_sum_exp(lx, idxs, bool(na_rm))
