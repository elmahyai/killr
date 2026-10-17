"""Split survival records at cut times (survival::survSplit)."""

from __future__ import annotations

import math
import re
from typing import Any, Mapping, Sequence

import numpy as np

from survival.fromtimeline import Categorical, TimelineFrame, _duplicated
from survival.surv import Surv, SurvObject, aeqSurv, is_Surv
from survival.surv2 import Surv2, Surv2Object, FactorEvent


def _make_names(text: str) -> str:
    out = re.sub(r"[^A-Za-z0-9._]", ".", str(text))
    if out and out[0].isdigit():
        out = "X." + out
    return out


def _as_table(data: Mapping[str, Any] | TimelineFrame) -> dict[str, Any]:
    if isinstance(data, TimelineFrame):
        return {name: col for name, col in zip(data.names, data.columns)}
    return dict(data)


def _column_len(col) -> int:
    if isinstance(col, (SurvObject, Surv2Object)):
        return len(col)
    if isinstance(col, Categorical):
        return len(col.values)
    if isinstance(col, np.ndarray):
        return int(col.shape[0])
    return len(col)


def _subset_table(table: dict[str, Any], keep: np.ndarray) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, col in table.items():
        if isinstance(col, Categorical):
            out[key] = Categorical([col.values[i] for i in range(len(col.values)) if keep[i]], col.levels)
        elif isinstance(col, np.ndarray):
            out[key] = col[keep]
        elif isinstance(col, (SurvObject, Surv2Object)):
            mat = col.matrix()[keep]
            if isinstance(col, Surv2Object):
                out[key] = Surv2Object(
                    mat,
                    states=col.states,
                    clabel=col.clabel,
                    input_attributes=col.input_attributes,
                    repeated=col.repeated,
                    colnames=col.colnames,
                )
            else:
                out[key] = SurvObject(mat, col.type, col.states, col.clabel)
        else:
            out[key] = [col[i] for i in range(len(col)) if keep[i]]
    return out


def _parse_surv_lhs(lhs: str) -> tuple[bool, list[str]]:
    text = lhs.strip()
    if text.startswith("Surv2"):
        m = re.match(r"Surv2\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)\s*$", text)
        if not m:
            raise ValueError("either a formula or the end and event arguments are required")
        return True, [m.group(1).strip(), m.group(2).strip()]
    if text.startswith("Surv"):
        m3 = re.match(r"Surv\s*\(\s*([^,)]+)\s*,\s*([^,)]+)\s*,\s*([^)]+)\s*\)\s*$", text)
        if m3:
            return False, [m3.group(1).strip(), m3.group(2).strip(), m3.group(3).strip()]
        m2 = re.match(r"Surv\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)\s*$", text)
        if m2:
            return False, [m2.group(1).strip(), m2.group(2).strip()]
        raise ValueError("either a formula or the end and event arguments are required")
    raise ValueError("either a formula or the end and event arguments are required")


def _build_response(table: dict[str, Any], is_surv2: bool, names: list[str]):
    if is_surv2:
        time_name, event_name = names
        if time_name not in table or event_name not in table:
            raise ValueError("the model must have a Surv or Surv2 object as the response")
        time = table[time_name]
        event = table[event_name]
        if isinstance(event, Categorical):
            return Surv2(time, FactorEvent(event.values, event.levels))
        if isinstance(event, FactorEvent):
            return Surv2(time, event)
        return Surv2(time, event)
    if len(names) == 2:
        end_name, event_name = names
        if end_name not in table or event_name not in table:
            raise ValueError("the model must have a Surv or Surv2 object as the response")
        return Surv(table[end_name], event=table[event_name])
    start_name, end_name, event_name = names
    for nm in (start_name, end_name, event_name):
        if nm not in table:
            raise ValueError("the model must have a Surv or Surv2 object as the response")
    return Surv(table[start_name], table[end_name], event=table[event_name])


def _apply_subset(table: dict[str, Any], subset) -> tuple[dict[str, Any], np.ndarray | None]:
    if subset is None:
        return table, None
    n = _column_len(next(iter(table.values())))
    if callable(subset):
        keep = np.asarray(subset(table), dtype=bool)
    else:
        keep = np.asarray(subset, dtype=bool)
    if keep.shape[0] != n:
        raise ValueError("subset length mismatch")
    return _subset_table(table, keep), keep


