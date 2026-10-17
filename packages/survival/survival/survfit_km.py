"""Kaplan–Meier curves for a single endpoint (survival::survfitKM).

The curve, hazard, and robust variance come from the survfitkm crate
(`Csurvfitkm` in survival 3.8-12 `src/survfitkm.c`). `x` is a factor
(`StrataFactor`); `y` is a right-censored or counting-process `Surv` object.
"""

from __future__ import annotations

import math
import warnings
from typing import Any

import numpy as np
from survfitkm import survfitkm as _survfitkm

from survival.strata import StrataFactor
from survival.surv import is_Surv
from survival.survfit_confint import survfit_confint

_CONF_TYPES = ("log", "log-log", "plain", "none", "logit", "arcsin")
_CONF_LOWER = ("usual", "peto", "modified")
_TYPE_NAMES = ("kaplan-meier", "fleming-harrington", "fh2")
_TYPE_CODES = (1, 3, 4)
_TOL = math.sqrt(np.finfo(float).eps)


def _match_arg(value: Any, choices: tuple[str, ...]) -> str:
    if isinstance(value, (list, tuple)) and tuple(value) == choices:
        return choices[0]
    if value in choices:
        return value
    hits = [choice for choice in choices if choice.startswith(str(value))]
    if len(hits) == 1:
        return hits[0]
    raise ValueError("'" + str(value) + "' should be one of " + ", ".join(repr(c) for c in choices))


def _charmatch(value: str, choices: tuple[str, ...]) -> int | None:
    if value in choices:
        return choices.index(value)
    hits = [i for i, choice in enumerate(choices) if choice.startswith(value)]
    if len(hits) == 1:
        return hits[0]
    return None


