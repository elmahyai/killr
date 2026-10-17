"""Pseudo values from a survfit object, from survival::pseudo."""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from survival.strata import StrataFactor, _as_factor
from survival.surv import SurvObject, aeqSurv


_TYPE_ALIASES = (
    "pstate",
    "cumhaz",
    "sojourn",
    "survival",
    "chaz",
    "rmst",
    "rmts",
    "auc",
)
_TYPE_MAP = (1, 2, 3, 1, 2, 3, 3, 3)
_CANONICAL_TYPES = ("pstate", "cumhaz", "auc")


@dataclass
class SurvFitObject:
    """Minimal survfit object for pseudo and IJ residuals (simple KM paths)."""

    n: int
    time: np.ndarray
    n_risk: np.ndarray
    n_event: np.ndarray
    n_censor: np.ndarray
    surv: np.ndarray
    cumhaz: np.ndarray
    class_: tuple[str, ...] = ("survfit",)
    type: str = "right"
    call: dict[str, Any] = field(default_factory=dict)
    y: np.ndarray | None = None
    model: Any = None
    x: StrataFactor | None = None
    strata: np.ndarray | None = None
    states: list[str] | None = None
    weight: np.ndarray | None = None
    start_time: float | None = None
    timefix: bool = True
    na_action: Any = None
    n_id: np.ndarray | None = None
    oldstates: Any = None
    logse: bool = True

    def __getitem__(self, index: int | slice) -> SurvFitObject:
        if isinstance(index, slice):
            raise NotImplementedError("vector survfit subscripts are not supported")
        if self.strata is None:
            raise IndexError("invalid survfit subscript")
        counts = np.asarray(self.strata, dtype=int)
        start = int(np.sum(counts[: index - 1])) if index > 1 else 0
        stop = start + int(counts[index - 1])
        sl = slice(start, stop)

        def take(name: str) -> np.ndarray:
            value = getattr(self, name)
            arr = np.asarray(value, dtype=float)
            if arr.ndim == 1:
                return arr[sl]
            return arr[sl, ...]

        return SurvFitObject(
            n=int(self.n),
            time=take("time"),
            n_risk=take("n_risk"),
            n_event=take("n_event"),
            n_censor=take("n_censor"),
            surv=take("surv"),
            cumhaz=take("cumhaz"),
            class_=self.class_,
            type=self.type,
            call=dict(self.call),
            y=self.y,
            model=self.model,
            x=self.x,
            strata=None,
            states=self.states,
            weight=self.weight,
            start_time=self.start_time,
            timefix=self.timefix,
            na_action=self.na_action,
            n_id=self.n_id,
            oldstates=self.oldstates,
            logse=self.logse,
        )


def _inherits_survfit(fit: Any) -> bool:
    if isinstance(fit, SurvFitObject):
        return True
    classes = getattr(fit, "class_", None)
    if classes is None and isinstance(fit, dict):
        classes = fit.get("class_") or fit.get("class")
    if classes is None:
        return False
    if isinstance(classes, str):
        classes = (classes,)
    return "survfit" in classes


def _is_survfitms(fit: SurvFitObject) -> bool:
    return "survfitms" in fit.class_


def _is_survfitcox(fit: SurvFitObject) -> bool:
    return "survfitcox" in fit.class_


def _normalize_type(type_arg: str | None) -> str:
    if type_arg is None:
        return "pstate"
    text = str(type_arg).lower()
    if text not in _TYPE_ALIASES:
        choices = ", ".join(f"'{item}'" for item in _TYPE_ALIASES[:3])
        raise ValueError(f"'type' should be one of {choices}")
    idx = _TYPE_ALIASES.index(text)
    return _CANONICAL_TYPES[_TYPE_MAP[idx] - 1]


def _fit_dim(fit: SurvFitObject) -> tuple[int, ...]:
    if fit.strata is not None and np.asarray(fit.strata).size:
        return (len(fit.strata), int(np.max(np.asarray(fit.time).size, 1)))
    return (int(np.asarray(fit.time).size),)


