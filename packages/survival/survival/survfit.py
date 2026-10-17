"""Survival curves (survival::survfit).

Right-censored and counting-process data go to `survfitKM`. Multi-state
data (a factor status, `mright` or `mcounting`) go through the survfitaj
crate, the Aalen-Johansen kernel in survival 3.8-12 `src/survfitaj.c`.
Interval-censored data is left for survfitTurnbull. The formula method
`survfit.formula` is a later wrapper around this function.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from survfitaj import survfitaj as _survfitaj

from survival.strata import StrataFactor
from survival.surv import SurvObject, is_Surv
from survival.survcheck import _survcheck2
from survival.survfit_confint import survfit_confint
from survival.survfit_km import (
    _appearance,
    _charmatch,
    _match_arg,
    _survflag,
    _values,
    _weights_are_one,
    survfitKM,
)

_CONF_TYPES = ("log", "log-log", "plain", "none", "logit", "arcsin")
_CONF_LOWER = ("usual", "peto", "modified")
_TYPE_NAMES = ("kaplan-meier", "fleming-harrington", "fh2")
_TYPE_CODES = (1, 3, 4)


def _supplied(value: Any) -> bool:
    if value is None:
        return False
    return len(_values(value)) > 0


def _codes_array(factor: StrataFactor) -> np.ndarray:
    return np.array([0 if code is None else int(code) for code in factor.codes], dtype=int)


def _reshape(flat: list[float] | np.ndarray, nrow: int, ncol: int) -> np.ndarray:
    if nrow == 0 or ncol == 0:
        return np.zeros((nrow, ncol))
    return np.asarray(flat, dtype=float).reshape((nrow, ncol), order="F")


def _stack(parts: list[np.ndarray]) -> np.ndarray:
    if len(parts) == 1:
        return parts[0]
    return np.vstack(parts)


def _hindx(cstate: np.ndarray, status: np.ndarray, nstate: int) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Column-major from-to index. Positive status `s` is 1-based state `s`."""
    temp = np.zeros((nstate, nstate), dtype=np.int32)
    for i, code in enumerate(status):
        if code > 0:
            temp[int(cstate[i]), int(code) - 1] += 1
    flat = temp.ravel(order="F")
    where = np.flatnonzero(flat > 0)
    hindx = np.full(nstate * nstate, -1, dtype=np.int32)
    hindx[where] = np.arange(len(where), dtype=np.int32)
    rows, cols = np.unravel_index(where, (nstate, nstate), order="F")
    trmat = np.concatenate([rows.astype(np.int32), cols.astype(np.int32)])
    names = [f"{int(row) + 1}:{int(col) + 1}" for row, col in zip(rows, cols)]
    return hindx, trmat, names


def _rowsum(values: np.ndarray, groups: np.ndarray) -> np.ndarray:
    if groups.size == 0:
        return np.zeros((0, values.shape[1]))
    nclust = int(groups.max()) + 1
    out = np.zeros((nclust, values.shape[1]))
    for row, group in enumerate(groups):
        out[int(group)] += values[row]
    return out


def _twoclust(id_codes: list[int], cluster_codes: list[int]) -> int:
    order = sorted(range(len(id_codes)), key=lambda i: id_codes[i])
    i = 0
    n = len(order)
    while i < n:
        cid = id_codes[order[i]]
        iclust = cluster_codes[order[i]]
        while i < n and id_codes[order[i]] == cid:
            if cluster_codes[order[i]] != iclust:
                return 1
            i += 1
    return 0


def _influence_flag(influence: Any, se_fit: bool) -> int:
    if not se_fit:
        return 0
    if isinstance(influence, (bool, np.bool_)):
        return 1 if bool(influence) else 0
    if not isinstance(influence, (int, np.integer, float, np.floating)):
        raise ValueError("influence argument must be numeric or logical")
    return 1 if float(influence) > 0 else 0


