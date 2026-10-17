"""Cox partial likelihood fit for right-censored data (survival::coxph.fit).

The Newton iteration is the Rust crate coxfit6 (survival src/coxfit6.c), and
the martingale residuals are the same crate (src/coxmart.c). This module does
the R glue: sorting by strata and time, the null model, scaling flags,
un-sorting the residuals, and the output list.
"""

from __future__ import annotations

from typing import Any

import numpy as np

from coxfit6 import coxfit6_py as _coxfit6_py
from coxfit6 import coxmart_py as _coxmart_py


def _as_matrix(x: Any) -> tuple[np.ndarray, int]:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        if arr.size == 0:
            return np.zeros((0, 0), dtype=float), 0
        arr = arr.reshape(-1, 1)
    return arr, arr.shape[1]


def coxph_fit(
    x: Any,
    y: Any,
    strata: Any,
    offset: Any,
    init: Any,
    control: dict[str, Any],
    weights: Any,
    method: str,
    rownames: Any = None,
    resid: bool = True,
    nocenter: Any = None,
) -> dict[str, Any]:
    """Fit a Cox model for right-censored data with the Breslow or Efron ties."""
    del rownames  # names are not carried by the Python residual vector
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 1:
        y_arr = y_arr.reshape(-1, 2)
    n = y_arr.shape[0]
    x_mat, nvar = _as_matrix(x)
    if nvar == 0:
        x_mat = np.zeros((n, 0), dtype=float)
    time = y_arr[:, 0]
    status = y_arr[:, 1]

    # Sort by strata, then time; newstrat marks the last row of each stratum.
    if strata is None or np.size(strata) == 0:
        sorted_idx = np.argsort(time, kind="stable")
        strata_sorted = None
        newstrat = np.zeros(n, dtype=np.int32)
    else:
        strata_arr = np.asarray(strata, dtype=float).reshape(-1)
        sorted_idx = np.lexsort((time, strata_arr))
        strata_sorted = strata_arr[sorted_idx]
        newstrat = np.ones(n, dtype=np.int32)
        if n > 1:
            newstrat[:-1] = (np.diff(strata_sorted) != 0).astype(np.int32)

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
    weights_sorted = weights_arr[sorted_idx]
    stime = np.ascontiguousarray(time[sorted_idx], dtype=float)
    sstat = np.ascontiguousarray(status[sorted_idx], dtype=np.int32)
    offset_sorted = np.ascontiguousarray(offset_arr[sorted_idx], dtype=float)

    if nvar == 0:
        x_work = np.ones((n, 1), dtype=float)
        nullmodel = True
        nvar_work = 1
        init_arr = np.zeros(1, dtype=float)
        maxiter = 0
    else:
        x_work = x_mat
        nullmodel = False
        nvar_work = nvar
        maxiter = int(control["iter.max"])
        if init is not None and np.size(init) > 0:
            init_arr = np.asarray(init, dtype=float).reshape(-1)
            if init_arr.size != nvar:
                raise ValueError("Wrong length for inital values")
        else:
            init_arr = np.zeros(nvar, dtype=float)
    if np.any(init_arr != 0):
        # The crate's coxfit6_py starts from beta = 0 and takes no init vector.
        raise NotImplementedError("non-zero init is not supported by the coxfit6 crate")

    if nocenter is None:
        zero_one = np.zeros(x_work.shape[1], dtype=bool)
    else:
        allowed = np.asarray(list(nocenter), dtype=float)
        zero_one = np.array(
            [bool(np.all(np.isin(x_work[:, j], allowed))) for j in range(x_work.shape[1])],
            dtype=bool,
        )
    doscale = np.where(zero_one, 0, 1).astype(np.int32)

    x_sorted = np.ascontiguousarray(x_work[sorted_idx, :], dtype=float)
    beta, means, u, imat, loglik, sctest, iter_, flag = _coxfit6_py(
        maxiter,
        stime,
        sstat,
        x_sorted,
        offset_sorted,
        np.ascontiguousarray(weights_sorted, dtype=float),
        np.ascontiguousarray(newstrat, dtype=np.int32),
        "efron" if method == "efron" else "breslow",
        float(control["eps"]),
        float(control["toler.chol"]),
        doscale,
    )
    beta = np.asarray(beta, dtype=float)
    means = np.asarray(means, dtype=float)
    u = np.asarray(u, dtype=float)
    imat = np.asarray(imat, dtype=float)
    loglik = np.asarray(loglik, dtype=float)

    if nullmodel:
        out: dict[str, Any] = {
            "loglik": np.float64(loglik[0]),
            "linear.predictors": offset_arr,
            "method": method,
            "class_": ("coxph.null", "coxph"),
        }
        if resid:
            score = np.exp(offset_sorted)
            coxres = _coxmart_py(
                stime,
                sstat,
                newstrat,
                np.ascontiguousarray(score, dtype=float),
                np.ascontiguousarray(weights_sorted, dtype=float),
                method == "efron",
            )
            residuals = np.zeros(n, dtype=float)
            residuals[sorted_idx] = np.asarray(coxres, dtype=float)
            out["residuals"] = residuals
        return out

    coef = beta.copy()
    lp = x_mat @ coef + offset_arr - float(np.sum(coef * means))
    var = imat.reshape(nvar, nvar)
    if flag < nvar:
        which_sing = np.diag(var) == 0
    else:
        which_sing = np.zeros(nvar, dtype=bool)
    if maxiter > 0:
        coef = coef.copy()
        coef[which_sing] = np.nan

    rval: dict[str, Any] = {
        "coefficients": coef,
        "var": var,
        "loglik": loglik,
        "score": float(sctest),
        "iter": int(iter_),
        "linear.predictors": np.asarray(lp, dtype=float),
        "means": means,
        "method": method,
        "class_": ("coxph",),
    }
    if resid:
        temp = np.asarray(lp, dtype=float)[sorted_idx]
        big = float(np.log(np.finfo(float).max))
        if np.any(temp > big):
            temp = temp + big - (1.0 + float(np.max(temp)))
        score = np.exp(temp)
        coxres = _coxmart_py(
            stime,
            sstat,
            newstrat,
            np.ascontiguousarray(score, dtype=float),
            np.ascontiguousarray(weights_sorted, dtype=float),
            method == "efron",
        )
        residuals = np.zeros(n, dtype=float)
        residuals[sorted_idx] = np.asarray(coxres, dtype=float)
        rval["residuals"] = residuals
    return rval
