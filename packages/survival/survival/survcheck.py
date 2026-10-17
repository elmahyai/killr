"""Consistency checks for multi-state survival data (survival::survcheck)."""

from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any, Mapping, Sequence

import numpy as np

from survival.fromtimeline import (
    Categorical,
    TimelineFrame,
    _model_extract,
    _model_response,
    _surv2counting,
)
from survival.surv import Surv, SurvObject, aeqSurv, is_Surv
from survival.surv2 import FactorEvent, Surv2, Surv2Object


def _parse_surv_lhs(lhs: str) -> tuple[bool, list[str]]:
    text = lhs.strip()
    if text.startswith("Surv2"):
        m = re.match(r"Surv2\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)\s*$", text)
        if not m:
            raise ValueError("response must be a survival object")
        return True, [m.group(1).strip(), m.group(2).strip()]
    if text.startswith("Surv"):
        m3 = re.match(r"Surv\s*\(\s*([^,)]+)\s*,\s*([^,)]+)\s*,\s*([^)]+)\s*\)\s*$", text)
        if m3:
            return False, [m3.group(1).strip(), m3.group(2).strip(), m3.group(3).strip()]
        m2 = re.match(r"Surv\s*\(\s*([^,)]+)\s*,\s*([^)]+)\s*\)\s*$", text)
        if m2:
            return False, [m2.group(1).strip(), m2.group(2).strip()]
    raise ValueError("response must be a survival object")


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


def _build_response(table: dict[str, Any], is_surv2: bool, names: list[str]):
    if is_surv2:
        time_name, event_name = names
        time = table[time_name]
        event = table[event_name]
        if isinstance(event, Categorical):
            return Surv2(time, FactorEvent(event.values, event.levels))
        if isinstance(event, FactorEvent):
            return Surv2(time, event)
        return Surv2(time, event)
    if len(names) == 2:
        end_name, event_name = names
        event = table[event_name]
        if isinstance(event, Categorical):
            index = {level: code for code, level in enumerate(event.levels)}
            status = np.array([float(index[v]) if v in index else math.nan for v in event.values], dtype=float)
            return SurvObject(
                np.column_stack([np.asarray(table[end_name], dtype=float), status]),
                "mright",
                event.levels[1:],
                event.levels[0],
            )
        return Surv(table[end_name], event=event)
    start_name, end_name, event_name = names
    event = table[event_name]
    if isinstance(event, Categorical):
        index = {level: code for code, level in enumerate(event.levels)}
        codes = np.array([float(index[v]) if v in index else math.nan for v in event.values], dtype=float)
        return SurvObject(
            np.column_stack(
                [
                    np.asarray(table[start_name], dtype=float),
                    np.asarray(table[end_name], dtype=float),
                    codes,
                ]
            ),
            "mcounting",
            event.levels[1:],
            event.levels[0],
        )
    return Surv(table[start_name], table[end_name], event=event)


def _row_any_na(mf: TimelineFrame) -> np.ndarray:
    n = len(mf)
    miss = np.zeros(n, dtype=bool)
    for col in mf.columns:
        if isinstance(col, (SurvObject, Surv2Object)):
            miss |= col.is_na()
        elif isinstance(col, Categorical):
            miss |= np.array([v is None or (isinstance(v, float) and math.isnan(v)) for v in col.values])
        elif isinstance(col, np.ndarray):
            if col.dtype == object:
                miss |= np.array([v is None or (isinstance(v, float) and math.isnan(v)) for v in col])
            else:
                miss |= np.isnan(col)
        else:
            miss |= np.array([v is None or (isinstance(v, float) and math.isnan(v)) for v in col])
    return miss


def _default_na_action(mf: TimelineFrame):
    keep = ~_row_any_na(mf)
    if np.all(keep):
        return mf, None
    omitted = np.where(~keep)[0] + 1
    return mf.subset_rows(keep), omitted


def _apply_na_action(mf: TimelineFrame, na_action):
    if na_action is None:
        return _default_na_action(mf)
    if na_action == "na.omit" or na_action is True:
        return _default_na_action(mf)
    if na_action == "na.pass":
        return mf, None
    if callable(na_action):
        return na_action(mf), None
    raise ValueError("unsupported na.action")


