"""Deprecated concordance fitter (survival::survConcordance.fit).

R keeps this routine for old code. It computes the concordance counts with
the heap-order tree ranks ``btree``. The two C kernels ``Cconcordance1``
(right-censored) and ``Cconcordance2`` (counting process) are the survconc
crate, loaded from ``crates/survconc`` (survival 3.8-12 ``src/concordance1.c``).
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from survconc import concordance1, concordance2

from survival.strata import StrataFactor
from survival.surv import SurvObject, is_Surv


def _btree(n: int) -> np.ndarray:
    """Heap-order tree ranks (1-based) for ``n`` distinct risk values."""
    ranks = np.zeros(n, dtype=np.int64)
    if n < 1:
        return ranks
    yet_to_do = np.arange(n)
    depth = n.bit_length() - 1  # floor(logb(n, 2))
    start = 1 << depth
    lastrow_length = 1 + n - start
    indx = np.arange(0, 2 * lastrow_length, 2)
    ranks[yet_to_do[indx]] = start + np.arange(indx.size)
    yet_to_do = np.delete(yet_to_do, indx)
    while start > 1:
        start //= 2
        indx = np.arange(0, 2 * start, 2)
        indx = indx[indx < yet_to_do.size]
        ranks[yet_to_do[indx]] = start + np.arange(indx.size)
        yet_to_do = np.delete(yet_to_do, indx)
    return ranks


def _concordance1(y: np.ndarray, wt: np.ndarray, indx: np.ndarray, ntree: int) -> np.ndarray:
    """Cconcordance1 from the survconc crate.

    ``y`` rows are sorted by time, then by -status. ``indx`` is 0-based.
    """
    return np.asarray(
        concordance1(
            np.ascontiguousarray(y, dtype=np.float64),
            np.ascontiguousarray(wt, dtype=np.float64),
            np.ascontiguousarray(indx, dtype=np.int32),
            int(ntree),
        ),
        dtype=float,
    )


def _concordance2(
    y: np.ndarray,
    wt: np.ndarray,
    indx: np.ndarray,
    ntree: int,
    sort_stop: np.ndarray,
    sort_start: np.ndarray,
) -> np.ndarray:
    """Cconcordance2 from the survconc crate for (start, stop] data.

    ``y`` is (start, stop, status) in original row order. Sort indices are 0-based.
    """
    return np.asarray(
        concordance2(
            np.ascontiguousarray(y, dtype=np.float64),
            np.ascontiguousarray(wt, dtype=np.float64),
            np.ascontiguousarray(indx, dtype=np.int32),
            int(ntree),
            np.ascontiguousarray(sort_stop, dtype=np.int32),
            np.ascontiguousarray(sort_start, dtype=np.int32),
        ),
        dtype=float,
    )


def _docount(stime: np.ndarray, risk: np.ndarray, wts: np.ndarray, surv_type: str) -> np.ndarray:
    """Concordance counts for one set of rows (R's inner ``docount``)."""
    if surv_type == "right":
        # order(stime[,1], -stime[,2])
        ord_idx = np.lexsort((-stime[:, 1], stime[:, 0]))
        ux = np.sort(np.unique(risk))
        n2 = ux.size
        ranks = _btree(n2)
        index = ranks[np.searchsorted(ux, risk[ord_idx])] - 1
        return _concordance1(stime[ord_idx], wts[ord_idx], index.astype(int), n2)
    if surv_type == "counting":
        # order(-stime[,2], stime[,3]) and order(-stime[,1])
        sort_stop = np.lexsort((stime[:, 2], -stime[:, 1]))
        sort_start = np.argsort(-stime[:, 0], kind="stable")
        ux = np.sort(np.unique(risk))
        n2 = ux.size
        ranks = _btree(n2)
        index = ranks[np.searchsorted(ux, risk)] - 1
        return _concordance2(stime, wts, index.astype(int), n2, sort_stop, sort_start)
    raise ValueError("Invalid survival type for concordance")


def _strata_labels(strata: Any) -> tuple[list[Any], list[Any]]:
    """Per-row labels (None for NA) and the factor levels in R order."""
    if isinstance(strata, StrataFactor):
        labels = [None if c is None else strata.levels[c - 1] for c in strata.codes]
        return labels, list(strata.levels)
    values = list(np.asarray(strata, dtype=object).reshape(-1))
    labels = [None if (v is None or (isinstance(v, float) and math.isnan(v))) else v for v in values]
    present = sorted({v for v in labels if v is not None})
    return labels, present


def survConcordance_fit(y, x, strata=None, weight=None):
    """Concordance counts from a survival object and a predictor (deprecated).

    Returns the vector ``(concordant, discordant, tied.risk, tied.time,
    std(c-d))`` when there are no strata. With strata it returns a matrix with
    one row per used stratum level, in factor-level order.
    """
    warnings.warn(
        "'survConcordance.fit' is deprecated.\nUse 'concordancefit' instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not is_Surv(y) and not isinstance(y, SurvObject):
        raise ValueError("y must be a survival object")
    xarr = np.asarray(x, dtype=float).reshape(-1)
    stime = np.asarray(y.columns, dtype=float)
    if np.any(np.isnan(xarr)) or np.any(np.isnan(stime)):
        return None

    n = xarr.size
    if weight is None or len(weight) == 0:
        wts = np.ones(n, dtype=float)
    else:
        wts = np.asarray(weight, dtype=float).reshape(-1)

    surv_type = y.type
    if surv_type == "right" and stime.shape[1] != 2:
        raise ValueError("Invalid survival type for concordance")

    if strata is None or len(strata) == 0:
        count = _docount(stime, xarr, wts, surv_type)
        if count[0] == 0 and count[1] == 0:
            count[4] = 0.0
        else:
            count[4] = 2.0 * math.sqrt(count[4])
        return count

    labels, levels_order = _strata_labels(strata)
    label_arr = np.array([None if v is None else v for v in labels], dtype=object)
    used = [lev for lev in levels_order if np.any(np.array([v == lev for v in labels], dtype=bool))]
    count = np.zeros((len(used), 5), dtype=float)
    for i, level in enumerate(used):
        keep = np.array([v is not None and v == level for v in label_arr], dtype=bool)
        keep_idx = np.where(keep)[0]
        count[i, :] = _docount(stime[keep_idx], xarr[keep_idx], wts[keep_idx], surv_type)
    zero_pairs = count[:, 0] + count[:, 1] == 0
    count[:, 4] = 2.0 * np.sqrt(np.where(zero_pairs, 0.0, count[:, 4]))
    return count
