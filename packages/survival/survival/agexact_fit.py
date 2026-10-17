"""Exact Cox partial likelihood for counting-process data (survival::agexact.fit).

The Newton iteration is the Rust crate agexact (survival src/agexact.c), and
the martingale residuals are the same crate (src/agmart.c). This module does
the R glue: sorting by strata, stop time, and status, centering flags, and
the output list. The method argument is accepted and ignored; residuals are
always the Breslow form (agmart method 0), and the returned method is "coxph".
"""

from __future__ import annotations

import warnings
from typing import Any

import numpy as np

from agexact import agexact as _agexact
from agexact import agmart as _agmart


def _center_flags(x: np.ndarray, nocenter: Any) -> np.ndarray:
    """1 centers the column. A column whose values all lie in nocenter stays put."""
    nvar = x.shape[1]
    if nocenter is None:
        return np.ones(nvar, dtype=np.int32)
    allowed = np.atleast_1d(np.asarray(nocenter, dtype=float))
    zero_one = np.array(
        [bool(np.all(np.isin(x[:, j], allowed))) for j in range(nvar)],
        dtype=bool,
    )
    return np.where(zero_one, 0, 1).astype(np.int32)


def _warn_infinite(infs: np.ndarray) -> None:
    which = ",".join(str(i + 1) for i in np.flatnonzero(infs))
    warnings.warn(
        f"Loglik converged before variable  {which} ; beta may be infinite. ",
        stacklevel=3,
    )


def agexact_fit(
    x: Any,
    y: Any,
    strata: Any,
    offset: Any,
    init: Any,
    control: dict[str, Any],
    weights: Any,
    method: Any,
    rownames: Any,
    resid: bool = True,
    nocenter: Any = None,
) -> dict[str, Any]:
    """Fit an exact Cox model. Case weights other than 1 are rejected."""
    del method, rownames
    x_mat = np.asarray(x, dtype=float)
    if x_mat.ndim != 2:
        raise ValueError("Invalid formula for cox fitting function")
    n, nvar = x_mat.shape
    if weights is not None and np.any(np.asarray(weights, dtype=float).reshape(-1) != 1):
        raise ValueError("Case weights are not supported for the exact method")
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 1:
        y_arr = y_arr.reshape(-1, 1)
    if y_arr.shape[1] == 3:
        start = y_arr[:, 0]
        stop = y_arr[:, 1]
        event = y_arr[:, 2]
    else:
        start = np.zeros(n, dtype=float)
        stop = y_arr[:, 0]
        event = y_arr[:, 1]

    if strata is None or np.size(strata) == 0:
        sorted_idx = np.lexsort((-event, stop))
        newstrat = np.zeros(n, dtype=np.int32)
    else:
        strata_arr = np.asarray(strata, dtype=float).reshape(-1)
        sorted_idx = np.lexsort((-event, stop, strata_arr))
        strata_sorted = strata_arr[sorted_idx]
        newstrat = np.ones(n, dtype=np.int32)
        if n > 1:
            newstrat[:-1] = (np.diff(strata_sorted) != 0).astype(np.int32)

    if offset is None:
        offset_arr = np.zeros(n, dtype=float)
    else:
        offset_arr = np.asarray(offset, dtype=float).reshape(-1)
    if init is not None:
        init_arr = np.asarray(init, dtype=float).reshape(-1)
        if init_arr.size != nvar:
            raise ValueError("Wrong length for inital values")
    else:
        init_arr = np.zeros(nvar, dtype=float)
    if nvar == 0:
        raise ValueError("Cannot handle a null model + exact calculation (yet)")

    flags = _center_flags(x_mat, nocenter)
    beta, u, imat, means, loglik, sctest, flag, iter_, _elapsed = _agexact(
        int(control["iter.max"]),
        np.ascontiguousarray(start[sorted_idx], dtype=float),
        np.ascontiguousarray(stop[sorted_idx], dtype=float),
        np.ascontiguousarray(np.trunc(event[sorted_idx]), dtype=np.int32),
        np.ascontiguousarray(x_mat[sorted_idx, :], dtype=float),
        np.ascontiguousarray(offset_arr[sorted_idx], dtype=float),
        np.ascontiguousarray(newstrat, dtype=np.int32),
        np.ascontiguousarray(init_arr, dtype=float),
        float(control["eps"]),
        float(control["toler.chol"]),
        np.ascontiguousarray(flags, dtype=np.int32),
    )
    coef = np.asarray(beta, dtype=float).copy()
    u_arr = np.asarray(u, dtype=float)
    var = np.asarray(imat, dtype=float)
    means_arr = np.asarray(means, dtype=float)
    flag_i = int(flag)
    if flag_i < nvar:
        which_sing = np.diag(var) == 0
    else:
        which_sing = np.zeros(nvar, dtype=bool)

    if int(control["iter.max"]) > 1:
        infs = np.abs(u_arr @ var)
        if flag_i == 1000:
            warnings.warn("Ran out of iterations and did not converge", stacklevel=2)
        else:
            limited = (infs > float(control["eps"])) & (
                infs > float(control["toler.inf"]) * np.abs(coef)
            )
            if np.any(limited):
                _warn_infinite(limited)

    lp = x_mat @ coef + offset_arr - float(np.sum(coef * means_arr))
    score = np.exp(lp[sorted_idx])
    coef = coef.copy()
    coef[which_sing] = np.nan

    out: dict[str, Any] = {
        "coefficients": coef,
        "var": var,
        "loglik": np.asarray(loglik, dtype=float),
        "score": float(sctest),
        "iter": int(iter_),
        "linear.predictors": np.asarray(lp, dtype=float),
        "means": means_arr,
        "method": "coxph",
    }
    if resid:
        resid_sorted, _elapsed_resid = _agmart(
            0,
            np.ascontiguousarray(start[sorted_idx], dtype=float),
            np.ascontiguousarray(stop[sorted_idx], dtype=float),
            np.ascontiguousarray(np.trunc(event[sorted_idx]), dtype=np.int32),
            np.ascontiguousarray(score, dtype=float),
            np.ones(n, dtype=float),
            np.ascontiguousarray(newstrat, dtype=np.int32),
        )
        residuals = np.empty(n, dtype=float)
        residuals[sorted_idx] = np.asarray(resid_sorted, dtype=float)
        out["residuals"] = residuals
    return out
