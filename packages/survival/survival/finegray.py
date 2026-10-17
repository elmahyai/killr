"""Fine-Gray competing-risks data (survival::finegray)."""

from __future__ import annotations

import math
import re
import warnings
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from survival.fromtimeline import Categorical, TimelineFrame
from survival.strata import StrataFactor, strata as strata_fn
from survival.surv import Surv, SurvObject, aeqSurv, is_Surv
from survival.surv_split import (
    _apply_subset,
    _as_table,
    _column_len,
    _make_names,
    _parse_surv_lhs,
)
from survival.untangle_specials import untangle_specials


def _split_rhs_terms(rhs: str) -> list[str]:
    parts: list[str] = []
    depth = 0
    start = 0
    for i, ch in enumerate(rhs):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "+" and depth == 0:
            parts.append(rhs[start:i].strip())
            start = i + 1
    parts.append(rhs[start:].strip())
    return [part for part in parts if part]


def _parse_strata_term(term: str) -> list[str]:
    m = re.match(r"strata\s*\((.*)\)\s*$", term.strip(), flags=re.IGNORECASE)
    if not m:
        return []
    inner = m.group(1).strip()
    if not inner:
        return []
    depth = 0
    args: list[str] = []
    start = 0
    for i, ch in enumerate(inner):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        elif ch == "," and depth == 0:
            args.append(inner[start:i].strip())
            start = i + 1
    args.append(inner[start:].strip())
    return [a for a in args if a]


def _find_interval(values, cuts, *, left_open: bool = False) -> np.ndarray:
    """R findInterval on numeric cutpoints (1-based when left_open is False)."""
    values = np.asarray(values, dtype=float)
    cuts = np.asarray(cuts, dtype=float)
    if left_open:
        index = np.searchsorted(cuts, values, side="left")
    else:
        index = np.searchsorted(cuts, values, side="right")
    out = index.astype(int)
    out[np.isnan(values)] = -1
    return out


def _cfinegray(
    tstart: np.ndarray,
    tstop: np.ndarray,
    ctime: np.ndarray,
    cprob: np.ndarray,
    extend: np.ndarray,
    keep: np.ndarray,
) -> dict[str, np.ndarray]:
    n = tstart.shape[0]
    ncut = cprob.shape[0]
    extra = 0
    for i in range(n):
        if math.isfinite(tstart[i]) and math.isfinite(tstop[i]) and extend[i]:
            j = 0
            while j < ncut and ctime[j] < tstop[i]:
                j += 1
            j += 1
            for jj in range(j, ncut):
                if keep[jj]:
                    extra += 1
    n2 = n + extra
    row = np.zeros(n2, dtype=int)
    start = np.zeros(n2, dtype=float)
    end = np.zeros(n2, dtype=float)
    wt = np.zeros(n2, dtype=float)
    add = np.zeros(n2, dtype=int)
    k = 0
    for i in range(n):
        start[k] = tstart[i]
        end[k] = tstop[i]
        row[k] = i + 1
        wt[k] = 1.0
        add[k] = 0
        if math.isfinite(tstart[i]) and math.isfinite(tstop[i]) and extend[i]:
            j = 0
            while j < ncut and ctime[j] < tstop[i]:
                j += 1
            end[k] = ctime[j]
            tempwt = cprob[j]
            j += 1
            iadd = 0
            for jj in range(j, ncut):
                if keep[jj]:
                    k += 1
                    iadd += 1
                    row[k] = i + 1
                    start[k] = ctime[jj - 1]
                    end[k] = ctime[jj]
                    wt[k] = cprob[jj] / tempwt
                    add[k] = iadd
        k += 1
    return {"row": row, "start": start, "end": end, "wt": wt, "add": add}