def _first_state(base: np.ndarray, xcodes: np.ndarray, id_codes: list[int], istate: list[Any]) -> tuple[bool, Any]:
    order = np.lexsort((base[:, 0], np.asarray(id_codes), xcodes))
    seen: set[tuple[int, int]] = set()
    chosen: list[Any] = []
    for idx in order:
        key = (int(xcodes[idx]), int(id_codes[idx]))
        if key in seen:
            continue
        seen.add(key)
        chosen.append(istate[int(idx)])
    same = all(state == chosen[0] for state in chosen)
    return same, chosen[0]


def _survfit_aj(
    x: StrataFactor,
    y: SurvObject,
    weights: np.ndarray | None,
    stype: int,
    ctype: int,
    id: Any,
    cluster: Any,
    robust: bool | None,
    istate: Any,
    se_fit: bool,
    conf_int: float,
    conf_type: str,
    conf_lower: str,
    influence: Any,
    start_time: float | None,
    p0: np.ndarray | None,
    type_name: str | None,
    entry: bool,
    time0: bool,
) -> dict[str, Any]:
    if type_name is not None:
        if not isinstance(type_name, str):
            raise ValueError("type argument must be character")
        matched = _charmatch(type_name, _TYPE_NAMES)
        if matched is None:
            raise ValueError("invalid value for 'type'")
        type_code = _TYPE_CODES[matched]
    else:
        if int(ctype) not in (1, 2):
            raise ValueError("ctype must be 1 or 2")
        if int(stype) not in (1, 2):
            raise ValueError("stype must be 1 or 2")
        type_code = int(2 * int(stype) + int(ctype) - 2)
    if type_code != 1 or int(ctype) != 1:
        warnings.warn("only stype=1, ctype=1 implimented for multi-state data", stacklevel=3)
    if conf_lower != "usual":
        warnings.warn("conf.lower is ignored for multi-state data", stacklevel=3)

    influence_flag = _influence_flag(influence, se_fit)
    if robust is None:
        robust = True
    if not robust:
        raise ValueError("multi-state survfit supports only a robust variance")

    columns = np.array(y.columns, dtype=float, copy=True)
    ny = int(columns.shape[1])
    n = int(columns.shape[0])
    xcodes = _codes_array(x)
    if xcodes.shape[0] != n:
        raise ValueError("x and y must have the same length")
    supplied_id = _supplied(id)
    if ny == 3 and not supplied_id:
        raise ValueError("an id statement is required for start,stop data")
    check_id = _values(id) if supplied_id else list(range(1, n + 1))
    istate_arg = None if not _supplied(istate) else _values(istate)
    mcheck = _survcheck2(y, check_id, istate_arg)
    flags = mcheck["flag"]
    if flags["overlap"] > 0:
        raise ValueError("a subject has overlapping time intervals")
    if any(int(value) > 0 for value in flags.values()):
        raise ValueError("one or more flags are >0 in survcheck")

    states = list(mcheck["states"])
    nstate = len(states)
    if states != list(y.states):
        smap = [0] + [states.index(name) + 1 for name in y.states]
        status = columns[:, -1]
        remapped = np.array(status, copy=True)
        for i, code in enumerate(status):
            if not math.isnan(code):
                remapped[i] = smap[int(code)]
        columns[:, -1] = remapped

    istate_cat = mcheck["istate"]
    level_index = {name: i for i, name in enumerate(istate_cat.levels)}
    cstate = np.array([level_index[value] for value in istate_cat.values], dtype=np.int32)
    if p0 is not None:
        p0 = np.asarray(p0, dtype=float).reshape(-1)
        if p0.size != nstate:
            raise ValueError("wrong length for p0")
        if not np.isfinite(p0).all() or not math.isclose(float(p0.sum()), 1.0):
            raise ValueError("p0 must be a numeric vector that adds to 1")

    cluster_values = _values(cluster) if _supplied(cluster) else None
    if start_time is not None:
        if not math.isfinite(start_time):
            raise ValueError("start.time must be a single numeric value")
        stop_col = ny - 2
        cmax: dict[int, float] = {}
        for code, stop in zip(xcodes, columns[:, stop_col]):
            cmax[int(code)] = stop if int(code) not in cmax else max(cmax[int(code)], float(stop))
        if any(cmax.get(level, -math.inf) <= start_time for level in range(1, len(x.levels) + 1)):
            raise ValueError("start.time has removed all the observations from at least one curve")
        keep = columns[:, stop_col] >= start_time
        columns = columns[keep]
        xcodes = xcodes[keep]
        cstate = cstate[keep]
        if weights is not None:
            weights = np.asarray(weights, dtype=float).reshape(-1)[keep]
        if supplied_id:
            id = [value for value, flag in zip(_values(id), keep) if flag]
        if cluster_values is not None:
            cluster_values = [value for value, flag in zip(cluster_values, keep) if flag]
        istate_values = [value for value, flag in zip(istate_cat.values, keep) if flag]
        n = int(columns.shape[0])
    else:
        istate_values = list(istate_cat.values)

    if weights is None:
        weights = np.ones(n, dtype=float)
    else:
        weights = np.asarray(weights, dtype=float).reshape(-1).copy()
        if weights.shape[0] != n:
            raise ValueError("weights and y must have the same length")

    if supplied_id:
        id_codes, id_levels = _appearance(_values(id) if start_time is None else id)
    else:
        id_codes = list(range(1, n + 1))
        id_levels = [str(code) for code in id_codes]
    supplied_cluster = cluster_values is not None
    if supplied_cluster:
        cluster_codes, clname = _appearance(cluster_values)
        if supplied_id and _twoclust(id_codes, cluster_codes) == 1:
            warnings.warn("an id value appears on more than one cluster", stacklevel=3)
    elif supplied_id:
        cluster_codes, clname = id_codes, id_levels
    else:
        cluster_codes = list(range(1, n + 1))
        clname = [str(code) for code in cluster_codes]

    if ny == 2:
        samestate = all(value == istate_values[0] for value in istate_values)
        stemp = istate_values[0]
    else:
        samestate, stemp = _first_state(columns, xcodes, id_codes, istate_values)
    if p0 is None and samestate:
        p0 = np.zeros(nstate)
        p0[states.index(stemp)] = 1.0

    if start_time is not None:
        t0 = float(start_time)
    elif ny == 2:
        t0 = float(min(0.0, float(np.min(columns[:, 1]))))
    elif samestate:
        t0 = float(np.min(columns[:, 0]))
    else:
        mins: dict[int, float] = {}
        for ident, start in zip(id_codes, columns[:, 0]):
            if ident not in mins or start < mins[ident]:
                mins[ident] = float(start)
        idmin = np.array(list(mins.values()))
        if np.all(np.isclose(idmin, idmin[0])):
            t0 = float(idmin[0])
        else:
            observed = columns[:, 2] != 0
            t0 = float(np.min(columns[observed, 1]))
            for level in range(1, len(x.levels) + 1):
                block = columns[xcodes == level]
                if block.size == 0 or float(np.max(block[:, 1])) < t0 or float(np.min(block[:, 0])) >= t0:
                    raise ValueError(
                        "no obs overlap the default start time of "
                        + str(t0)
                        + " in at least one curve; specify a start.time"
                    )

    status_for_haz = columns[:, -1].copy()
    cstate_for_haz = cstate.copy()
    if ny == 2:
        entry = False
        min_y = float(np.min(columns[:, 0]))
        start_col = np.zeros(n) if min_y > 0 else np.full(n, 2.0 * min_y - 1.0)
        columns = np.column_stack([start_col, columns])
        position = np.full(n, 3, dtype=np.int32)
    else:
        position = np.asarray(_survflag(columns, id_codes, xcodes), dtype=np.int32)

    hindx, trmat, cname = _hindx(cstate_for_haz, status_for_haz, nstate)
    separm = 2 * influence_flag + (1 if se_fit else 0)
    xlev = list(x.levels)
    ncurve = len(xlev)
    order1 = np.lexsort((columns[:, 0], xcodes))
    order2 = np.lexsort((columns[:, 1], xcodes))
    counts = np.bincount(xcodes, minlength=ncurve + 1)[1:]
    breaks = np.cumsum(counts)
    starts = np.concatenate([[0], breaks[:-1]]).astype(int)

    curves: list[dict[str, Any]] = []
    for curve in range(ncurve):
        sort1 = order1[int(starts[curve]) : int(breaks[curve])]
        sort2 = order2[int(starts[curve]) : int(breaks[curve])]
        in_curve = xcodes == (curve + 1)
        event = columns[:, 2] > 0
        if entry:
            take_start = in_curve & ((position == 1) | (position == 3))
            take_stop = in_curve & (event | (position > 1))
            pieces = [columns[take_start, 0], columns[take_stop, 1]]
            utime = np.unique(np.concatenate(pieces)) if take_start.any() or take_stop.any() else np.array([])
        else:
            ignore = (position < 2) & (columns[:, 2] == 0)
            chosen = in_curve & ~ignore
            utime = np.unique(columns[chosen, 1]) if chosen.any() else np.array([])
        utime = np.asarray(utime, dtype=float)
        if time0:
            utime = np.concatenate([[t0], utime[utime > t0]])
        else:
            utime = utime[utime >= t0]

        present: list[int] = []
        seen_c: set[int] = set()
        for idx in np.flatnonzero(in_curve):
            code = int(cluster_codes[int(idx)])
            if code not in seen_c:
                seen_c.add(code)
                present.append(code)
        cluster_index = {code: i for i, code in enumerate(present)}
        c2 = np.zeros(n, dtype=np.int32)
        for i, code in enumerate(cluster_codes):
            c2[i] = cluster_index.get(int(code), 0)
        nclust = len(present)
        id_in = {int(id_codes[int(idx)]) for idx in np.flatnonzero(in_curve)}

        if p0 is None:
            if ny == 2:
                atrisk = in_curve
            elif t0 == float(np.min(columns[:, 0] if ny == 3 else status_for_haz)):
                atrisk = in_curve & (columns[:, 0] <= t0) & (columns[:, 1] >= t0)
            else:
                atrisk = in_curve & (columns[:, 0] < t0) & (columns[:, 1] >= t0)
            if not np.any(atrisk):
                raise ValueError(
                    "no one at risk for one of the curves, at the default time 0; specify a start.time"
                )
            wtsum = float(np.sum(weights[atrisk]))
            p00 = np.zeros(nstate)
            for state, weight in zip(cstate[atrisk], weights[atrisk]):
                p00[int(state)] += float(weight)
            p00 /= wtsum
            u0 = np.zeros((nclust, nstate))
            sd0 = None
            if np.all(p00 < 1) and separm > 0:
                rows = np.flatnonzero(in_curve)
                utemp = np.zeros((rows.size, nstate))
                for j in range(nstate):
                    temp = (cstate[rows] == j).astype(float) - p00[j]
                    utemp[:, j] = np.where(atrisk[rows], weights[rows] * temp, 0.0) / wtsum
                u0 = _rowsum(utemp, c2[rows])
                sd0 = np.sqrt(np.sum(u0 * u0, axis=0))
        else:
            p00 = np.asarray(p0, dtype=float)
            u0 = np.zeros((nclust, nstate))
            sd0 = None

        ntime = int(utime.size)
        if ntime == 0:
            fit = {
                "n.risk": np.zeros((0, nstate)),
                "n.event": np.zeros((0, nstate)),
                "n.censor": np.zeros((0, nstate)),
                "pstate": np.zeros((0, nstate)),
                "cumhaz": np.zeros((0, len(cname))),
                "n.transition": np.zeros((0, len(cname))),
                "n.risk.u": np.zeros((0, nstate)),
                "n.censor.u": np.zeros((0, nstate)),
                "n.transition.u": np.zeros((0, len(cname))),
            }
        else:
            i0 = np.ravel(np.asfortranarray(u0), order="F")
            raw = _survfitaj(
                np.ravel(np.asfortranarray(columns), order="F").tolist(),
                n,
                [int(v) for v in sort1],
                [int(v) for v in sort2],
                [float(v) for v in utime],
                [int(v) for v in cstate],
                [float(v) for v in weights],
                [int(v) for v in c2],
                nclust,
                [float(v) for v in p00],
                [float(v) for v in i0],
                int(separm),
                1 if entry else 0,
                [int(v) for v in position],
                [int(v) for v in hindx],
                [int(v) for v in trmat],
                float(t0),
            )
            (
                n_risk,
                n_event,
                n_censor,
                pstate,
                cumhaz,
                std_err,
                std_chaz,
                std_auc,
                influence_flat,
                n_enter,
                n_transition,
            ) = raw
            nhaz = len(cname)
            risk = _reshape(n_risk, ntime, 2 * nstate)
            trans = _reshape(n_transition, ntime, 2 * nhaz)
            censor = _reshape(n_censor, ntime, 2 * nstate)
            fit = {
                "n.risk": risk[:, :nstate],
                "n.risk.u": risk[:, nstate:],
                "n.event": _reshape(n_event, ntime, nstate),
                "n.censor": censor[:, :nstate],
                "n.censor.u": censor[:, nstate:],
                "pstate": _reshape(pstate, ntime, nstate),
                "cumhaz": _reshape(cumhaz, ntime, nhaz),
                "n.transition": trans[:, :nhaz],
                "n.transition.u": trans[:, nhaz:],
            }
            if entry:
                enter = _reshape(n_enter, ntime, 2 * nstate)
                fit["n.enter"] = enter[:, :nstate]
                fit["n.enter.u"] = enter[:, nstate:]
            if se_fit:
                fit["std.err"] = _reshape(std_err, ntime, nstate)
                fit["std.chaz"] = _reshape(std_chaz, ntime, nhaz)
                fit["std.auc"] = _reshape(std_auc, ntime, nstate)
            if influence_flag and influence_flat:
                arr = _reshape(influence_flat, nclust * nstate, ntime)
                arr = arr.reshape((nclust, nstate, ntime), order="F")
                fit["influence"] = np.transpose(arr, (0, 2, 1))
                fit["influence.names"] = [str(code) for code in present]
            if sd0 is not None and not time0:
                fit["sd0"] = sd0
        fit["n"] = int(sort1.size)
        fit["time"] = utime
        fit["n.id"] = len(id_in)
        fit["p0"] = p00
        curves.append(fit)

    weighted = not _weights_are_one(weights)
    out: dict[str, Any] = {
        "n": np.array([curve["n"] for curve in curves], dtype=float),
        "time": np.concatenate([curve["time"] for curve in curves]) if curves else np.array([]),
        "n.risk": _stack([curve["n.risk"] for curve in curves]),
        "n.event": _stack([curve["n.event"] for curve in curves]),
        "n.censor": _stack([curve["n.censor"] for curve in curves]),
        "pstate": _stack([curve["pstate"] for curve in curves]),
        "n.transition": _stack([curve["n.transition"] for curve in curves]),
        "n.id": np.array([curve["n.id"] for curve in curves], dtype=float),
        "cumhaz": _stack([curve["cumhaz"] for curve in curves]),
        "p0": curves[0]["p0"] if ncurve == 1 else np.vstack([curve["p0"] for curve in curves]),
        "states": states,
        "transitions": mcheck["transitions"],
        "type": y.type,
        "t0": float(t0),
        "cumhaz.names": cname,
    }
    if entry:
        out["n.enter"] = _stack([curve["n.enter"] for curve in curves])
    if weighted:
        out["counts"] = np.column_stack(
            [
                _stack([curve["n.risk.u"] for curve in curves]),
                _stack([curve["n.transition.u"] for curve in curves]),
                _stack([curve["n.censor.u"] for curve in curves]),
            ]
        )
    if ncurve > 1:
        out["strata"] = np.array([curve["time"].shape[0] for curve in curves], dtype=float)
        out["strata.names"] = xlev
    if se_fit:
        out["std.err"] = _stack([curve["std.err"] for curve in curves])
        out["std.chaz"] = _stack([curve["std.chaz"] for curve in curves])
        out["std.auc"] = _stack([curve["std.auc"] for curve in curves])
        out["logse"] = False
        if any("sd0" in curve for curve in curves):
            out["se0"] = _stack([curve.get("sd0", np.zeros(nstate)) for curve in curves])
        if conf_type != "none":
            ci = survfit_confint(out["pstate"], out["std.err"], logse=False, conf_type=conf_type, conf_int=conf_int)
            out["lower"] = ci["lower"]
            out["upper"] = ci["upper"]
            out["conf.type"] = conf_type
            out["conf.int"] = float(conf_int)
    if influence_flag and any("influence" in curve for curve in curves):
        if ncurve == 1:
            out["influence.pstate"] = curves[0].get("influence")
            out["influence.pstate.names"] = curves[0].get("influence.names")
        else:
            out["influence.pstate"] = [curve.get("influence") for curve in curves]
            out["influence.pstate.names"] = [curve.get("influence.names") for curve in curves]
    if start_time is not None:
        out["start.time"] = float(start_time)
    out["class_"] = ("survfitms", "survfit")
    return out