def _label(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _values(column: Any) -> list[Any]:
    if column is None:
        return []
    if isinstance(column, StrataFactor):
        return [None if code is None else column.levels[code - 1] for code in column.codes]
    if isinstance(column, np.ndarray):
        return column.reshape(-1).tolist()
    if isinstance(column, str):
        return [column]
    return list(column)


def _appearance(values: list[Any]) -> tuple[list[int], list[str]]:
    """factor(x, unique(x)): levels in order of first appearance."""
    index: dict[str, int] = {}
    levels: list[str] = []
    codes: list[int] = []
    for value in values:
        label = _label(value)
        code = index.get(label)
        if code is None:
            code = len(levels) + 1
            index[label] = code
            levels.append(label)
        codes.append(code)
    return codes, levels


def _any_duplicated(codes: list[int]) -> bool:
    seen: set[int] = set()
    for code in codes:
        if code in seen:
            return True
        seen.add(code)
    return False


def _weights_are_one(weights: np.ndarray) -> bool:
    if weights.size == 0:
        return True
    diff = float(np.mean(np.abs(weights - 1.0)))
    return diff <= _TOL


def _survflag(y: np.ndarray, id_codes: list[int], group_codes: np.ndarray) -> np.ndarray:
    """1 = first interval of a subject, 2 = last, 3 = both. Data order."""
    n = y.shape[0]
    if n == 0:
        return np.array([], dtype=int)
    start = y[:, 0]
    stop = y[:, 1]
    id_arr = np.asarray(id_codes, dtype=int)
    group = np.asarray(group_codes, dtype=int)
    indx = np.lexsort((stop, id_arr, group))
    id2 = id_arr[indx]
    group2 = group[indx]
    if n == 1:
        flag_sorted = np.array([3], dtype=int)
    else:
        newid = (id2[:-1] != id2[1:]) | (group2[:-1] != group2[1:])
        gap = stop[indx][:-1] < start[indx][1:]
        breaks = newid | gap
        flag_sorted = np.concatenate([[True], breaks]).astype(int) + 2 * np.concatenate(
            [breaks, [True]]
        ).astype(int)
    flag = np.empty(n, dtype=int)
    flag[indx] = flag_sorted
    return flag


def _n_lag(n_event: np.ndarray, n_risk: np.ndarray, strata: np.ndarray | None) -> np.ndarray:
    """Risk set at the previous event, or at the first time of each curve."""
    events = np.asarray(n_event, dtype=float) > 0
    events = events.copy()
    if strata is None or len(strata) <= 1:
        if events.size:
            events[0] = True
    else:
        starts = np.cumsum(np.concatenate([[0], np.asarray(strata, dtype=int)[:-1]])).astype(int)
        for start in starts:
            if 0 <= int(start) < events.size:
                events[int(start)] = True
    if events.size == 0:
        return np.array([], dtype=float)
    positions = np.flatnonzero(events) + 1
    times = np.diff(np.concatenate([positions, [events.size + 1]])).astype(int)
    return np.repeat(np.asarray(n_risk, dtype=float)[events], times)


def _kernel(columns, weights, sort1, sort2, type_code, id0, nid, position, influence, entry, utime):
    flat = np.ravel(np.asfortranarray(columns, dtype=float), order="F")
    nrows, ny = columns.shape
    sort1_list = [] if sort1 is None else [int(v) for v in np.asarray(sort1).reshape(-1)]
    result = _survfitkm(
        flat.tolist(),
        int(nrows),
        int(ny),
        np.asarray(weights, dtype=float).reshape(-1).tolist(),
        sort1_list,
        [int(v) for v in np.asarray(sort2).reshape(-1)],
        int(type_code),
        [] if nid == 0 else [int(v) for v in np.asarray(id0).reshape(-1)],
        int(nid),
        [int(v) for v in np.asarray(position).reshape(-1)],
        int(influence),
        0,
        1 if entry else 0,
        [float(v) for v in np.asarray(utime, dtype=float).reshape(-1)],
    )
    time, n_flat, n_cols, est_flat, std_flat, inf1, inf2 = result
    ntime = len(time)
    n_mat = np.array(n_flat, dtype=float).reshape((ntime, int(n_cols)), order="F")
    estimate = np.array(est_flat, dtype=float).reshape((ntime, 2), order="F")
    std = np.array(std_flat, dtype=float).reshape((ntime, 2), order="F")
    influence1 = None
    influence2 = None
    if inf1:
        influence1 = np.array(inf1, dtype=float).reshape((int(nid), ntime), order="F")
    if inf2:
        influence2 = np.array(inf2, dtype=float).reshape((int(nid), ntime), order="F")
    return {
        "time": np.asarray(time, dtype=float),
        "n": n_mat,
        "estimate": estimate,
        "std": std,
        "influence1": influence1,
        "influence2": influence2,
    }


def _times_right(columns, rows):
    time = columns[rows, 0]
    sort2 = rows[np.argsort(time, kind="mergesort")]
    utime = np.unique(time)
    return None, sort2, utime


def _times_counting(columns, rows, position, entry):
    start = columns[rows, 0]
    stop = columns[rows, 1]
    sort1 = rows[np.argsort(start, kind="mergesort")]
    sort2 = rows[np.argsort(stop, kind="mergesort")]
    status = columns[:, 2]
    if entry:
        if rows.shape[0] == columns.shape[0] and np.all(rows == np.arange(columns.shape[0])):
            u1 = columns[(position == 1) | (position == 3), 0]
            u2 = columns[(status == 1) | (position > 1), 1]
        else:
            mask = np.zeros(columns.shape[0], dtype=bool)
            mask[rows] = True
            u1 = columns[mask & ((position == 1) | (position == 3)), 0]
            u2 = columns[mask & (position > 1), 1]
        pieces = [u1, u2]
        utime = np.unique(np.concatenate(pieces)) if u1.size or u2.size else np.array([], dtype=float)
    else:
        if rows.shape[0] == columns.shape[0] and np.all(rows == np.arange(columns.shape[0])):
            mask = (status == 1) | (position > 1)
            utime = np.unique(columns[mask, 1])
        else:
            chosen = rows[position[rows] > 1]
            utime = np.unique(columns[chosen, 1]) if chosen.size else np.array([], dtype=float)
    return sort1, sort2, utime


def _curve(columns, weights, position, type_code, cluster_codes, ncluster, influence, entry, rows, counting):
    if counting:
        sort1, sort2, utime = _times_counting(columns, rows, position, entry)
    else:
        sort1, sort2, utime = _times_right(columns, rows)
    id0 = []
    nid = 0
    if ncluster > 0:
        id0 = np.asarray(cluster_codes, dtype=int) - 1
        nid = int(ncluster)
    return _kernel(
        columns, weights, sort1, sort2, type_code, id0, nid, position, influence, entry, utime
    )


def _attach_influence(rval, curves, rownames, type_code, influence, single):
    if influence <= 0:
        return

    def pack(which):
        if single:
            matrix = curves[0][which]
            names = rownames[0]
            return matrix, names
        matrices = []
        names = []
        for curve, name in zip(curves, rownames):
            if curve is None:
                raise ValueError("influence requested for an empty curve")
            matrices.append(curve[which])
            names.append(name)
        return matrices, names

    if type_code in (1, 2):
        if influence in (1, 3):
            matrix, names = pack("influence1")
            rval["influence.surv"] = matrix
            rval["influence.surv.rownames"] = names
        if influence in (2, 3):
            matrix, names = pack("influence2")
            rval["influence.chaz"] = matrix
            rval["influence.chaz.rownames"] = names
        return

    matrix, names = pack("influence2")
    if influence in (2, 3):
        rval["influence.chaz"] = matrix
        rval["influence.chaz.rownames"] = names
    if influence in (1, 3):
        if single:
            surv = curves[0]["estimate"][:, 0]
            rval["influence.surv"] = -matrix * surv[np.newaxis, :]
            rval["influence.surv.rownames"] = names
        else:
            derived = []
            for curve, chaz in zip(curves, matrix):
                surv = curve["estimate"][:, 0]
                derived.append(-chaz * surv[np.newaxis, :])
            rval["influence.surv"] = derived
            rval["influence.surv.rownames"] = names


def survfitKM(
    x,
    y,
    weights=None,
    stype=1,
    ctype=1,
    se_fit=True,
    conf_int=0.95,
    conf_type=_CONF_TYPES,
    conf_lower=_CONF_LOWER,
    start_time=None,
    id=None,
    cluster=None,
    robust=None,
    influence=False,
    type=None,
    entry=False,
    time0=False,
):
    """One survival curve per level of `x` (survival::survfitKM).

    `time0` is accepted and ignored, as in the R function. Confidence limits
    use `survfit_confint`.
    """
    del time0
    if type is not None:
        if not isinstance(type, str):
            raise ValueError("type argument must be character")
        matched = _charmatch(type, _TYPE_NAMES)
        if matched is None:
            raise ValueError("invalid value for 'type'")
        type_code = _TYPE_CODES[matched]
    else:
        if int(stype) not in (1, 2):
            raise ValueError("stype must be 1 or 2")
        if int(ctype) not in (1, 2):
            raise ValueError("ctype must be 1 or 2")
        type_code = int(2 * int(stype) + int(ctype) - 2)

    conf_type = _match_arg(conf_type, _CONF_TYPES)
    conf_lower = _match_arg(conf_lower, _CONF_LOWER)
    if isinstance(conf_int, bool):
        if not conf_int:
            conf_type = "none"
        conf_int = 0.95
    else:
        conf_int = float(conf_int)
    if not isinstance(entry, bool):
        raise ValueError("entry argument must be TRUE/FALSE")
    if not is_Surv(y):
        raise ValueError("y must be a Surv object")
    if y.type not in ("right", "counting"):
        raise ValueError("Can only handle right censored or counting data")
    if not isinstance(x, StrataFactor):
        raise ValueError("x must be a factor")

    columns = np.array(y.columns, dtype=float, copy=True)
    ny = int(columns.shape[1])
    xlev = list(x.levels)
    xcodes = [None if code is None else int(code) for code in x.codes]
    if len(xcodes) != columns.shape[0]:
        raise ValueError("x and y must have the same length")

    id_values = _values(id) if id is not None else None
    cluster_values = _values(cluster) if cluster is not None else None
    weights_given = weights is not None
    if weights is None:
        weights = np.ones(len(xcodes), dtype=float)
    else:
        weights = np.asarray(weights, dtype=float).reshape(-1).copy()
        if weights.shape[0] != len(xcodes):
            raise ValueError("weights and x must have the same length")
    if id_values is not None and len(id_values) not in (0, len(xcodes)):
        raise ValueError("id and y must have the same length")
    if cluster_values is not None and len(cluster_values) not in (0, len(xcodes)):
        raise ValueError("cluster and y must have the same length")

    if start_time is None:
        t0 = float(min(0.0, np.min(columns[:, :-1]))) if columns.size else 0.0
    else:
        start = np.asarray(start_time, dtype=float).reshape(-1)
        if start.size != 1:
            raise ValueError("start.time must be a single numeric value")
        t0 = float(start[0])

    keep = columns[:, ny - 2] >= t0
    if not np.all(keep):
        if not np.any(keep):
            raise ValueError("all observations removed by start.time")
        columns = columns[keep]
        xcodes = [code for code, flag in zip(xcodes, keep) if flag]
        weights = weights[keep]
        if id_values:
            id_values = [value for value, flag in zip(id_values, keep) if flag]
        if cluster_values:
            cluster_values = [value for value, flag in zip(cluster_values, keep) if flag]

    n = columns.shape[0]
    has_cluster = bool(cluster_values)
    has_id = bool(id_values)
    has_rwt = bool(weights_given and np.any(weights != np.floor(weights)))
    robust_given = robust is not None
    if has_id:
        id_codes, id_levels = _appearance(id_values)
    else:
        id_codes, id_levels = [], []
        entry = False

    if robust is None:
        if influence:
            robust = True
            if not (has_cluster or has_id):
                cluster_values = list(range(1, n + 1))
                has_cluster = True
        elif has_cluster or has_rwt or (
            has_id and _any_duplicated([code for code, status in zip(id_codes, columns[:, -1]) if status == 1.0])
        ):
            robust = True
        else:
            robust = False
    if not isinstance(robust, bool):
        raise ValueError("robust must be TRUE/FALSE")

    clname: list[str] | None
    cluster_codes: list[int] | None
    if has_cluster:
        if not robust:
            warnings.warn("cluster specified with robust=FALSE, cluster ignored", stacklevel=2)
            ncluster = 0
            clname = None
            cluster_codes = None
        else:
            cluster_codes, clname = _appearance(cluster_values)
            ncluster = len(clname)
    elif robust:
        if has_id:
            clname = list(id_levels)
            cluster_codes = list(id_codes)
            ncluster = len(clname)
        elif ny == 2 or not robust_given:
            cluster_codes = list(range(1, n + 1))
            clname = [str(i) for i in cluster_codes]
            ncluster = n
        else:
            raise ValueError("id or cluster option required")
    else:
        ncluster = 0
        clname = None
        cluster_codes = None

    if isinstance(influence, bool):
        influence = 0 if not influence else 3
    elif isinstance(influence, (int, np.integer)):
        influence = int(influence)
    else:
        raise ValueError("influence argument must be numeric or logical")
    if influence not in (0, 1, 2, 3):
        raise ValueError("influence argument must be 0, 1, 2, or 3")
    if not robust and influence > 0:
        warnings.warn("robust=FALSE implies influence=FALSE", stacklevel=2)
        influence = 0
    if not se_fit:
        ncluster = 0
        influence = 0
    if (not has_id) or ny == 2:
        entry = False

    x_arr = np.array([0 if code is None else code for code in xcodes], dtype=int)
    if ny == 3 and has_id:
        position = _survflag(columns, id_codes, x_arr)
    else:
        position = np.full(n, 3, dtype=int)
    counting = ny == 3

    def rownames_for(unique_codes: list[int]) -> list[str]:
        assert clname is not None
        return [clname[code - 1] for code in unique_codes]

    if len(xlev) == 1:
        rows = np.arange(n, dtype=int)
        n_used = np.array([n], dtype=int)
        n_id = np.array([len(set(id_codes))], dtype=int) if has_id else None
        cfit = _curve(
            columns, weights, position, type_code, cluster_codes, ncluster, influence, entry, rows, counting
        )
        curves = [cfit]
        curve_names = [list(clname)] if influence > 0 and clname is not None else [None]
        strata = None
    else:
        ngroup = len(xlev)
        n_used = np.zeros(ngroup, dtype=int)
        n_id = np.zeros(ngroup, dtype=int) if has_id else None
        curves = []
        curve_names = []
        base_codes = list(cluster_codes) if cluster_codes is not None else None
        for group in range(1, ngroup + 1):
            keep_rows = np.flatnonzero(x_arr == group)
            n_used[group - 1] = int(keep_rows.size)
            if keep_rows.size == 0:
                curves.append(None)
                curve_names.append(None)
                continue
            if has_id and n_id is not None:
                n_id[group - 1] = len({id_codes[int(row)] for row in keep_rows})
            group_codes = base_codes
            group_n = ncluster
            names: list[str] | None = list(clname) if clname is not None else None
            if ncluster > 0 and base_codes is not None:
                seen: dict[int, int] = {}
                unique_codes: list[int] = []
                mapped = [0] * n
                for row in keep_rows:
                    code = base_codes[int(row)]
                    slot = seen.get(code)
                    if slot is None:
                        slot = len(unique_codes)
                        seen[code] = slot
                        unique_codes.append(code)
                    mapped[int(row)] = slot + 1
                group_codes = mapped
                group_n = len(unique_codes)
                names = rownames_for(unique_codes) if influence > 0 else None
            cfit = _curve(
                columns,
                weights,
                position,
                type_code,
                group_codes,
                group_n,
                influence,
                entry,
                keep_rows.astype(int),
                counting,
            )
            curves.append(cfit)
            curve_names.append(names)
        strata = np.array(
            [0 if curve is None else int(curve["time"].shape[0]) for curve in curves], dtype=int
        )

    def stacked(getter):
        parts = []
        for curve in curves:
            if curve is None:
                continue
            parts.append(getter(curve))
        if not parts:
            return np.array([], dtype=float)
        return np.concatenate(parts)

    single = len(xlev) == 1
    rval: dict[str, Any] = {
        "n": n_used,
        "time": stacked(lambda curve: curve["time"]),
        "n.risk": stacked(lambda curve: curve["n"][:, 3]),
        "n.event": stacked(lambda curve: curve["n"][:, 4]),
        "n.censor": stacked(lambda curve: curve["n"][:, 5]),
        "surv": stacked(lambda curve: curve["estimate"][:, 0]),
        "cumhaz": stacked(lambda curve: curve["estimate"][:, 1]),
    }
    if se_fit:
        rval["std.err"] = stacked(lambda curve: curve["std"][:, 0])
        rval["std.chaz"] = stacked(lambda curve: curve["std"][:, 1])
    if entry:
        rval["n.enter"] = stacked(lambda curve: curve["n"][:, 7])
    if not _weights_are_one(weights):
        cols = [0, 1, 2, 6] if entry else [0, 1, 2]
        blocks = []
        for curve in curves:
            if curve is None:
                raise ValueError("cannot stack counts for an empty curve")
            blocks.append(curve["n"][:, cols])
        rval["counts"] = blocks[0] if single else np.vstack(blocks)
    if strata is not None:
        rval["strata"] = strata
        rval["strata.names"] = list(xlev)
    if has_id and n_id is not None:
        rval["n.id"] = n_id
    rval["type"] = "counting" if counting else "right"

    if se_fit:
        logse = bool(ncluster == 0 or type_code in (2, 4))
        rval["logse"] = logse
        rval["conf.int"] = float(conf_int)
        rval["conf.type"] = conf_type
        if conf_lower != "usual":
            rval["conf.lower"] = conf_lower
        if conf_lower == "modified":
            n_lag = _n_lag(rval["n.event"], rval["n.risk"], strata)
        else:
            n_lag = None
        with np.errstate(divide="ignore", invalid="ignore"):
            if conf_lower == "usual":
                std_low = rval["std.err"]
            elif conf_lower == "peto":
                std_low = np.sqrt((1.0 - rval["surv"]) / rval["n.risk"])
            else:
                std_low = rval["std.err"] * np.sqrt(n_lag / rval["n.risk"])
        if conf_type != "none":
            limits = survfit_confint(
                rval["surv"],
                rval["std.err"],
                logse=logse,
                conf_type=conf_type,
                conf_int=float(conf_int),
                selow=std_low,
            )
            rval["lower"] = limits["lower"]
            rval["upper"] = limits["upper"]
    rval["t0"] = float(t0)
    _attach_influence(rval, curves, curve_names, type_code, influence, single)
    return rval