def _survfit_km_one(y: np.ndarray, wt: np.ndarray) -> dict[str, np.ndarray]:
    n = y.shape[0]
    time1 = y[:, 0]
    time2 = y[:, 1]
    status = y[:, 2]
    position = np.full(n, 3, dtype=int)
    event = status == 1
    utime = np.sort(np.unique(time2[event | (position > 1)]))
    sort2 = np.argsort(time2, kind="mergesort")
    sort1 = np.argsort(time1, kind="mergesort")
    ntime = utime.size
    n1 = 0
    wt1 = 0.0
    person1 = n - 1
    person2 = n - 1
    nmat = np.zeros((ntime, 6), dtype=float)
    for k in range(ntime - 1, -1, -1):
        dt = utime[k]
        n2 = n3 = 0
        wt2 = wt3 = 0.0
        while person2 >= 0:
            i2 = sort2[person2]
            if time2[i2] < dt:
                break
            n1 += 1
            wt1 += wt[i2]
            if status[i2] == 1:
                n2 += 1
                wt2 += wt[i2]
            elif position[i2] & 2:
                n3 += 1
                wt3 += wt[i2]
            person2 -= 1
        while person1 >= 0:
            i1 = sort1[person1]
            if time1[i1] < dt:
                break
            n1 -= 1
            wt1 -= wt[i1]
            person1 -= 1
        nmat[k, :] = (n1, n2, n3, wt1, wt2, wt3)
    km = 1.0
    surv = np.zeros(ntime, dtype=float)
    for i in range(ntime):
        d1 = nmat[i, 4]
        nrisk = nmat[i, 3]
        if nmat[i, 1] > 0 and d1 > 0:
            km *= (nrisk - d1) / nrisk
        surv[i] = km
    return {"time": utime, "n.event": nmat[:, 1], "surv": surv}


def _survfit_km(y: np.ndarray, istrat: np.ndarray, wt: np.ndarray) -> dict[int, dict[str, np.ndarray]]:
    maxstrat = int(np.max(istrat))
    out: dict[int, dict[str, np.ndarray]] = {}
    for i in range(1, maxstrat + 1):
        keep = istrat == i
        if not np.any(keep):
            continue
        out[i] = _survfit_km_one(y[keep], wt[keep])
    return out


def _build_terms(formula_text: str, mf_names: list[str]) -> dict[str, Any]:
    covars = [name for name in mf_names if name != mf_names[0]]
    nrows = len(covars) + 1
    matrix = [[0] * len(covars) for _ in range(nrows)]
    for j, name in enumerate(covars):
        if name.startswith("strata("):
            matrix[nrows - 1][j] = 1
        else:
            matrix[j + 1][j] = 1
    specials: dict[str, list[int]] = {}
    for j, name in enumerate(covars):
        if name.startswith("strata("):
            specials["strata"] = [j + 2]
    return {
        "response": 1,
        "order": [1] * len(covars),
        "factors": {"matrix": matrix, "rownames": [mf_names[0], *covars], "colnames": covars},
        "specials": specials,
    }


def _as_numeric_strata(strata_obj: StrataFactor | Any) -> np.ndarray:
    if isinstance(strata_obj, StrataFactor):
        codes = []
        for code in strata_obj.codes:
            codes.append(1 if code is None else int(code))
        return np.asarray(codes, dtype=int)
    return np.asarray(strata_obj, dtype=int)


@dataclass
class FinegrayFrame:
    names: list[str]
    columns: list[Any]
    event: str = ""
    specials: dict[str, Any] = field(default_factory=dict)

    def __len__(self) -> int:
        return _column_len(self.columns[0]) if self.columns else 0


def _covariate_columns(mf: TimelineFrame) -> tuple[list[str], list[Any]]:
    names: list[str] = []
    cols: list[Any] = []
    for name, col in zip(mf.names, mf.columns):
        if name == mf.names[0]:
            continue
        if name.startswith("(") or re.match(r"strata\s*\(", name, flags=re.IGNORECASE):
            continue
        names.append(name)
        cols.append(col)
    return names, cols


def _subset_rows_col(col: Any, keep: np.ndarray) -> Any:
    if isinstance(col, Categorical):
        return Categorical([col.values[i] for i in range(len(col.values)) if keep[i]], col.levels)
    if isinstance(col, np.ndarray):
        return col[keep]
    return [col[i] for i in range(len(col)) if keep[i]]


def _select_rows(cols: list[Any], row_idx: np.ndarray) -> list[Any]:
    idx = row_idx.astype(int) - 1
    out: list[Any] = []
    for col in cols:
        if isinstance(col, Categorical):
            out.append(Categorical([col.values[i] for i in idx], col.levels))
        elif isinstance(col, np.ndarray):
            out.append(col[idx])
        elif isinstance(col, (list, tuple)):
            out.append([col[i] for i in idx])
        else:
            out.append(col)
    return out