def _build_model_frame(
    formula_text: str,
    data: Mapping[str, Any] | TimelineFrame,
    *,
    subset=None,
    id=None,
) -> tuple[TimelineFrame, SurvObject | Surv2Object, list[str], bool]:
    table = _as_table(data)
    table, _ = _apply_subset(table, subset)
    if "~" not in formula_text:
        raise ValueError("either a formula or the end and event arguments are required")
    lhs, rhs = formula_text.split("~", 1)
    is_surv2, lhs_names = _parse_surv_lhs(lhs)
    rhs = rhs.strip()
    if rhs != ".":
        raise ValueError("only Surv(...) ~ . formulas are supported")
    response = _build_response(table, is_surv2, lhs_names)
    used = set(lhs_names)
    covariate_names = [name for name in table if name not in used]
    mf_names = [lhs.strip(), *covariate_names]
    mf_cols: list[Any] = [response]
    for name in covariate_names:
        mf_cols.append(table[name])
    specials: dict[str, Any] = {}
    if id is not None:
        if isinstance(id, str):
            if id not in table:
                raise ValueError(f"id variable {id!r} not found in data")
            specials["id"] = table[id]
            mf_names.append("(id)")
            mf_cols.append(table[id])
        else:
            raise ValueError("invalid value for id")
    return TimelineFrame(mf_names, mf_cols, specials), response, lhs_names, is_surv2


def _csurvsplit(tstart: np.ndarray, tstop: np.ndarray, cut: np.ndarray) -> dict[str, np.ndarray]:
    n = tstart.shape[0]
    ncut = cut.shape[0]
    extra = 0
    for i in range(n):
        for j in range(ncut):
            if math.isfinite(tstart[i]) and math.isfinite(tstop[i]) and cut[j] > tstart[i] and cut[j] < tstop[i]:
                extra += 1
    n2 = n + extra
    row = np.zeros(n2, dtype=int)
    interval = np.zeros(n2, dtype=int)
    start = np.zeros(n2, dtype=float)
    end = np.zeros(n2, dtype=float)
    censor = np.zeros(n2, dtype=bool)
    k = 0
    for i in range(n):
        if math.isnan(tstart[i]) or math.isnan(tstop[i]):
            start[k] = tstart[i]
            end[k] = tstop[i]
            row[k] = i + 1
            interval[k] = 1
            k += 1
            continue
        j = 0
        while j < ncut and cut[j] <= tstart[i]:
            j += 1
        start[k] = tstart[i]
        row[k] = i + 1
        interval[k] = j
        while j < ncut and cut[j] < tstop[i]:
            if cut[j] > tstart[i]:
                end[k] = cut[j]
                censor[k] = True
                k += 1
                start[k] = cut[j]
                row[k] = i + 1
                interval[k] = j + 1
            j += 1
        end[k] = tstop[i]
        censor[k] = False
        k += 1
    return {"row": row, "interval": interval, "start": start, "end": end, "censor": censor}


def _aeq_times_two_col(times: np.ndarray, status: np.ndarray) -> np.ndarray:
    temp = SurvObject(np.column_stack([times, status]), "right")
    fixed = aeqSurv(temp)
    return fixed.columns[:, 0]