def survfit(
    x,
    y,
    weights=None,
    stype=1,
    ctype=1,
    id=None,
    cluster=None,
    robust=None,
    istate=None,
    entry=False,
    time0=False,
    se_fit=True,
    conf_int=0.95,
    conf_type=_CONF_TYPES,
    conf_lower=_CONF_LOWER,
    influence=False,
    start_time=None,
    p0=None,
    type=None,
):
    """One curve per level of `x` (survival::survfit).

    `y` is a `Surv` object. A factor status uses the Aalen-Johansen crate.
    A 0/1 status uses `survfitKM`. Left and interval censoring wait on
    `survfitTurnbull`.
    """
    if not isinstance(time0, (bool, np.bool_)):
        raise ValueError("time0 must be TRUE/FALSE")
    if not isinstance(entry, (bool, np.bool_)):
        raise ValueError("entry argument must be TRUE/FALSE")
    if isinstance(conf_int, (bool, np.bool_)):
        if not bool(conf_int):
            conf_type = "none"
        conf_int = 0.95
    else:
        conf_int = float(conf_int)
    conf_type = _match_arg(conf_type, _CONF_TYPES)
    conf_lower = _match_arg(conf_lower, _CONF_LOWER)
    if not is_Surv(y):
        raise ValueError("y must be a Surv object")
    if y.type in ("left", "interval"):
        raise NotImplementedError("waiting on survfitTurnbull")
    if y.type in ("right", "counting"):
        return survfitKM(
            x,
            y,
            weights=weights,
            stype=stype,
            ctype=ctype,
            se_fit=se_fit,
            conf_int=conf_int,
            conf_type=conf_type,
            conf_lower=conf_lower,
            start_time=start_time,
            id=id,
            cluster=cluster,
            robust=robust,
            influence=influence,
            type=type,
            entry=bool(entry),
            time0=bool(time0),
        )
    if y.type in ("mright", "mcounting"):
        if not isinstance(x, StrataFactor):
            raise ValueError("x must be a factor")
        start = None if start_time is None else float(np.asarray(start_time, dtype=float).reshape(-1)[0])
        return _survfit_aj(
            x,
            y,
            None if weights is None else np.asarray(weights, dtype=float),
            int(stype),
            int(ctype),
            id,
            cluster,
            robust,
            istate,
            bool(se_fit),
            float(conf_int),
            conf_type,
            conf_lower,
            influence,
            start,
            None if p0 is None else np.asarray(p0, dtype=float),
            type,
            bool(entry),
            bool(time0),
        )
    raise ValueError("unrecognized survival type")
