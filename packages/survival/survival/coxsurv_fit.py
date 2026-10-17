"""Survival curves from a fitted Cox model (survival::coxsurv.fit).

This is called by survfit.coxph after the data and arguments are checked. The
per-stratum baseline pieces come from survival's agsurv, which is the Python
helper in survival._coxsurv (it implements the agsurv5 Efron sums in Python).

Translated: survtype 2 (Breslow) and 3 (Efron), with the stratum loop, the
newdata expansion for one or many rows (with std.err), the time-dependent
newdata branch with id2 (onecurve), and unlist.

Not translated: stype = 1 (Kalbfleisch-Prentice). That path uses the Cagsurv4
kernel, which is not in a crate, so NotImplementedError is raised.
"""

from __future__ import annotations

from typing import Any

import numpy as np


def _rcumsum(values: np.ndarray) -> np.ndarray:
    """R rev(cumsum(rev(x))): sum from the last time to the first."""
    return np.flip(np.cumsum(np.flip(values, axis=0), axis=0), axis=0)


def _agsurv(y: Any, x: Any, wt: Any, risk: Any, survtype: int, vartype: int) -> dict[str, Any]:
    """Per-stratum baseline pieces (survival agsurv.R), for survtype 2 and 3.

    The Efron sums follow agsurv5.c with the matrix indexed [time, covariate],
    which is the column-major layout the C code assumes.
    """
    y_arr = np.asarray(y, dtype=float)
    n = y_arr.shape[0]
    if y_arr.shape[1] != 2:
        raise NotImplementedError("counting process survival data is not translated for coxsurv.fit")
    x_mat = np.asarray(x, dtype=float).reshape(n, -1)
    nvar = x_mat.shape[1]
    wt_arr = np.asarray(wt, dtype=float).reshape(-1)
    risk_arr = np.asarray(risk, dtype=float).reshape(-1)
    status = y_arr[:, 1]
    dtime = y_arr[:, 0]
    death = status == 1
    time = np.unique(dtime)
    ntime = len(time)
    index = np.searchsorted(time, dtime)

    def rowsum(values: np.ndarray) -> np.ndarray:
        out = np.zeros((ntime,) + values.shape[1:], dtype=float)
        np.add.at(out, index, values)
        return out

    nevent = rowsum(wt_arr * death)
    ncens = rowsum(wt_arr * (~death))
    wrisk = wt_arr * risk_arr
    nrisk = _rcumsum(rowsum(wrisk))
    irisk = _rcumsum(rowsum(wt_arr))
    xsum = _rcumsum(rowsum(wrisk[:, None] * x_mat))
    ndeath = rowsum(status)

    sum1 = np.zeros(ntime, dtype=float)
    sum2 = np.zeros(ntime, dtype=float)
    xbar_efron = np.zeros((ntime, nvar), dtype=float)
    if survtype == 3 or vartype == 3:
        xsum2 = rowsum((wrisk * death)[:, None] * x_mat)
        erisk = rowsum(wrisk * death)
        for i in range(ntime):
            d = int(round(ndeath[i]))
            if d == 1:
                temp = 1.0 / nrisk[i]
                sum1[i] = temp
                sum2[i] = temp * temp
                xbar_efron[i, :] = xsum[i, :] * temp * temp
            else:
                for j in range(d):
                    temp = 1.0 / (nrisk[i] - erisk[i] * j / d)
                    sum1[i] += temp / d
                    sum2[i] += temp * temp / d
                    xbar_efron[i, :] += ((xsum[i, :] - xsum2[i, :] * j / d) * temp * temp) / d

    if survtype == 1:
        raise NotImplementedError("survtype 1 needs the agsurv4 kernel")
    haz = nevent / nrisk if survtype == 2 else nevent * sum1
    if vartype == 1:
        denom = np.where(nevent >= nrisk, nrisk, nrisk - nevent)
        varhaz = nevent / (nrisk * denom)
    elif vartype == 2:
        varhaz = nevent / nrisk**2
    else:
        varhaz = nevent * sum2
    if vartype in (1, 2):
        xbar = (xsum / nrisk[:, None]) * haz[:, None]
    else:
        xbar = nevent[:, None] * xbar_efron
    return {
        "n": n,
        "time": time,
        "n.event": nevent,
        "n.risk": irisk,
        "n.censor": ncens,
        "hazard": haz,
        "cumhaz": np.cumsum(haz),
        "varhaz": varhaz,
        "ndeath": ndeath,
        "xbar": xbar,
    }


def _as_2d(x: Any) -> np.ndarray:
    arr = np.asarray(x, dtype=float)
    if arr.ndim == 1:
        return arr.reshape(1, -1) if arr.size else arr.reshape(0, 0)
    return arr