def _kaplan_meier_from_y(y: np.ndarray, weights: np.ndarray | None = None) -> dict[str, np.ndarray]:
    """Right-censored KM curve matching survival::survfit(Surv(time, status) ~ 1)."""
    if y.shape[1] != 2:
        raise ValueError("expected two-column Surv data")
    if weights is None:
        wt = np.ones(y.shape[0], dtype=float)
    else:
        wt = np.asarray(weights, dtype=float).reshape(-1)
    time = y[:, 0]
    status = y[:, 1].astype(int)
    order = np.argsort(time, kind="mergesort")
    time = time[order]
    status = status[order]
    wt = wt[order]
    utime = np.unique(time)
    ntime = utime.size
    n_risk = np.zeros(ntime, dtype=float)
    n_event = np.zeros(ntime, dtype=float)
    n_censor = np.zeros(ntime, dtype=float)
    surv = np.ones(ntime, dtype=float)
    km = 1.0
    for i, t in enumerate(utime):
        at = time == t
        d = float(np.sum(wt[at & (status == 1)]))
        c = float(np.sum(wt[at & (status == 0)]))
        nr = float(np.sum(wt[time >= t]))
        n_risk[i] = nr
        n_event[i] = d
        n_censor[i] = c
        if d > 0 and nr > 0:
            km *= (nr - d) / nr
        surv[i] = km
    with np.errstate(divide="ignore", invalid="ignore"):
        increments = np.where(n_risk > 0, n_event / n_risk, 0.0)
    cumhaz = np.cumsum(increments)
    return {
        "time": utime,
        "n.risk": n_risk,
        "n.event": n_event,
        "n.censor": n_censor,
        "surv": surv,
        "cumhaz": cumhaz,
    }


def survfit_from_y(
    y: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    model: Any = None,
    call: dict[str, Any] | None = None,
) -> SurvFitObject:
    """Build a simple ~1 survfit object from a two-column survival matrix."""
    km = _kaplan_meier_from_y(y, weights)
    n = int(y.shape[0])
    x = _as_factor([1] * n)
    return SurvFitObject(
        n=n,
        time=km["time"],
        n_risk=km["n.risk"],
        n_event=km["n.event"],
        n_censor=km["n.censor"],
        surv=km["surv"],
        cumhaz=km["cumhaz"],
        y=np.asarray(y, dtype=float),
        model=model,
        x=x,
        call=call or {"stype": 1, "ctype": 1},
        timefix=True,
    )


def _summary_at_times(fit: SurvFitObject, times: np.ndarray, *, extend: bool) -> dict[str, np.ndarray]:
    times = np.asarray(times, dtype=float).reshape(-1)
    curve = fit
    if not extend:
        times = times[times <= np.max(curve.time)]
    if times.size == 0 or curve.time.size == 0:
        raise ValueError("no points selected for one or more curves")
    index1 = _find_interval_r(times, curve.time)
    index2 = 1 + _find_interval_r_left_open(times, curve.time)
    pick_index = np.maximum(index1, 1) - 1

    def pick(name: str) -> np.ndarray:
        arr = np.asarray(getattr(curve, name), dtype=float)
        return arr[pick_index]

    nrisk_pad = np.concatenate([curve.n_risk, [0.0]])
    n_risk = nrisk_pad[np.clip(index2 - 1, 0, nrisk_pad.size - 1)]
    out = {
        "time": times,
        "surv": pick("surv"),
        "cumhaz": pick("cumhaz"),
        "n.risk": n_risk,
        "n.event": pick("n_event"),
        "n.censor": pick("n_censor"),
    }
    if fit.states is not None and len(fit.states) > 1:
        out["pstate"] = out["surv"]
    return out


