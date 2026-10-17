"""Brier score for a fitted Cox model (survival::brier)."""

from __future__ import annotations

import numpy as np

from survival._coxsurv import _agsurv, _component, _inherits
from survival.surv import SurvObject, aeqSurv, is_Surv


def _as_surv_array(y):
    if is_Surv(y):
        return np.asarray(y.columns, dtype=float), y
    arr = np.asarray(y, dtype=float)
    if arr.ndim != 2 or arr.shape[1] not in (2, 3):
        raise ValueError("response must be a Surv object")
    return arr, SurvObject(arr, "right")


def _km_stype1(y: np.ndarray, wt: np.ndarray) -> dict[str, np.ndarray]:
    ny = y.shape[1]
    dtime = y[:, ny - 2]
    dstat = y[:, ny - 1]
    event = dstat == 1
    utime = np.sort(np.unique(dtime[event]))
    if utime.size == 0:
        return {
            "time": np.array([], dtype=float),
            "n.event": np.array([], dtype=float),
            "surv": np.array([], dtype=float),
        }
    nevent = np.zeros(utime.size, dtype=float)
    surv = np.zeros(utime.size, dtype=float)
    s_val = 1.0
    for k, t in enumerate(utime):
        at_risk = np.sum(wt[dtime >= t])
        d = np.sum(wt[(dtime == t) & event])
        nevent[k] = d
        if at_risk > 0 and d > 0:
            s_val *= (at_risk - d) / at_risk
        surv[k] = s_val
    return {"time": utime, "n.event": nevent, "surv": surv}