def _expand(
    fit: dict[str, Any],
    survtype: int,
    x2: np.ndarray,
    risk2: np.ndarray,
    varmat: np.ndarray,
    se_fit: bool,
) -> dict[str, Any]:
    surv = np.exp(-fit["cumhaz"])
    out = dict(fit)
    if x2.ndim == 2 and x2.shape[0] > 1:
        out["surv"] = np.power.outer(surv, risk2)
        if se_fit:
            varh = np.zeros((len(fit["varhaz"]), x2.shape[0]), dtype=float)
            for i in range(x2.shape[0]):
                dt = np.outer(fit["hazard"], x2[i, :]) - fit["xbar"]
                dt = np.cumsum(dt, axis=0)
                varh[:, i] = (np.cumsum(fit["varhaz"]) + np.sum((dt @ varmat) * dt, axis=1)) * risk2[i] ** 2
            out["std.err"] = np.sqrt(varh)
        out["cumhaz"] = np.outer(fit["cumhaz"], risk2)
    else:
        row = x2.reshape(-1)
        out["surv"] = surv ** risk2[0]
        if se_fit:
            dt = np.outer(fit["hazard"], row) - fit["xbar"]
            dt = np.cumsum(dt, axis=0)
            varh = (np.cumsum(fit["varhaz"]) + np.sum((dt @ varmat) * dt, axis=1)) * risk2[0] ** 2
            out["std.err"] = np.sqrt(varh)
        out["cumhaz"] = fit["cumhaz"] * risk2[0]
    return out


def _onecurve(
    survlist: list[dict[str, Any]],
    survtype: int,
    x2: np.ndarray,
    y2: np.ndarray,
    strata2: np.ndarray,
    risk2: np.ndarray,
    se_fit: bool,
    varmat: np.ndarray,
    stratum_n: list[int],
) -> dict[str, Any]:
    ntarget = x2.shape[0]
    times: list[np.ndarray] = []
    hazards: list[np.ndarray] = []
    n_event: list[np.ndarray] = []
    n_risk: list[np.ndarray] = []
    n_censor: list[np.ndarray] = []
    dts: list[np.ndarray] = []
    varh1: list[np.ndarray] = []
    toffset = 0.0
    stemp = np.asarray(strata2, dtype=int)
    for i in range(ntarget):
        if i > 0:
            toffset = toffset + y2[i - 1, 1] - y2[i, 0]
        slist = survlist[int(stemp[i]) - 1]
        indx = np.where((slist["time"] > y2[i, 0]) & (slist["time"] <= y2[i, 1]))[0]
        if len(indx) == 0:
            continue
        times.append(toffset + slist["time"][indx])
        hazards.append(slist["hazard"][indx] * risk2[i])
        n_event.append(slist["n.event"][indx])
        n_risk.append(slist["n.risk"][indx])
        n_censor.append(slist["n.censor"][indx])
        dts.append((np.outer(slist["hazard"][indx], x2[i, :]) - slist["xbar"][indx, :]) * risk2[i])
        varh1.append(slist["varhaz"][indx] * risk2[i] ** 2)

    hazard_all = np.concatenate(hazards) if hazards else np.zeros(0)
    cumhaz = np.cumsum(hazard_all)
    surv = np.exp(-cumhaz)
    out: dict[str, Any] = {
        "n": stratum_n[int(stemp[0]) - 1],
        "time": np.concatenate(times) if times else np.zeros(0),
        "n.risk": np.concatenate(n_risk) if n_risk else np.zeros(0),
        "n.event": np.concatenate(n_event) if n_event else np.zeros(0),
        "n.censor": np.concatenate(n_censor) if n_censor else np.zeros(0),
        "surv": surv,
        "cumhaz": cumhaz,
    }
    if se_fit:
        if dts:
            dt_all = np.vstack(dts)
            dt_all = np.cumsum(dt_all, axis=0)
            varh2 = np.sum((dt_all @ varmat) * dt_all, axis=1)
            varh1_all = np.concatenate(varh1)
            out["std.err"] = np.sqrt(np.cumsum(varh1_all) + varh2)
        else:
            out["std.err"] = np.zeros(0)
    return out