def _build_model_frame(
    formula: str,
    data: Mapping[str, Any],
    *,
    subset=None,
    id=None,
    istate=None,
) -> TimelineFrame:
    if data is None:
        raise ValueError("data argument is required")
    if id is None:
        raise ValueError("an id argument is required")
    if "~" not in formula:
        raise ValueError("a formula argument is required")
    lhs, rhs = formula.split("~", 1)
    is_surv2, lhs_names = _parse_surv_lhs(lhs)
    table = dict(data)
    n = _column_len(next(iter(table.values())))
    if subset is not None:
        if callable(subset):
            keep = np.asarray(subset(table), dtype=bool)
        else:
            keep = np.asarray(subset, dtype=bool)
        if keep.shape[0] != n:
            raise ValueError("subset length mismatch")
        table = _subset_table(table, keep)
        n = _column_len(next(iter(table.values())))
    for name in lhs_names:
        if name not in table:
            raise ValueError("response must be a survival object")
    response = _build_response(table, is_surv2, lhs_names)
    used = set(lhs_names)
    rhs = rhs.strip()
    covariate_names: list[str] = []
    if rhs == ".":
        covariate_names = [name for name in table if name not in used]
    elif rhs != "1":
        covariate_names = [part.strip() for part in rhs.split("+") if part.strip()]
    mf_names = [lhs.strip(), *covariate_names]
    mf_cols: list[Any] = [response]
    for name in covariate_names:
        mf_cols.append(table[name])
    specials: dict[str, Any] = {}
    if isinstance(id, str):
        if id not in table:
            raise ValueError("wrong length for id")
        specials["id"] = table[id]
    else:
        id_col = list(id)
        if len(id_col) != n:
            raise ValueError("wrong length for id")
        specials["id"] = id_col
    mf_names.append("(id)")
    mf_cols.append(specials["id"])
    if istate is not None:
        if isinstance(istate, str):
            if istate not in table:
                raise ValueError("wrong length for istate")
            istate_col = table[istate]
        else:
            istate_col = istate
        if _column_len(istate_col) != n:
            raise ValueError("wrong length for istate")
        mf_names.append("(istate)")
        mf_cols.append(istate_col)
        specials["istate"] = istate_col
    return TimelineFrame(mf_names, mf_cols, specials)


def _multicheck(time1, time2, status, id2, istate, sort_index):
    n = len(id2)
    dupid = np.zeros(n, dtype=int)
    gap = np.zeros(n, dtype=int)
    cstate = np.zeros(n, dtype=int)
    oldid = -1
    oldii = 0
    cstate[0] = istate[0]
    for i in range(n):
        ii = int(sort_index[i])
        if id2[ii] == oldid:
            dupid[ii] = 0
            if time1[ii] == time2[oldii]:
                gap[ii] = 0
            elif time1[ii] > time2[oldii]:
                gap[ii] = 1
            else:
                gap[ii] = -1
            if status[oldii] > 0:
                cstate[ii] = status[oldii]
            else:
                cstate[ii] = cstate[oldii]
        else:
            oldid = id2[ii]
            dupid[ii] = 0
            gap[ii] = 0
            cstate[ii] = istate[ii]
            if i > 0:
                dupid[oldii] += 2
        oldii = ii
    dupid[oldii] += 2
    return {"dupid": dupid, "gap": gap, "cstate": cstate}


def _as_factor(values, levels):
    if isinstance(values, Categorical):
        return Categorical(list(values.values), list(levels))
    out = []
    index = {level: i for i, level in enumerate(levels)}
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            out.append(None)
        elif value in index:
            out.append(levels[index[value]])
        else:
            out.append(str(value))
    return Categorical(out, list(levels))


def _factor_codes(values, levels):
    index = {level: i + 1 for i, level in enumerate(levels)}
    codes = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            codes.append(0)
        else:
            codes.append(index.get(value, 0))
    return np.array(codes, dtype=int)


def _match_state(level, ystate):
    try:
        return ystate.index(level) + 1
    except ValueError:
        return 0