def _summary_rmean(fit: SurvFitObject, tau: float) -> np.ndarray:
    """Restricted mean survival time per curve (simple survival, one stratum)."""
    time = np.asarray(fit.time, dtype=float)
    surv = np.asarray(fit.surv, dtype=float)
    if time.size == 0:
        return np.array([0.0])
    t0 = 0.0 if np.min(time) > 0 else 2.0 * np.min(time) - 1.0
    dtime = np.concatenate([[t0], time])
    delta = np.diff(dtime)
    j = time.size
    aucd = np.cumsum(np.concatenate([[0.0], surv[:-1]]) * delta)
    if tau > np.max(time):
        rmean = aucd[j - 1] + surv[j - 1] * (tau - time[j - 1])
    else:
        idx = np.searchsorted(time, tau, side="right") - 1
        idx = int(np.clip(idx, 0, j - 1))
        if tau <= time[0]:
            rmean = tau - t0
        else:
            prev_time = time[idx - 1] if idx > 0 else t0
            prev_auc = aucd[idx - 1] if idx > 0 else 0.0
            rmean = prev_auc + surv[idx] * (tau - prev_time)
    return np.array([rmean])


def _find_interval_r(values: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    """R ``findInterval`` with ``left.open=FALSE`` (1-based index into ``cuts``)."""
    values = np.asarray(values, dtype=float)
    cuts = np.asarray(cuts, dtype=float)
    return np.searchsorted(cuts, values, side="right").astype(int)


def _find_interval_r_left_open(values: np.ndarray, cuts: np.ndarray) -> np.ndarray:
    """R ``findInterval(..., left.open=TRUE)``."""
    values = np.asarray(values, dtype=float)
    cuts = np.asarray(cuts, dtype=float)
    return np.searchsorted(cuts, values, side="left").astype(int)


def _rsurvpart1(
    y: np.ndarray,
    times: np.ndarray,
    type_name: str,
    stype: int,
    ctype: int,
    fit: SurvFitObject,
) -> np.ndarray:
    times = np.asarray(times, dtype=float).reshape(-1)
    ntime = times.size
    events = fit.n_event > 0
    hazard = np.diff(np.concatenate([[0.0], fit.cumhaz[events]]))
    nrisk = fit.n_risk[events]
    surv = fit.surv[events]
    dtime = fit.time[events]
    n = y.shape[0]
    ny = y.shape[1]
    status = y[:, ny - 1].astype(int)

    tindex = _find_interval_r(times, dtime)
    # R uses Y[, ny - 1] (1-based), the event/stop time column.
    yindex = _find_interval_r(y[:, ny - 2], dtime)
    if ny == 3:
        sindex = _find_interval_r(y[:, 0], dtime)
    else:
        sindex = None

    ymin = np.minimum.outer(yindex, tindex)
    dmin = np.where(
        (status == 0)[:, None],
        0,
        np.where((yindex[:, None] == 0) | (yindex[:, None] > tindex[None, :]), 0, yindex[:, None]),
    )
    if ny == 3:
        smin = np.minimum.outer(sindex, tindex)

    if type_name == "cumhaz" or (type_name == "pstate" and stype == 2):
        hsum = np.cumsum(np.concatenate([[0.0], hazard / nrisk]))
        term1 = np.concatenate([[0.0], 1.0 / nrisk])[dmin]
        term2 = hsum[ymin]
        if ny == 2:
            resid = term1 - term2
        else:
            term3 = hsum[smin]
            resid = term1 + term3 - term2
        if ctype == 2:
            warnings.warn(
                "code for ctype=2 not yet completed, result is approximate",
                RuntimeWarning,
                stacklevel=3,
            )
        if type_name == "pstate":
            surv_at_t = np.concatenate([[1.0], surv])[np.repeat(tindex, n)]
            resid = -resid * surv_at_t.reshape(n, ntime, order="F")
    elif type_name == "pstate":
        temp = np.where(hazard == 1, 1.0, 1.0 - hazard)
        hsum = np.cumsum(np.concatenate([[0.0], hazard / (nrisk * temp)]))
        term1 = np.concatenate([[0.0], 1.0 / (temp * nrisk)])[dmin]
        term2 = hsum[ymin]
        stemp = np.concatenate([[1.0], surv])[np.repeat(tindex, n)]
        if ny == 2:
            resid = stemp.reshape(n, ntime, order="F") * (term2 - term1)
        else:
            term3 = hsum[smin]
            resid = stemp.reshape(n, ntime, order="F") * (term2 - (term3 + term1))
    elif type_name == "auc":
        if np.min(dtime) > 0:
            t0 = 0.0
        else:
            t0 = 2.0 * np.min(dtime) - 1.0
        delta = np.diff(np.concatenate([[t0], dtime]))
        j = dtime.size
        aucd = np.cumsum(np.concatenate([[1.0], surv[:-1]]) * delta)
        if np.max(times) > np.max(dtime):
            x = np.concatenate([[t0], dtime, [np.max(times)]])
            y = np.concatenate([[0.0], aucd, [aucd[j - 1] + surv[j - 1] * (np.max(times) - dtime[j - 1])]])
            auctau = np.interp(times, x, y, left=0.0)
        else:
            auctau = np.interp(times, np.concatenate([[t0], dtime]), np.concatenate([[0.0], aucd]), left=0.0)
        if stype == 2:
            dd = 1.0 / nrisk
        else:
            dd = 1.0 / (nrisk * (1.0 - hazard))
        dd = np.where(np.isfinite(dd), dd, 0.0)
        wtmat = auctau[:, None] - aucd[None, :]
        resid = np.zeros((n, ntime), dtype=float)
        for i in range(ntime):
            hsum = np.cumsum(np.concatenate([[0.0], wtmat[i, :] * hazard * dd]))
            term1 = np.concatenate([[0.0], wtmat[i, :] * dd])[dmin[:, i]]
            term2 = hsum[ymin[:, i]]
            if ny == 2:
                resid[:, i] = term2 - term1
            else:
                term3 = hsum[smin[:, i]]
                resid[:, i] = term2 - (term1 + term3)
    else:
        raise ValueError("unknown type")
    return resid


def _residuals_survfit(
    fit: SurvFitObject,
    times: np.ndarray,
    *,
    type_name: str,
    collapse: bool,
    weighted: bool | None,
    data_frame: bool,
    extra: bool,
) -> Any:
    if fit.type == "interval":
        raise ValueError("residuals for interval-censored data are not available")
    if _is_survfitcox(fit):
        raise ValueError("residuals method for coxph survival curve not found")
    if not isinstance(collapse, (bool, np.bool_)):
        raise ValueError("collapse must be TRUE/FALSE")
    if weighted is None:
        weighted = collapse
    if not isinstance(weighted, (bool, np.bool_)):
        raise ValueError("weighted must be TRUE/FALSE")
    if not isinstance(data_frame, (bool, np.bool_)):
        raise ValueError("data.frame must be TRUE/FALSE")
    if fit.oldstates is not None:
        raise ValueError("residuals not available for a subscripted survfit object")

    type_name = _normalize_type(type_name)
    timefix = fit.timefix is None or bool(fit.timefix)
    if times is None:
        raise ValueError("the times argument is required")
    times = np.sort(np.unique(np.asarray(times, dtype=float)))
    if timefix:
        surv_times = SurvObject(np.column_stack([times, np.zeros_like(times)]), "right")
        times = aeqSurv(surv_times).columns[:, 0]

    if fit.model is None:
        if fit.y is None:
            raise ValueError("survfit object must include y or model")
        mf = {"response": fit.y}
    else:
        mf = fit.model
    if isinstance(mf, dict) and "response" in mf:
        y = np.asarray(mf["response"], dtype=float)
    else:
        y = np.asarray(fit.y if fit.y is not None else mf, dtype=float)
    n = y.shape[0]
    if n == 0:
        raise ValueError("data set has no non-missing observations")

    if fit.weight is None:
        casewt = np.ones(n, dtype=float)
    else:
        casewt = np.asarray(fit.weight, dtype=float).reshape(-1)
        weighted = False

    if fit.x is None:
        x = _as_factor([1] * n)
    else:
        x = fit.x
    rowid = np.array([code if code is not None else 1 for code in x.codes], dtype=int)
    ncurve = int(np.max(rowid))
    if _is_survfitms(fit):
        raise NotImplementedError("multi-state survfit residuals are not implemented")

    resid = np.zeros((n, times.size), dtype=float)
    stype = int(fit.call.get("stype", 1) or 1)
    ctype = int(fit.call.get("ctype", 1) or 1)
    for i in range(1, ncurve + 1):
        i1 = np.where(rowid == i)[0]
        curve_fit = fit[i] if fit.strata is not None else fit
        resid[i1, :] = _rsurvpart1(y[i1, :], times, type_name, stype, ctype, curve_fit)

    id_vals = np.arange(1, n + 1, dtype=int)
    cluster = id_vals
    if cluster.size and np.unique(cluster).size == cluster.size:
        collapse = False
    if collapse and not weighted:
        raise ValueError("invalid combination of options: collapse=TRUE and weighted=FALSE")

    curve = rowid
    if collapse:
        order = np.argsort(id_vals, kind="mergesort")
        sorted_id = id_vals[order]
        uniq, first_idx = np.unique(sorted_id, return_index=True)
        accum = np.zeros((uniq.size, times.size), dtype=float)
        counts = np.zeros(uniq.size, dtype=int)
        for row, ident in enumerate(id_vals):
            j = int(np.searchsorted(uniq, ident))
            accum[j, :] += resid[row, :] * casewt[row]
            counts[j] += 1
        resid = accum
        id_vals = uniq
        curve = rowid[np.sort(first_idx)]

    elif weighted and np.any(casewt != 1):
        resid = resid * casewt[:, None]

    if ncurve == 1:
        curve_out = None
    else:
        curve_out = curve

    if data_frame:
        raise NotImplementedError("data.frame=TRUE is not implemented for pseudo")
    if extra:
        return {"resid": resid, "curve": curve_out}
    return resid


def pseudo(
    fit: SurvFitObject | Any,
    times: np.ndarray | list[float],
    type: str | None = None,
    collapse: bool = True,
    data_frame: bool = False,
    **kwargs: Any,
) -> np.ndarray | dict[str, Any]:
    """Infinitesimal-jackknife pseudo values from a survfit object."""
    if not _inherits_survfit(fit):
        raise ValueError("fit argument must be a survfit object")
    if isinstance(fit, dict):
        fit = _dict_to_survfit(fit)
    if fit.model is None and fit.y is not None:
        fit.model = {"response": fit.y}

    type_name = _normalize_type(type)
    times_arr = np.asarray(times, dtype=float).reshape(-1)
    ntime = times_arr.size

    rfit = _residuals_survfit(
        fit,
        times_arr,
        type_name=type_name,
        collapse=collapse,
        weighted=kwargs.get("weighted"),
        data_frame=data_frame,
        extra=True,
    )

    ddf = _fit_dim(fit)
    if not data_frame:
        ddr = np.asarray(rfit["resid"]).shape
    else:
        ddr = None

    if fit.strata is None:
        ncurve = 1
        icurve = 1
    else:
        ncurve = len(fit.strata)
        icurve = rfit["curve"]

    if fit.states is not None and len(fit.states) > 1:
        nstate = len(fit.states)
        nhaz = np.asarray(fit.cumhaz).shape[1] if np.asarray(fit.cumhaz).ndim > 1 else 1
        if data_frame:
            raise NotImplementedError("multi-state data.frame pseudo is not implemented")
        if type_name == "cumhaz":
            ihaz = np.repeat(np.arange(1, nhaz + 1), ddr[0])
        else:
            istate = np.repeat(np.arange(1, nstate + 1), ddr[0])
    else:
        nstate = nhaz = 1
        istate = ihaz = 1

    if ntime == 1:
        itime = 1
    else:
        if data_frame:
            raise NotImplementedError("data.frame pseudo is not implemented")
        prod_ddr = int(np.prod(np.asarray(rfit["resid"]).shape[:-1]))
        itime = np.repeat(np.arange(1, ntime + 1), prod_ddr)

    if fit.n_id is None:
        nn = np.array([fit.n], dtype=float)
    else:
        nn = np.asarray(fit.n_id, dtype=float)

    if ncurve == 1:
        etime = float(np.max(fit.time))
    else:
        etime = fit.time[np.cumsum(np.asarray(fit.strata, dtype=int)) - 1]
    if np.any(etime < np.max(times_arr)):
        warnings.warn(
            "requested time points are beyond the end of one or more curves",
            RuntimeWarning,
            stacklevel=2,
        )

    resid_flat = np.asarray(rfit["resid"], dtype=float).reshape(-1, order="F")

    if type_name == "pstate":
        temp = _summary_at_times(fit, times_arr, extend=True)
        if nstate > 1:
            yhat = temp["pstate"].reshape(ntime, ncurve, nstate)
            idx = (itime - 1, np.asarray(icurve) - 1, np.asarray(istate) - 1)
            ptemp = yhat[idx] + nn[np.asarray(icurve) - 1] * resid_flat
        else:
            yhat = temp["surv"].reshape(ntime, ncurve)
            if ncurve == 1:
                ptemp = yhat[itime - 1, 0] + nn[0] * resid_flat
            else:
                ic = np.asarray(icurve) - 1
                ptemp = yhat[itime - 1, ic] + nn[0] * resid_flat
    elif type_name == "auc":
        yhat = np.zeros((ntime, ncurve, max(nstate, 1)), dtype=float)
        if nstate > 1:
            for i in range(ntime):
                table = _summary_rmean(fit, float(times_arr[i]))
                yhat[i, :, :] = table
            idx = (itime - 1, np.asarray(icurve) - 1, np.asarray(istate) - 1)
            ptemp = yhat[idx] + nn[np.asarray(icurve) - 1] * resid_flat
        else:
            yhat2 = np.zeros((ntime, ncurve), dtype=float)
            for i in range(ntime):
                table = _summary_rmean(fit, float(times_arr[i]))
                if ncurve == 1:
                    yhat2[i, :] = table[0]
                else:
                    yhat2[i, :] = table
            ic = np.zeros_like(itime) if ncurve == 1 else np.asarray(icurve) - 1
            ptemp = yhat2[itime - 1, ic] + nn[0] * resid_flat
    elif type_name == "cumhaz":
        temp = _summary_at_times(fit, times_arr, extend=True)
        if nstate > 1:
            yhat = temp["cumhaz"].reshape(ntime, ncurve, nhaz)
            idx = (itime - 1, np.asarray(icurve) - 1, np.asarray(ihaz) - 1)
            ptemp = yhat[idx] + nn[np.asarray(icurve) - 1] * resid_flat
        else:
            yhat = temp["cumhaz"].reshape(ntime, ncurve)
            if ncurve == 1:
                ptemp = yhat[itime - 1, 0] + nn[0] * resid_flat
            else:
                ic = np.asarray(icurve) - 1
                ptemp = yhat[itime - 1, ic] + nn[0] * resid_flat
    else:
        raise ValueError("unknown type")

    if data_frame:
        rfit["pseudo"] = ptemp
        return rfit
    return np.asarray(ptemp, dtype=float).reshape(rfit["resid"].shape, order="F")


def _dict_to_survfit(data: dict[str, Any]) -> SurvFitObject:
    return SurvFitObject(
        n=int(data["n"]),
        time=np.asarray(data["time"], dtype=float),
        n_risk=np.asarray(data.get("n_risk", data.get("n.risk")), dtype=float),
        n_event=np.asarray(data.get("n_event", data.get("n.event")), dtype=float),
        n_censor=np.asarray(data.get("n_censor", data.get("n.censor")), dtype=float),
        surv=np.asarray(data["surv"], dtype=float),
        cumhaz=np.asarray(data["cumhaz"], dtype=float),
        class_=tuple(data.get("class_", ("survfit",))),
        type=str(data.get("type", "right")),
        call=dict(data.get("call", {})),
        y=None if data.get("y") is None else np.asarray(data["y"], dtype=float),
        model=data.get("model"),
        x=data.get("x"),
        strata=None if data.get("strata") is None else np.asarray(data["strata"]),
        states=data.get("states"),
        weight=None if data.get("weight") is None else np.asarray(data["weight"], dtype=float),
        start_time=data.get("start_time"),
        timefix=data.get("timefix", True),
        na_action=data.get("na_action"),
        n_id=None if data.get("n_id") is None else np.asarray(data["n_id"], dtype=float),
        oldstates=data.get("oldstates"),
        logse=bool(data.get("logse", True)),
    )
