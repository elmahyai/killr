"""Row and column interquartile ranges, ported from matrixStats."""

from __future__ import annotations

import numpy as np

from matrixstats.rowquantiles import _NA_INTEGER, _Result, colQuantiles, rowQuantiles

__all__ = ["rowIQRs", "colIQRs"]

_PROBS = np.array([0.25, 0.75], dtype=np.float64)


def rowIQRs(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    use_names=True,
    type=7,
    digits=7,
    fuzz=None,
):
    """Interquartile range of each row.

    Mirrors ``matrixStats::rowIQRs``. The value is the 0.75 quantile minus
    the 0.25 quantile from :func:`matrixstats.rowquantiles.rowQuantiles`.
    A row with a missing value is ``nan`` when ``na_rm`` is false.
    """
    quantiles = rowQuantiles(
        x,
        rows=rows,
        cols=cols,
        probs=_PROBS,
        na_rm=na_rm,
        type=type,
        digits=digits,
        use_names=use_names,
        drop=False,
        fuzz=fuzz,
    )
    return _difference(quantiles, use_names)


def colIQRs(
    x,
    rows=None,
    cols=None,
    na_rm=False,
    use_names=True,
    type=7,
    digits=7,
    fuzz=None,
):
    """Interquartile range of each column.

    Mirrors ``matrixStats::colIQRs``. Arguments match :func:`rowIQRs`.
    """
    quantiles = colQuantiles(
        x,
        rows=rows,
        cols=cols,
        probs=_PROBS,
        na_rm=na_rm,
        type=type,
        digits=digits,
        use_names=use_names,
        drop=False,
        fuzz=fuzz,
    )
    return _difference(quantiles, use_names)


def _difference(quantiles, use_names):
    array = np.asarray(quantiles)
    # An integer quantile matrix is the untouched NA allocation: every
    # entry is R's integer NA, and NA minus NA stays that sentinel.
    if np.issubdtype(array.dtype, np.integer):
        gap = np.full(array.shape[0], _NA_INTEGER, dtype=np.int32)
    else:
        gap = np.asarray(array, dtype=np.float64)[:, 1] - np.asarray(array, dtype=np.float64)[:, 0]
    names = quantiles.rownames if use_names else None
    return _Result(gap, names=names)