def _timefix_surv(Y: SurvObject, cut: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ntimes = cut.shape[0]
    mat = np.array(Y.columns, dtype=float, copy=True)
    ymiss = np.isnan(mat)
    if mat.shape[1] == 2:
        ty = np.vstack([np.column_stack([cut, np.zeros(ntimes)]), mat])
        fixed = aeqSurv(SurvObject(ty, Y.type, Y.states, Y.clabel))
        new_cut = fixed.columns[:ntimes, 0]
        mat[:, 0] = fixed.columns[ntimes:, 0]
    else:
        finite_start = mat[~np.any(ymiss, axis=1), 0]
        ty = np.vstack(
            [
                np.column_stack([np.min(finite_start), cut, np.zeros(ntimes)]),
                mat,
            ]
        )
        fixed = aeqSurv(SurvObject(ty, Y.type, Y.states, Y.clabel))
        new_cut = fixed.columns[:ntimes, 1]
        mat[:, 0:2] = fixed.columns[ntimes:, 0:2]
    return new_cut, mat


def _timefix_surv2(Y: Surv2Object, cut: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    ntimes = cut.shape[0]
    mat = np.array(Y.matrix(), dtype=float, copy=True)
    ty = np.vstack([np.column_stack([cut, np.zeros(ntimes)]), mat])
    fixed_times = _aeq_times_two_col(ty[:, 0], ty[:, 1])
    new_cut = fixed_times[:ntimes]
    mat[:, 0] = fixed_times[ntimes:]
    return new_cut, mat


def _select_rows_table(table: dict[str, Any], row_idx: np.ndarray) -> dict[str, Any]:
    idx = row_idx.astype(int) - 1
    out: dict[str, Any] = {}
    for key, col in table.items():
        if isinstance(col, Categorical):
            out[key] = Categorical([col.values[i] for i in idx], col.levels)
        elif isinstance(col, np.ndarray):
            out[key] = col[idx]
        else:
            out[key] = [col[i] for i in idx]
    return out


def _select_rows_mf(mf: TimelineFrame, row_idx: np.ndarray, drop_response: bool) -> dict[str, Any]:
    idx = row_idx.astype(int) - 1
    start = 1 if drop_response else 0
    out: dict[str, Any] = {}
    for name, col in zip(mf.names[start:], mf.columns[start:]):
        if name.startswith("("):
            continue
        if isinstance(col, Categorical):
            out[name] = Categorical([col.values[i] for i in idx], col.levels)
        elif isinstance(col, np.ndarray):
            out[name] = col[idx]
        else:
            out[name] = [col[i] for i in idx]
    return out


def _status_factor(status: np.ndarray, states: Sequence[str] | None) -> Categorical | np.ndarray:
    if states is None:
        return status
    labels = ["censor", *list(states)]
    values = []
    for code in status:
        if math.isnan(code):
            values.append(None)
        else:
            icode = int(code)
            if 0 <= icode < len(labels):
                values.append(labels[icode])
            else:
                values.append(None)
    return Categorical(values, labels)


def survSplit(
    formula,
    data=None,
    subset=None,
    na_action=None,
    id=None,
    cut=None,
    zero=0,
    episode=None,
    start="tstart",
    end="tstop",
    event="event",
    added=None,
    timefix=True,
):
    """Split survival records at cut times."""
    formula_text = None

    if data is None and not isinstance(formula, str):
        data = formula
        formula = None

    if formula is None or isinstance(formula, (dict, TimelineFrame)) or (
        hasattr(formula, "keys") and not isinstance(formula, str)
    ):
        if formula is not None and not isinstance(formula, str):
            if data is None:
                data = formula
        if data is None:
            raise ValueError("a data frame is required")
        table = _as_table(data)
        if not isinstance(event, str) or event not in table:
            raise ValueError("'event' must be a variable name in the data set")
        if not isinstance(end, str) or end not in table:
            raise ValueError("'end' must be a variable name in the data set")
        if not isinstance(start, str):
            raise ValueError("'start' must be a variable name")
        if start in table:
            formula_text = f"Surv({start}, {end}, {event}) ~ ."
        else:
            formula_text = f"Surv({end}, {event}) ~ ."
        formula_lhs_names = _parse_surv_lhs(formula_text.split("~", 1)[0])[1]
    elif isinstance(formula, str):
        formula_text = formula
        if data is None:
            raise ValueError("a data argument is required")
        table = _as_table(data)
        if id is not None and not isinstance(id, str):
            if isinstance(id, (list, tuple, np.ndarray)) and len(id) != 1:
                pass
            else:
                raise ValueError("invalid value for id")
        formula_lhs_names = _parse_surv_lhs(formula_text.split("~", 1)[0])[1]
    else:
        raise ValueError("either a formula or the end and event arguments are required")

    if cut is None:
        raise ValueError("cut must be a vector of finite numbers")
    cut_arr = np.asarray(cut, dtype=float).reshape(-1)
    if cut_arr.size == 0 or not np.all(np.isfinite(cut_arr)):
        raise ValueError("cut must be a vector of finite numbers")
    cut_arr = np.unique(np.sort(cut_arr))

    if not isinstance(timefix, (bool, np.bool_)) or (isinstance(timefix, (list, tuple, np.ndarray)) and len(timefix) > 1):
        raise ValueError("invalid value for timefix option")

    id_for_mf = id if isinstance(id, str) else None
    mf, Y, lhs_names, is_surv2 = _build_model_frame(formula_text, data, subset=subset, id=id_for_mf)
    n_orig = len(mf)

    if is_surv2:
        if not isinstance(Y, Surv2Object):
            raise ValueError("the model must have a Surv or Surv2 object as the response")
    elif not is_Surv(Y):
        raise ValueError("the model must have a Surv or Surv2 object as the response")
    elif Y.type not in ("right", "mright", "counting", "mcounting"):
        raise ValueError(f"not valid for {Y.type} censored survival data")

    states = Y.states
    nY = Y.matrix().shape[1]
    ymiss = np.isnan(Y.matrix())

    if timefix:
        if is_surv2:
            cut_arr, ymat = _timefix_surv2(Y, cut_arr)
            Y = Surv2Object(ymat, states=Y.states, clabel=Y.clabel, input_attributes=Y.input_attributes, repeated=Y.repeated)
        else:
            cut_arr, ymat = _timefix_surv(Y, cut_arr)
            Y = SurvObject(ymat, Y.type, Y.states, Y.clabel)

    table_full = _as_table(data)
    table_full, _ = _apply_subset(table_full, subset)
    rightdot = formula_text.split("~", 1)[1].strip() == "." and n_orig == _column_len(next(iter(table_full.values())))

    if isinstance(id, str) and id not in table_full and is_Surv(Y) and Y.type == "right":
        nrows = _column_len(next(iter(table_full.values())))
        seq_id = np.arange(1, nrows + 1, dtype=float)
        table_full[id] = seq_id
        if id not in mf.names:
            mf.names.append(id)
            mf.columns.append(list(seq_id))

    if is_surv2:
        id_col = mf.specials.get("id")
        if id_col is None:
            raise ValueError("an id statement is required")
        ymat = np.array(Y.matrix(), dtype=float)
        id_arr = np.asarray(id_col, dtype=object)
        idord = np.lexsort((ymat[:, 0], id_arr))
        yfake = ymat[:, 0].copy()
        notlast = _duplicated(id_arr[idord], from_last=True)
        next_rows = np.concatenate([idord[1:], [0]])
        yfake[idord[notlast]] = yfake[next_rows[notlast]]
        index = _csurvsplit(ymat[:, 0], yfake, cut_arr)
        status = ymat[index["row"] - 1, 1].copy()
        for pos in np.flatnonzero(index["censor"]):
            if pos + 1 < status.shape[0]:
                status[pos + 1] = 0.0
        start_name = lhs_names[0]
        event_name = lhs_names[1]
    else:
        ymat = np.array(Y.matrix(), dtype=float)
        if nY == 2:
            if np.any(ymat[~np.any(ymiss, axis=1), 0] <= zero):
                raise ValueError("'zero' parameter must be less than any observed times")
            ymat = np.column_stack([np.full(ymat.shape[0], float(zero)), ymat])
        bad = ymat[~np.any(ymiss, axis=1), 0] >= ymat[~np.any(ymiss, axis=1), 1]
        if np.any(bad):
            raise ValueError("start time must be < stop time")
        index = _csurvsplit(ymat[:, 0], ymat[:, 1], cut_arr)
        status = ymat[index["row"] - 1, 2].copy()
        status[index["censor"]] = 0.0
        if len(lhs_names) == 2:
            end_name = lhs_names[0]
            event_name = lhs_names[1]
            start_name = start
        else:
            start_name = lhs_names[0]
            end_name = lhs_names[1]
            event_name = lhs_names[2]

    if rightdot:
        newdata = _select_rows_table(table_full, index["row"])
    else:
        newdata = _select_rows_mf(mf, index["row"], drop_response=True)

    status = _status_factor(status, states)

    if is_surv2:
        newdata[start_name] = index["start"]
        newdata[event_name] = status
    else:
        newdata[start_name] = index["start"]
        newdata[end_name] = index["end"]
        newdata[event_name] = status

    if episode is not None:
        if not isinstance(episode, str):
            raise ValueError("episode must be a character string")
        newdata[_make_names(episode)] = index["interval"] + 1

    if added is not None:
        if not isinstance(added, str):
            raise ValueError("added must be a character string")
        newdata[_make_names(added)] = index["censor"]

    names = list(newdata.keys())
    cols = [newdata[name] for name in names]
    return TimelineFrame(names, cols)


def survSplit_table(formula, data=None, **kwargs) -> dict[str, Any]:
    """Return survSplit output as a column dictionary."""
    frame = survSplit(formula, data, **kwargs)
    return {name: col for name, col in zip(frame.names, frame.columns)}