def coxsurv_fit(
    ctype: int,
    stype: int,
    se_fit: bool,
    varmat: Any,
    cluster: Any,
    y: Any,
    x: Any,
    wt: Any,
    risk: Any,
    position: Any = None,
    strata: Any = None,
    oldid: Any = None,
    y2: Any = None,
    x2: Any = None,
    risk2: Any = None,
    strata2: Any = None,
    id2: Any = None,
    unlist: bool = True,
) -> Any:
    """Baseline survival curves for a coxph model, one per stratum."""
    del cluster, position, oldid
    if stype == 1:
        raise NotImplementedError("stype = 1 (Kalbfleisch-Prentice) needs the agsurv4 kernel, not translated")
    y_arr = np.asarray(y, dtype=float)
    if y_arr.ndim == 1:
        y_arr = y_arr.reshape(-1, 2)
    nrow = y_arr.shape[0]
    x_arr = _as_2d(x)
    risk_arr = np.asarray(risk, dtype=float).reshape(-1)
    wt_arr = np.ones(nrow) if wt is None else np.asarray(wt, dtype=float).reshape(-1)
    if strata is None or np.size(strata) == 0:
        strata_arr = np.zeros(nrow, dtype=int)
    else:
        strata_arr = np.asarray(strata).reshape(-1)
    ustrata = np.unique(strata_arr)
    survtype = 1 if stype == 1 else ctype + 1
    vartype = survtype
    varmat_arr = np.asarray(varmat, dtype=float)
    if varmat_arr.ndim == 0:
        varmat_arr = varmat_arr.reshape(1, 1)
    if x_arr.ndim == 1:
        x_arr = x_arr.reshape(nrow, -1)

    survlist: list[dict[str, Any]] = []
    stratum_n: list[int] = []
    for u in ustrata:
        indx = np.where(strata_arr == u)[0]
        stratum_n.append(len(indx))
        survlist.append(
            _agsurv(
                y_arr[indx, :],
                x_arr[indx, :],
                wt_arr[indx],
                risk_arr[indx],
                survtype,
                vartype,
            )
        )

    x2_arr = _as_2d(x2) if x2 is not None else np.zeros((1, x_arr.shape[1]))
    risk2_arr = np.asarray(risk2 if risk2 is not None else [1.0], dtype=float).reshape(-1)
    names = [str(u) for u in ustrata]

    if id2 is None:
        result = [_expand(fit, survtype, x2_arr, risk2_arr, varmat_arr, se_fit) for fit in survlist]
        result_names = names
        multi = x2_arr.ndim == 2 and x2_arr.shape[0] > 1
        if unlist:
            if len(result) == 1:
                return _pick(result[0], se_fit)
            temp: dict[str, Any] = {
                "n": np.array([r["n"] for r in result]),
                "time": np.concatenate([r["time"] for r in result]),
                "n.risk": np.concatenate([r["n.risk"] for r in result]),
                "n.event": np.concatenate([r["n.event"] for r in result]),
                "n.censor": np.concatenate([r["n.censor"] for r in result]),
                "strata": {nm: len(r["time"]) for nm, r in zip(result_names, result)},
            }
            if multi:
                temp["surv"] = np.vstack([r["surv"] for r in result])
                temp["cumhaz"] = np.vstack([r["cumhaz"] for r in result])
                if se_fit:
                    temp["std.err"] = np.vstack([r["std.err"] for r in result])
            else:
                temp["surv"] = np.concatenate([np.ravel(r["surv"]) for r in result])
                temp["cumhaz"] = np.concatenate([np.ravel(r["cumhaz"]) for r in result])
                if se_fit:
                    temp["std.err"] = np.concatenate([np.ravel(r["std.err"]) for r in result])
            return temp
        return dict(zip(result_names, result))

    # Time-dependent newdata: one curve per id, built from the (time1, time2] rows.
    if y2 is None or strata2 is None:
        raise ValueError("y2 and strata2 are needed with id2")
    y2_arr = np.asarray(y2, dtype=float).reshape(-1, 2)
    strata2_arr = np.asarray(strata2).reshape(-1)
    id2_arr = np.asarray(id2).reshape(-1)
    x2_mat = _as_2d(x2)
    if np.all(id2_arr == id2_arr[0]):
        result = [
            _onecurve(
                survlist, survtype, x2_mat, y2_arr, strata2_arr, risk2_arr, se_fit, varmat_arr, stratum_n
            )
        ]
        result_names = [str(id2_arr[0])]
    else:
        uid = np.unique(id2_arr)
        result = []
        for u in uid:
            idx = np.where(id2_arr == u)[0]
            result.append(
                _onecurve(
                    survlist,
                    survtype,
                    x2_mat[idx, :],
                    y2_arr[idx, :],
                    strata2_arr[idx],
                    risk2_arr[idx],
                    se_fit,
                    varmat_arr,
                    stratum_n,
                )
            )
        result_names = [str(u) for u in uid]

    if unlist:
        if len(result) == 1:
            return _pick(result[0], se_fit)
        temp = {
            "n": np.array([r["n"] for r in result]),
            "time": np.concatenate([r["time"] for r in result]),
            "n.risk": np.concatenate([r["n.risk"] for r in result]),
            "n.event": np.concatenate([r["n.event"] for r in result]),
            "n.censor": np.concatenate([r["n.censor"] for r in result]),
            "strata": {nm: len(r["time"]) for nm, r in zip(result_names, result)},
            "surv": np.concatenate([r["surv"] for r in result]),
            "cumhaz": np.concatenate([r["cumhaz"] for r in result]),
        }
        if se_fit:
            temp["std.err"] = np.concatenate([r["std.err"] for r in result])
        return temp
    return dict(zip(result_names, result))


def _pick(fit: dict[str, Any], se_fit: bool) -> dict[str, Any]:
    keys = ["n", "time", "n.risk", "n.event", "n.censor", "surv", "cumhaz"]
    if se_fit:
        keys.append("std.err")
    return {k: fit[k] for k in keys}
