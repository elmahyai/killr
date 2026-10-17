"""Row and column standard deviations, ported from matrixStats."""

from __future__ import annotations

import numpy as np

from matrixstats.rowvars import colVars, rowVars

_NA_REAL_BITS = np.uint64(0x7FF00000000007A2)

__all__ = ["rowSds", "colSds"]


def rowSds(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    refine=True,
    center=None,
    dim=None,
    use_names=True,
):
    """Sample standard deviation of each row.

    Mirrors ``matrixStats::rowSds``. It calls :func:`matrixstats.rowvars.rowVars`
    and takes the square root. R's NA from the variance is kept, including its
    bits. Arguments match ``rowVars``.
    """
    return _sqrt_keep_na(
        rowVars(
            x,
            rows=rows,
            cols=cols,
            na_rm=na_rm,
            refine=refine,
            center=center,
            dim=dim,
            use_names=use_names,
        )
    )


def colSds(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    refine=True,
    center=None,
    dim=None,
    use_names=True,
):
    """Sample standard deviation of each column.

    Mirrors ``matrixStats::colSds``. It calls :func:`matrixstats.rowvars.colVars`
    and takes the square root. Arguments match ``colVars``.
    """
    return _sqrt_keep_na(
        colVars(
            x,
            rows=rows,
            cols=cols,
            na_rm=na_rm,
            refine=refine,
            center=center,
            dim=dim,
            use_names=use_names,
        )
    )


def _sqrt_keep_na(variance):
    """Square root that leaves R's NA payload unchanged.

    ``sqrt`` in R returns ``NA_real_`` for ``NA_real_``. NumPy quiets that
    NaN, so the exact bits are copied back.
    """
    variance = np.ascontiguousarray(variance, dtype=np.float64)
    with np.errstate(invalid="ignore"):
        out = np.sqrt(variance)
    na = variance.view(np.uint64) == _NA_REAL_BITS
    if np.any(na):
        out = np.array(out, dtype=np.float64, copy=True)
        out.view(np.uint64)[na] = _NA_REAL_BITS
    return out
