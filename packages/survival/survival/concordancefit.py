"""Working routine behind concordance (survival::concordancefit)."""

from __future__ import annotations

from typing import Any

import numpy as np

from survival.concordance import _concordancefit
from survival.surv import Surv, SurvObject, is_Surv


def _coerce_response(y: Any) -> SurvObject:
    if is_Surv(y):
        return y
    if isinstance(y, (list, tuple, np.ndarray)):
        flat = np.asarray(y, dtype=float).reshape(-1)
        if flat.ndim == 1:
            return Surv(flat)
    raise ValueError(
        "left hand side of the formula must be a numeric vector, "
        "survival object, or an orderable factor"
    )


def _apply_matched_strata_trick(
    y: SurvObject,
    strata: np.ndarray,
    *,
    timewt: str,
    nstrat: int,
    keepstrata: bool,
    nvar: int,
) -> tuple[SurvObject, np.ndarray, int]:
    if nvar > 1 or nstrat == 1:
        keepstrata = False
    if timewt not in ("n", "I") or nstrat <= 10 or keepstrata:
        return y, strata, nstrat

    surv = np.asarray(y.columns, dtype=float)
    n = surv.shape[0]
    ny = surv.shape[1]
    _, stemp = np.unique(strata, return_inverse=True)

    if ny == 3:
        delta = 2 + np.max(surv[:, 1]) - np.min(surv[:, 0])
        surv[:, 0] = surv[:, 0] + stemp * delta
        surv[:, 1] = surv[:, 1] + stemp * delta
        y = SurvObject(surv, y.type, states=y.states, clabel=y.clabel)
    else:
        delta = np.max(surv[:, 0]) + 2
        m1 = np.full(n, -1.0)
        start = m1 + stemp * delta
        stop = surv[:, 0] + stemp * delta
        event = surv[:, 1]
        y = Surv(start, stop, event, type="counting")
    strata = np.ones(n, dtype=int)
    return y, strata, 1


def concordancefit(
    y,
    x,
    strata=None,
    weights=None,
    ymin=None,
    ymax=None,
    timewt="n",
    cluster=None,
    influence=0,
    ranks=False,
    reverse=False,
    timefix=True,
    keepstrata=10,
    std_err=True,
):
    """Compute concordance from a response and predictor with minimal checking."""
    xarr = np.asarray(x, dtype=float)
    if np.any(np.isnan(xarr)):
        return None

    y = _coerce_response(y)
    if np.any(np.isnan(np.asarray(y.columns, dtype=float))):
        return None

    if ymin is not None and not np.isscalar(ymin):
        raise ValueError("ymin must be numeric")
    if ymax is not None and not np.isscalar(ymax):
        raise ValueError("ymax must be numeric")
    if ymin is not None:
        ymin = float(ymin)
    if ymax is not None:
        ymax = float(ymax)

    if not std_err:
        ranks = False
        influence = 0

    n = len(y)
    xmat = np.atleast_2d(xarr)
    if xmat.shape[0] == 1 and n > 1:
        xmat = xmat.reshape(n, -1)
    elif xmat.shape[0] != n:
        raise ValueError("x and y are not the same length")
    nvar = xmat.shape[1]

    if strata is None or len(strata) == 0:
        strata_arr = np.ones(n, dtype=int)
    else:
        strata_arr = np.asarray(strata)
        if len(strata_arr) != n:
            raise ValueError("y and strata are not the same length")

    nstrat = len(np.unique(strata_arr))
    if isinstance(keepstrata, (bool, np.bool_)):
        keep = bool(keepstrata)
    elif isinstance(keepstrata, (int, float, np.integer, np.floating)):
        keep = nstrat <= int(keepstrata)
    else:
        raise ValueError("keepstrata argument must be logical or numeric")

    y, strata_arr, nstrat = _apply_matched_strata_trick(
        y,
        strata_arr,
        timewt=timewt,
        nstrat=nstrat,
        keepstrata=keep,
        nvar=nvar,
    )

    return _concordancefit(
        y,
        xmat,
        strata=strata_arr,
        weights=weights,
        ymin=ymin,
        ymax=ymax,
        timewt=timewt,
        cluster=cluster,
        influence=influence,
        ranks=ranks,
        reverse=reverse,
        timefix=timefix,
        keepstrata=keepstrata,
        std_err=std_err,
    )