def _survcheck2(y: SurvObject, id_col, istate=None, istate0="(s0)"):
    n = len(id_col)
    ny = y.columns.shape[1]
    if not is_Surv(y) or y.states is None:
        raise ValueError("survcheck2 called with an invalid y argument")
    ystate = list(y.states)
    if np.any(y.columns[:, ny - 1] > len(ystate)):
        raise ValueError("survcheck2 called with an invalid y argument")

    if istate is None or (hasattr(istate, "__len__") and len(istate) == 0):
        inull = True
        cstate = Categorical([istate0] * n, [istate0])
    else:
        if len(istate) != n:
            raise ValueError("wrong length for istate")
        inull = False
        if isinstance(istate, Categorical):
            cstate = Categorical(list(istate.values), list(istate.levels))
        else:
            levels = sorted(set(istate), key=str)
            cstate = Categorical(list(istate), levels)

    clevels = list(cstate.levels)
    index = [_match_state(level, ystate) for level in clevels]
    states = [clevels[i] for i, hit in enumerate(index) if hit == 0] + ystate
    cstate2 = _as_factor(cstate.values, states)
    cstate_codes = _factor_codes(cstate2.values, states)

    tab1: dict[Any, list[int]] = {}
    for subj, code in zip(id_col, y.columns[:, ny - 1]):
        if subj not in tab1:
            tab1[subj] = [0] * (len(ystate) + 1)
        icode = int(code) if not math.isnan(code) else 0
        if icode > 0:
            tab1[subj][icode] += 1
    rows = [tab1[s][1:] for s in tab1]
    events = None
    if rows:
        arr = np.array(rows, dtype=int)
        if not np.all(arr == 0):
            if arr.shape[1] == 1:
                temp = Counter(arr[:, 0])
                events = {ystate[0]: dict(temp)}
            else:
                arr = np.column_stack([arr, arr.sum(axis=1)])
                levels = sorted(set(arr.reshape(-1)))
                state_names = list(ystate) + ["(any)"]
                events = {}
                for j, name in enumerate(state_names):
                    counts = Counter(arr[:, j])
                    events[name] = {level: counts[level] for level in levels if level in counts}
                novisit = [name for name in state_names if name != "(any)" and sum(events[name].values()) == 0]
                for name in novisit:
                    del events[name]

    sindx = [states.index(state) + 1 for state in ystate]
    status_col = y.columns[:, ny - 1]
    stat2 = np.zeros(n, dtype=int)
    for i, code in enumerate(status_col):
        if math.isnan(code) or code == 0:
            stat2[i] = 0
        else:
            icode = max(1, int(code))
            stat2[i] = sindx[icode - 1]

    _, id_inv = np.unique(id_col, return_inverse=True)
    id2 = id_inv + 1
    ymat = np.asarray(y.columns, dtype=float)
    if ny == 2:
        sort_index = np.lexsort((ymat[:, 0], np.asarray(id_col, dtype=object)))
        check = _multicheck(np.zeros(n), ymat[:, 0], stat2, id2, cstate_codes, sort_index)
    else:
        sort_index = np.lexsort((ymat[:, 0], ymat[:, 1], np.asarray(id_col, dtype=object)))
        check = _multicheck(ymat[:, 0], ymat[:, 1], stat2, id2, cstate_codes, sort_index)

    if inull and ny > 2:
        cstate2 = _as_factor([states[c - 1] for c in check["cstate"]], states)
        cstate_codes = _factor_codes(cstate2.values, states)

    censor_label = f"({y.clabel})"
    keep = (stat2 != 0) | (check["dupid"] > 1)
    from_vals = [cstate2.values[i] for i in range(n) if keep[i]]
    to_vals = []
    for i in range(n):
        if not keep[i]:
            continue
        if stat2[i] == 0:
            to_vals.append(censor_label)
        else:
            to_vals.append(states[stat2[i] - 1])
    row_levels = list(states)
    col_levels = list(states) + [censor_label]
    transitions = np.zeros((len(row_levels), len(col_levels)), dtype=int)
    ri = {value: idx for idx, value in enumerate(row_levels)}
    ci = {value: idx for idx, value in enumerate(col_levels)}
    for a, b in zip(from_vals, to_vals):
        transitions[ri[a], ci[b]] += 1
    nr = transitions.shape[0]
    never = (transitions.sum(axis=1) + transitions[:, :nr].sum(axis=0)) == 0
    keep_row = ~never
    keep_col = transitions.sum(axis=0) > 0
    transitions = transitions[keep_row][:, keep_col]
    to_labels = [lab for lab, k in zip(col_levels, keep_col) if k]

    cstate_num = check["cstate"]
    mismatch = cstate_codes != cstate_num
    flag = {
        "overlap": int(np.sum(check["gap"] < 0)),
        "gap": int(np.sum((check["gap"] > 0) & (~mismatch))),
        "jump": int(np.sum((check["gap"] > 0) & mismatch)),
        "teleport": int(np.sum((check["gap"] == 0) & mismatch & (check["dupid"] % 2 == 0))),
    }

    istate_out = _as_factor([states[c - 1] for c in cstate_num], states)
    rval = {
        "states": states,
        "transitions": transitions,
        "transition_to": to_labels,
        "events": events,
        "flag": flag,
        "istate": istate_out,
    }
    if flag["overlap"] > 0:
        j = np.where(check["gap"] < 0)[0]
        rval["overlap"] = {"row": j + 1, "id": list(dict.fromkeys([id_col[i] for i in j]))}
    if flag["gap"] > 0:
        j = np.where((check["gap"] > 0) & (~mismatch))[0]
        rval["gap"] = {"row": j + 1, "id": list(dict.fromkeys([id_col[i] for i in j]))}
    if flag["jump"] > 0:
        j = np.where((check["gap"] > 0) & mismatch)[0]
        rval["jump"] = {"row": j + 1, "id": list(dict.fromkeys([id_col[i] for i in j]))}
    if flag["teleport"] > 0:
        j = np.where((check["gap"] == 0) & mismatch & (check["dupid"] % 2 == 0))[0]
        rval["teleport"] = {"row": j + 1, "id": list(dict.fromkeys([id_col[i] for i in j]))}
    return rval