def _survfit0_km(fit: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    time = np.asarray(fit["time"], dtype=float)
    surv = np.asarray(fit["surv"], dtype=float)
    n_event = np.asarray(fit["n.event"], dtype=float)
    if time.size == 0:
        return fit
    t0 = min(0.0, float(time[0]))
    if time[0] == t0:
        return {"time": time, "surv": surv, "n.event": n_event}
    return {
        "time": np.concatenate([[t0], time]),
        "surv": np.concatenate([[1.0], surv]),
        "n.event": np.concatenate([[0.0], n_event]),
    }


def _summary_surv_at_times(
    time: np.ndarray, surv: np.ndarray, times: np.ndarray, *, extend: bool = True
) -> np.ndarray:
    time = np.asarray(time, dtype=float)
    surv = np.asarray(surv, dtype=float)
    out = np.empty(len(times), dtype=float)
    for i, t in enumerate(times):
        idx = np.where(time <= t)[0]
        if idx.size == 0:
            out[i] = 1.0 if extend else np.nan
        else:
            out[i] = surv[idx[-1]]
    return out


def _summary_survfit_surv(
    sfit: dict[str, np.ndarray], times: np.ndarray, *, extend: bool = True
) -> np.ndarray:
    s0 = _survfit0_km(sfit)
    return _summary_surv_at_times(s0["time"], s0["surv"], times, extend=extend)


def _summary_coxph_surv(
    time: np.ndarray, surv_matrix: np.ndarray, times: np.ndarray, *, extend: bool = True
) -> np.ndarray:
    n_sub = surv_matrix.shape[1]
    out = np.empty((len(times), n_sub), dtype=float)
    for i, t in enumerate(times):
        idx = np.where(time <= t)[0]
        if idx.size == 0:
            out[i, :] = 1.0 if extend else np.nan
        else:
            out[i, :] = surv_matrix[idx[-1], :]
    return out


def _survfit_null(y: np.ndarray, wt: np.ndarray, *, stype: int, ctype: int) -> dict[str, np.ndarray]:
    n = y.shape[0]
    if stype == 1:
        return _km_stype1(y, wt)
    x = np.zeros((n, 1), dtype=float)
    risk = np.ones(n, dtype=float)
    survtype = ctype + 1
    return _agsurv(y, x, wt, risk, survtype, survtype)


def _survfit_coxph_newdata(
    fit,
    y: np.ndarray,
    x: np.ndarray,
    wt: np.ndarray,
    linear_predictors: np.ndarray,
    *,
    ctype: int,
) -> dict[str, np.ndarray]:
    risk = np.exp(np.asarray(linear_predictors, dtype=float).reshape(-1))
    base = _agsurv(y, x, wt, risk, survtype=ctype + 1, vartype=ctype + 1)
    cumhaz = base["cumhaz"]
    surv0 = np.exp(-cumhaz)
    surv_matrix = np.exp(-np.outer(cumhaz, risk))
    return {
        "time": base["time"],
        "n.event": base["n.event"],
        "surv": surv_matrix,
        "cumhaz": base["cumhaz"],
        "null_surv": surv0,
    }


def _find_interval_vec(x: np.ndarray, vec: np.ndarray) -> np.ndarray:
    return np.searchsorted(vec, x, side="right")


def brier(
    fit,
    times=None,
    newdata=None,
    ties=True,
    detail=False,
    timefix=True,
    efron=False,
):
    if not _inherits(fit, "coxph"):
        raise ValueError("fit must be a coxph object")

    ty = _component(fit, "y")
    y_arr, y_obj = _as_surv_array(ty)
    if not is_Surv(y_obj):
        raise ValueError("response must be a Surv object")
    kind = y_obj.type
    if kind not in ("right", "mright", "counting", "mcounting"):
        raise ValueError("response must be right censored")

    n = y_arr.shape[0]
    ny = y_arr.shape[1]

    if not isinstance(timefix, (bool, np.bool_)) or (
        isinstance(timefix, (list, tuple, np.ndarray)) and len(timefix) > 1
    ):
        raise ValueError("invalid value for timefix option")
    if timefix:
        y_obj = aeqSurv(y_obj)
        y_arr = np.asarray(y_obj.columns, dtype=float)

    twt = _component(fit, "weights", optional=True)
    if twt is None:
        casewt = np.ones(n, dtype=float)
    else:
        casewt = np.asarray(twt, dtype=float).reshape(-1)
        if not np.issubdtype(casewt.dtype, np.number):
            raise ValueError("weights must be numeric")
        if not np.all(np.isfinite(casewt)):
            raise ValueError("weights must be finite")
        if np.any(casewt < 0):
            raise ValueError("weights must be non-negative")

    id_col = _component(fit, "id", optional=True)
    if ny == 3 and id_col is None:
        raise ValueError("id is required for start-stop data")
    if id_col is not None:
        raise ValueError("delayed entry is not yet implemented")

    method = str(_component(fit, "method", optional=True) or "efron")
    if efron and method == "efron":
        s0 = _survfit_null(y_arr, casewt, stype=2, ctype=2)
    else:
        s0 = _survfit_null(y_arr, casewt, stype=1, ctype=1)

    if times is None:
        ne = np.asarray(s0["n.event"], dtype=float)
        times = s0["time"][ne > 0]
    else:
        times = np.asarray(times, dtype=float).reshape(-1)
        if times.size == 0:
            raise ValueError("no values in times vector")
        if np.any(np.isnan(times)):
            raise ValueError("times contains missing values")

    p0 = 1.0 - _summary_survfit_surv(s0, times, extend=True)

    tx = _component(fit, "x", optional=True)
    tlp = _component(fit, "linear.predictors", optional=True)
    if newdata is not None:
        if isinstance(newdata, dict):
            tx_new = newdata.get("x")
            tlp_new = newdata.get("linear_predictors", newdata.get("linear.predictors"))
        else:
            raise NotImplementedError("newdata must be a dict with x and linear_predictors")
        if tx_new is None or tlp_new is None:
            raise ValueError("newdata must supply x and linear_predictors")
        tx = np.asarray(tx_new, dtype=float)
        tlp = np.asarray(tlp_new, dtype=float).reshape(-1)
    elif tx is None or tlp is None:
        raise ValueError("fit must contain x and linear.predictors for model predictions")

    tx = np.asarray(tx, dtype=float)
    tlp = np.asarray(tlp, dtype=float).reshape(-1)
    ctype_map = {"exact": 1, "breslow": 1, "efron": 2}
    ctype = ctype_map.get(method, 2)
    s1 = _survfit_coxph_newdata(fit, y_arr, tx, casewt, tlp, ctype=ctype)
    p1 = 1.0 - _summary_coxph_surv(s1["time"], s1["surv"], times, extend=True)

    dtime = y_arr[:, ny - 2].copy()
    dstat = y_arr[:, ny - 1]
    ntime = times.size

    if ties:
        unique_times = np.sort(np.unique(dtime))
        if unique_times.size > 1:
            mindiff = np.min(np.diff(unique_times))
            dtime = dtime + np.where(dstat == 0, mindiff / 2.0, 0.0)

    y_cens = np.column_stack([dtime, 1.0 - dstat])
    c0 = _survfit0_km(_km_stype1(y_cens, casewt))
    c0_time = c0["time"]
    c0_surv = c0["surv"]

    casewt = casewt / np.sum(casewt)
    brier_mat = np.zeros((ntime, 2), dtype=float)
    eff_n = np.zeros(ntime, dtype=float)

    for i in range(ntime):
        indx = _find_interval_vec(np.minimum(dtime, times[i]), c0_time)
        surv_c = c0_surv[np.maximum(indx - 1, 0)]
        wt = np.where((dtime < times[i]) & (dstat == 0), 0.0, casewt / surv_c)
        eff_n[i] = 1.0 / np.sum(wt**2)

        b0 = np.where(dtime > times[i], p0[i] ** 2, (dstat - p0[i]) ** 2)
        b1 = np.where(dtime > times[i], p1[i, :] ** 2, (dstat - p1[i, :]) ** 2)
        denom = np.sum(wt)
        brier_mat[i, 0] = np.sum(wt * b0) / denom
        brier_mat[i, 1] = np.sum(wt * b1) / denom

    ret = {
        "rsquared": 1.0 - brier_mat[:, 1] / brier_mat[:, 0],
        "brier": brier_mat[:, 1],
        "times": times,
    }
    if detail:
        ret["p0"] = p0
        ret["phat"] = p1
        ret["eff.n"] = eff_n
    return ret