def _build_finegray_response(table: dict[str, Any], lhs_names: list[str]) -> SurvObject:
    if len(lhs_names) == 2:
        end_name, event_name = lhs_names
        event = table[event_name]
        if isinstance(event, Categorical):
            event = event.values
        return Surv(table[end_name], event=event)
    start_name, end_name, event_name = lhs_names
    event = table[event_name]
    if isinstance(event, Categorical):
        event = event.values
    return Surv(table[start_name], table[end_name], event=event)


def _build_model_frame(
    formula_text: str,
    data: Mapping[str, Any] | TimelineFrame,
    *,
    subset=None,
    weights=None,
    id=None,
) -> TimelineFrame:
    if "~" not in formula_text:
        raise ValueError("A formula argument is required")
    lhs, rhs = formula_text.split("~", 1)
    is_surv2, lhs_names = _parse_surv_lhs(lhs)
    if is_surv2:
        raise ValueError("Response must be a survival object")
    table = _as_table(data)
    table, _ = _apply_subset(table, subset)
    response = _build_finegray_response(table, lhs_names)
    used = set(lhs_names)
    rhs_terms = _split_rhs_terms(rhs.strip())
    covariate_names: list[str] = []
    strata_terms: list[str] = []
    for term in rhs_terms:
        if term == ".":
            covariate_names.extend(name for name in table if name not in used)
        elif re.match(r"cluster\s*\(", term, flags=re.IGNORECASE):
            raise ValueError("a cluster() term is not valid")
        elif re.match(r"strata\s*\(", term, flags=re.IGNORECASE):
            inner = _parse_strata_term(term)
            for var in inner:
                if var not in table:
                    raise ValueError(f"variable {var!r} not found in data")
            strata_terms.append(term)
            for var in inner:
                if var not in covariate_names:
                    covariate_names.append(var)
        else:
            if term not in table:
                raise ValueError(f"variable {term!r} not found in data")
            covariate_names.append(term)
    seen: set[str] = set()
    ordered_covars: list[str] = []
    for name in covariate_names:
        if name not in seen and name not in used:
            seen.add(name)
            ordered_covars.append(name)
    mf_names = [lhs.strip(), *ordered_covars]
    if strata_terms:
        mf_names.extend(strata_terms)
    mf_cols: list[Any] = [response]
    for name in ordered_covars:
        mf_cols.append(table[name])
    for st in strata_terms:
        args = _parse_strata_term(st)
        if len(args) == 1:
            mf_cols.append(strata_fn(table[args[0]]))
        else:
            mf_cols.append(strata_fn(*[table[a] for a in args], shortlabel=True))
    if id is not None:
        if not isinstance(id, str) or id not in table:
            raise ValueError(f"id variable {id!r} not found in data")
        mf_names.append("(id)")
        mf_cols.append(table[id])
    if weights is not None:
        if isinstance(weights, str):
            if weights not in table:
                raise ValueError(f"weights variable {weights!r} not found in data")
            wt_col = table[weights]
        else:
            wt_col = np.asarray(weights, dtype=float)
        mf_names.append("(weights)")
        mf_cols.append(wt_col)
    return TimelineFrame(mf_names, mf_cols, {})


