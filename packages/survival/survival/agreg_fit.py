"""Counting-process Cox fit (survival::agreg.fit).

The Newton iteration is the Rust crate agfit4 (survival src/agfit4.c), and
the martingale residuals are the same crate (src/agmart3.c). This module does
the R glue: dropping rows that span no death, 0-based sort indexes, the null
model, centering flags, and the output list.
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from agfit4 import agfit4 as _agfit4
from agfit4 import agmart3 as _agmart3


def _center_flags(x: np.ndarray, nocenter: Any) -> np.ndarray:
    """1 centers the column. A column whose values all lie in nocenter stays put.

    A missing nocenter matches R's ``z %in% NULL``, which never holds, so every
    column is centered.
    """
    nvar = x.shape[1]
    if nocenter is None:
        return np.ones(nvar, dtype=np.int32)
    allowed = np.atleast_1d(np.asarray(nocenter, dtype=float))
    zero_one = np.array(
        [bool(np.all(np.isin(x[:, j], allowed))) for j in range(nvar)],
        dtype=bool,
    )
    return np.where(zero_one, 0, 1).astype(np.int32)


def _as_strata(strata: Any) -> np.ndarray:
    arr = np.asarray(strata)
    if arr.dtype.kind in "iuf":
        return np.ascontiguousarray(np.trunc(arr.astype(float)).astype(np.int32))
    levels = sorted(set(arr.reshape(-1).tolist()))
    code = {level: i + 1 for i, level in enumerate(levels)}
    return np.array([code[value] for value in arr.reshape(-1).tolist()], dtype=np.int32)


def agreg_fit(
    x: Any,
    y: Any,
    strata: Any,
    offset: Any,
    init: Any,
    control: dict[str, Any],
    weights: Any,
    method: str,
    rownames: Any,
    resid: bool = True,
    nocenter: Any = None,
) -> dict[str, Any]:
    """Fit a Cox model on (start, stop] data with Breslow or Efron ties."""
    del rownames
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 1:
        y_arr = y_arr.reshape(-1, 1)
    n = y_arr.shape[0]
    status = y_arr[:, 2]
    if np.all(status == 0):
        raise ValueError("Can't fit a Cox model with 0 failures")
    if offset is None:
        offset_arr = np.zeros(n, dtype=float)
    else:
        offset_arr = np.asarray(offset, dtype=float).reshape(-1)
    if weights is None:
        weights_arr = np.ones(n, dtype=float)
    else:
        weights_arr = np.asarray(weights, dtype=float).reshape(-1)
        if np.any(weights_arr <= 0):
            raise ValueError("Invalid weights, must be >0")

    start = y_arr[:, 0]
    stop = y_arr[:, 1]
    if strata is None or np.size(strata) == 0:
        y1 = start
        y2 = stop
        strata_i = None
    else:
        strata_i = _as_strata(strata)
        span = 1.0 + float(np.max(stop) - np.min(start))
        delta = strata_i.astype(float) * span
        y1 = start + delta
        y2 = stop + delta
    occurred = status > 0
    dtime = np.unique(y2[occurred])
    indx1 = np.searchsorted(dtime, y1, side="right")
    indx2 = np.searchsorted(dtime, y2, side="right")
    ignore = indx1 == indx2
    nused = int(np.sum(~ignore))
    ignore_key = ignore.astype(np.int32)
    if strata_i is None:
        sort_end = np.lexsort((-stop, ignore_key)).astype(np.int32)
        sort_start = np.lexsort((-start, ignore_key)).astype(np.int32)
        strata_i = np.zeros(n, dtype=np.int32)
    else:
        sort_end = np.lexsort((-stop, strata_i, ignore_key)).astype(np.int32)
        sort_start = np.lexsort((-start, strata_i, ignore_key)).astype(np.int32)

    x_arr = np.asarray(x, dtype=float)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(-1, 1)
    nvar = x_arr.shape[1] if x_arr.ndim == 2 else 0
    if nvar == 0:
        x_work = np.arange(1, n + 1, dtype=float).reshape(n, 1)
        maxiter = 0
        nullmodel = True
        if init is not None and np.size(init) != 0:
            raise ValueError("Wrong length for inital values")
        init_arr = np.zeros(1, dtype=float)
        nvar = 1
    else:
        x_work = x_arr
        nullmodel = False
        maxiter = int(control["iter.max"])
        if init is None:
            init_arr = np.zeros(nvar, dtype=float)
        else:
            init_arr = np.asarray(init, dtype=float).reshape(-1)
            if init_arr.size != nvar:
                raise ValueError("Wrong length for inital values")

    doscale = _center_flags(x_work, nocenter)
    zero_one = doscale == 0
    y_work = np.ascontiguousarray(np.column_stack([start, stop, status]), dtype=float)
    coef, u, vmat, loglik, sctest, flag, iter_ = _agfit4(
        nused,
        y_work,
        np.ascontiguousarray(x_work, dtype=float),
        np.ascontiguousarray(strata_i, dtype=np.int32),
        np.ascontiguousarray(weights_arr, dtype=float),
        np.ascontiguousarray(offset_arr, dtype=float),
        np.ascontiguousarray(init_arr, dtype=float),
        np.ascontiguousarray(sort_start, dtype=np.int32),
        np.ascontiguousarray(sort_end, dtype=np.int32),
        1 if method == "efron" else 0,
        maxiter,
        float(control["eps"]),
        float(control["toler.chol"]),
        np.ascontiguousarray(doscale, dtype=np.int32),
    )
    coef = np.asarray(coef, dtype=float).copy()
    u_arr = np.asarray(u, dtype=float)
    vmat = np.asarray(vmat, dtype=float)
    loglik_arr = np.asarray(loglik, dtype=float)
    flag_arr = np.asarray(flag, dtype=np.int32)
    agmeans = np.where(zero_one, 0.0, x_work.mean(axis=0))

    if int(flag_arr[0]) < nvar:
        which_sing = np.diag(vmat) == 0
    else:
        which_sing = np.zeros(nvar, dtype=bool)
    if maxiter > 1:
        infs = np.abs(u_arr @ vmat)
        if not np.all(np.isfinite(coef)) or not np.all(np.isfinite(vmat)):
            raise RuntimeError(
                "routine failed due to numeric overflow."
                "This should never happen.  Please contact the author."
            )
        if int(flag_arr[3]) > 0:
            warnings.warn("Ran out of iterations and did not converge", stacklevel=2)
        else:
            bad = (~np.isfinite(u_arr)) | (
                infs > float(control["toler.inf"]) * (1.0 + np.abs(coef))
            )
            if np.any(bad):
                which = ",".join(str(i + 1) for i in np.flatnonzero(bad))
                warnings.warn(
                    f"Loglik converged before variable  {which} ; beta may be infinite. ",
                    stacklevel=2,
                )

    lp = np.asarray(x_work @ coef + offset_arr - float(np.sum(coef * agmeans)), dtype=float)
    residuals = None
    if resid:
        if np.any(lp > np.log(np.finfo(float).max)):
            temp = lp + np.log(np.finfo(float).max) - (1.0 + float(np.max(lp)))
            score = np.exp(temp)
        else:
            score = np.exp(lp)
        residuals = np.asarray(
            _agmart3(
                nused,
                y_work,
                np.ascontiguousarray(score, dtype=float),
                np.ascontiguousarray(weights_arr, dtype=float),
                np.ascontiguousarray(strata_i, dtype=np.int32),
                np.ascontiguousarray(sort_start, dtype=np.int32),
                np.ascontiguousarray(sort_end, dtype=np.int32),
                1 if method == "efron" else 0,
            ),
            dtype=float,
        )

    if nullmodel:
        out: dict[str, Any] = {
            "loglik": np.float64(loglik_arr[1]),
            "linear.predictors": offset_arr,
            "method": method,
            "class_": ("coxph.null", "coxph"),
        }
        if resid:
            out["residuals"] = residuals
        return out

    if maxiter > 0:
        coef = coef.copy()
        coef[which_sing] = np.nan
    out = {
        "coefficients": coef,
        "var": vmat,
        "loglik": loglik_arr,
        "score": float(sctest),
        "iter": int(iter_),
        "linear.predictors": lp,
        "means": np.asarray(agmeans, dtype=float),
        "first": u_arr,
        "info": flag_arr,
        "method": method,
        "class_": ("coxph",),
    }
    if resid:
        out["residuals"] = residuals
    return out