def _recode_binary_surv(y: SurvObject) -> SurvObject:
    kind = y.type
    if kind == "right":
        status = y.columns[:, 1]
        labels = ["censor", "event"]
        codes = np.array([labels[int(s)] if not math.isnan(s) and int(s) in (0, 1) else math.nan for s in status])
        index = {label: i for i, label in enumerate(labels)}
        numeric = np.array([float(index[c]) if c in index else math.nan for c in codes], dtype=float)
        return SurvObject(np.column_stack([y.columns[:, 0], numeric]), "mright", ["event"], "censor")
    if kind == "counting":
        status = y.columns[:, 2]
        labels = ["censor", "event"]
        codes = np.array([labels[int(s)] if not math.isnan(s) and int(s) in (0, 1) else math.nan for s in status])
        index = {label: i for i, label in enumerate(labels)}
        numeric = np.array([float(index[c]) if c in index else math.nan for c in codes], dtype=float)
        return SurvObject(np.column_stack([y.columns[:, 0], y.columns[:, 1], numeric]), "mcounting", ["event"], "censor")
    if kind in ("mright", "mcounting"):
        return y
    raise ValueError("response must be right censored")


class SurvcheckResult(dict):
    """survcheck return value."""


def survcheck(
    formula,
    data=None,
    subset=None,
    na_action=None,
    id=None,
    istate=None,
    istate0="(s0)",
    timefix=True,
    **kwargs,
):
    if formula is None:
        raise ValueError("a formula argument is required")
    mf = _build_model_frame(formula, data, subset=subset, id=id, istate=istate)
    Y = _model_response(mf)
    if not (is_Surv(Y) or isinstance(Y, Surv2Object)):
        raise ValueError("response must be a survival object")
    if isinstance(Y, Surv2Object):
        mf = _surv2counting(mf)
        Y = _model_response(mf)
    mf, omit = _apply_na_action(mf, na_action)
    Y = _model_response(mf)
    id_col = _model_extract(mf, "id")
    n = len(Y)
    if n == 0:
        raise ValueError("No (non-missing) observations")
    if not (isinstance(timefix, (bool, np.bool_)) and np.asarray(timefix).size == 1):
        raise ValueError("invalid value for timefix option")
    if timefix:
        Y = aeqSurv(Y)
    istate_col = _model_extract(mf, "istate")
    kind = Y.type
    Y = _recode_binary_surv(Y)
    if id_col is None:
        raise ValueError("an id argument is required")
    if len(id_col) != n:
        raise ValueError("wrong length for id")
    if istate_col is not None and len(istate_col) != n:
        raise ValueError("wrong length for istate")
    fit = _survcheck2(Y, id_col, istate_col, istate0=istate0)
    censorlabel = f"({Y.clabel})"
    trans = fit["transitions"]
    to_labels = fit.get("transition_to", [])
    if trans.size and to_labels:
        keep_cols = [label for label in to_labels if label != censorlabel]
        col_idx = [i for i, label in enumerate(to_labels) if label != censorlabel]
        trans_count = int(trans[:, col_idx].sum()) if col_idx else int(trans.sum())
    else:
        trans_count = int(trans.sum()) if trans.size else 0
    fit["n"] = {
        "id": len(set(id_col)),
        "observations": len(id_col),
        "transitions": trans_count,
    }
    fit["flag"]["duplicate"] = 0
    if omit is None:
        dummy = np.arange(1, n + 1)
    else:
        full = np.arange(1, n + len(omit) + 1)
        dummy = np.delete(full, np.asarray(omit, dtype=int) - 1)
    for key in ("overlap", "gap", "teleport", "jump"):
        if key in fit:
            temp = dict(fit[key])
            temp["row"] = dummy[np.asarray(temp["row"], dtype=int) - 1]
            fit[key] = temp
    fit["Y"] = Y
    fit["id"] = list(id_col)
    if omit is not None and len(omit):
        fit["na.action"] = omit
    fit["call"] = {"formula": formula, "id": id, "istate": istate}
    return SurvcheckResult(fit)