def finegray(
    formula,
    data=None,
    weights=None,
    subset=None,
    na_action=None,
    etype=None,
    prefix="fg",
    count=None,
    id=None,
    timefix=True,
):
    """Create augmented data for a Fine-Gray subdistribution hazards model."""
    if data is None and isinstance(formula, str):
        raise ValueError("a data argument is required")
    if not isinstance(formula, str):
        raise ValueError("A formula argument is required")
    if na_action is not None and na_action not in (None, "na.pass"):
        raise NotImplementedError("only na.pass is supported")
    mf = _build_model_frame(formula, data, subset=subset, weights=weights, id=id)
    Y = mf.columns[0]
    if len(mf) == 0:
        raise ValueError("No (non-missing) observations")
    if not is_Surv(Y):
        raise ValueError("Response must be a survival object")
    if Y.type not in ("mright", "mcounting"):
        raise ValueError("Fine-Gray model requires a multi-state survival")
    states = Y.states
    if states is None or len(states) < 2:
        raise ValueError("survival time has only a single state")
    if timefix:
        Y = aeqSurv(Y)
    terms = _build_terms(formula, mf.names)
    stemp = untangle_specials(terms, "strata", 1)
    if stemp.get("vars"):
        varnames = stemp["vars"]
        if len(varnames) == 1:
            st_col = mf.columns[mf.names.index(varnames[0])]
        else:
            cols = [mf.columns[mf.names.index(v)] for v in varnames if v in mf.names]
            st_col = strata_fn(*cols, shortlabel=True)
        istrat = _as_numeric_strata(st_col)
        drop_names = set(varnames)
        keep_idx = [i for i, name in enumerate(mf.names) if name not in drop_names]
        mf = TimelineFrame([mf.names[i] for i in keep_idx], [mf.columns[i] for i in keep_idx], mf.specials)
    else:
        istrat = np.ones(len(mf), dtype=int)
    id_col = None
    if id is not None:
        if isinstance(id, str):
            id_col = mf.columns[mf.names.index("(id)")]
    wt_col = None
    if "(weights)" in mf.names:
        wt_col = mf.columns[mf.names.index("(weights)")]
    user_weights = np.ones(len(mf), dtype=float) if wt_col is None else np.asarray(wt_col, dtype=float).reshape(-1)
    cluster = untangle_specials(terms, "cluster", 1)
    if cluster.get("vars"):
        raise ValueError("a cluster() term is not valid")
    ymat = np.array(Y.matrix(), dtype=float, copy=True)
    nY = ymat.shape[1]
    delay = False
    first = last = None
    if Y.type == "mcounting":
        if id_col is None:
            raise ValueError("(start, stop] data requires a subject id")
        id_arr = np.asarray(id_col)
        index = np.lexsort((ymat[:, 1], id_arr))
        sorty = ymat[index]
        first_idx = np.flatnonzero(np.diff(id_arr[index], prepend=id_arr[index][0] - 1) != 0)
        last_idx = np.concatenate([first_idx[1:] - 1, [len(id_arr) - 1]])
        if np.any(sorty[last_idx[:-1], 2] != 0):
            raise ValueError("a subject has a transition before their last time point")
        delta = np.concatenate([sorty[1:, 0], [0.0]]) - sorty[:, 1]
        if np.any(delta[last_idx[:-1]] != 0):
            raise ValueError("a subject has gaps in time")
        if np.any(ymat[first_idx, 0] > np.min(ymat[:, 1])):
            delay = True
        temp1 = np.zeros(len(mf), dtype=bool)
        temp2 = np.zeros(len(mf), dtype=bool)
        temp1[index[first_idx]] = True
        temp2[index[last_idx]] = True
        first = temp1
        last = temp2
    else:
        last = np.ones(len(mf), dtype=bool)
    if etype is None:
        enum = 1
    else:
        if states is None:
            raise ValueError("etype argument has a state that is not in the data")
        targets = [etype] if isinstance(etype, str) else list(etype)
        index = []
        for e in targets:
            try:
                index.append(states.index(e) + 1)
            except ValueError:
                index.append(-1)
        if any(i < 0 for i in index):
            raise ValueError("etype argument has a state that is not in the data")
        enum = index[0]
        if len(index) > 1:
            warnings.warn("only the first endpoint was used", stacklevel=2)
    count_name = None if count is None else _make_names(count)
    oname = [f"{prefix}{suffix}" for suffix in ("start", "stop", "status", "wt")]
    if nY == 2:
        finite = ymat[np.isfinite(ymat[:, 0]), 0]
        temp = float(np.min(finite)) if finite.size else 0.0
        zero = 0.0 if temp > 0 else 2.0 * temp - 1.0
        ymat = np.column_stack([np.full(ymat.shape[0], zero), ymat])
    utime = np.sort(np.unique(np.concatenate([ymat[:, 0], ymat[:, 1]])))
    newtime = np.column_stack([_find_interval(ymat[:, 0], utime), _find_interval(ymat[:, 1], utime)])
    status = ymat[:, 2]
    newtime = newtime.astype(float, copy=True)
    evmask = status != 0
    newtime[evmask, 1] = newtime[evmask, 1] - 0.2
    event_g = (last & (status == 0)).astype(float)
    y_km = np.column_stack([newtime[:, 0], newtime[:, 1], event_g])
    gsurv = _survfit_km(y_km, istrat, user_weights)
    hsurv = None
    if delay:
        event_h = first.astype(float)
        y_h = np.column_stack([-newtime[:, 1], -newtime[:, 0], event_h])
        hsurv = _survfit_km(y_h, istrat, user_weights)
    status = ymat[:, 2]

    def stratfun(i: int) -> FinegrayFrame | None:
        keep = istrat == i
        times = np.sort(np.unique(ymat[keep & (status == enum), 1]))
        if times.size == 0:
            return None
        tdata_names, tdata_cols = _covariate_columns(mf)
        tdata_cols = [_subset_rows_col(c, keep) for c in tdata_cols]
        maxtime = float(np.max(ymat[keep, 1]))
        gtemp = gsurv[i]
        if delay and hsurv is not None:
            htemp = hsurv[i]
            dtime = -htemp["time"][htemp["n.event"] > 0][::-1]
            dprob = np.concatenate([htemp["surv"][htemp["n.event"] > 0][::-1][1:], [1.0]])
            ctime_ev = gtemp["time"][gtemp["n.event"] > 0]
            cprob = np.concatenate([[1.0], gtemp["surv"][gtemp["n.event"] > 0]])
            temp = np.sort(np.unique(np.concatenate([dtime, ctime_ev])))
            index1 = _find_interval(temp, dtime)
            index2 = _find_interval(temp, ctime_ev)
            ctime_out = utime[np.asarray(temp, dtype=int) - 1]
            cprob_out = dprob[index1] * cprob[index2 + 1]
        else:
            ev_t = gtemp["time"][gtemp["n.event"] > 0]
            ctime_out = utime[np.asarray(ev_t, dtype=int) - 1]
            cprob_out = gtemp["surv"][gtemp["n.event"] > 0]
        ct2 = np.concatenate([ctime_out, [maxtime]])
        cp2 = np.concatenate([[1.0], cprob_out])
        index = _find_interval(times, ct2, left_open=True)
        index = np.sort(np.unique(index))
        ckeep = np.zeros(ct2.size, dtype=bool)
        for idx in index:
            if idx > 0:
                ckeep[int(idx) - 1] = True
        expand = (ymat[keep, 2] != 0) & (ymat[keep, 2] != enum) & last[keep]
        split = _cfinegray(ymat[keep, 0], ymat[keep, 1], ct2, cp2, expand, np.concatenate([[True], ckeep]))
        row = split["row"]
        tdata_cols = _select_rows(tdata_cols, row)
        tstat = np.where(status[keep][row - 1] == enum, 1.0, 0.0)
        out_cols = list(tdata_cols)
        out_names = list(tdata_names)
        out_cols.extend([split["start"], split["end"], tstat, split["wt"] * user_weights[row - 1]])
        out_names.extend(oname)
        if count_name is not None:
            out_cols.append(split["add"])
            out_names.append(count_name)
        return FinegrayFrame(out_names, out_cols, event=states[enum - 1])

    if int(np.max(istrat)) == 1:
        result = stratfun(1)
    else:
        parts = [stratfun(i) for i in range(1, int(np.max(istrat)) + 1)]
        parts = [p for p in parts if p is not None]
        if not parts:
            raise ValueError("No (non-missing) observations")
        out_names = parts[0].names
        out_cols = []
        for name in out_names:
            merged = []
            for part in parts:
                j = part.names.index(name)
                col = part.columns[j]
                if isinstance(col, np.ndarray):
                    merged.append(col)
                elif isinstance(col, Categorical):
                    merged.extend(col.values)
                else:
                    merged.extend(list(col))
            if isinstance(parts[0].columns[out_names.index(name)], np.ndarray):
                out_cols.append(np.concatenate(merged))
            elif isinstance(parts[0].columns[out_names.index(name)], Categorical):
                out_cols.append(Categorical(merged, parts[0].columns[out_names.index(name)].levels))
            else:
                out_cols.append(merged)
        result = FinegrayFrame(out_names, out_cols, event=parts[0].event)
    if result is None:
        raise ValueError("No (non-missing) observations")
    return result


def finegray_table(formula, data=None, **kwargs) -> dict[str, Any]:
    """Return finegray output as a column dictionary."""
    frame = finegray(formula, data, **kwargs)
    out = {name: col for name, col in zip(frame.names, frame.columns)}
    out["event"] = frame.event
    return out
