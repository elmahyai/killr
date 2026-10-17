"""Collapse adjacent counting-process rows (survival::survcondense)."""

from __future__ import annotations

import re
from typing import Any, Mapping

import numpy as np

from survival.fromtimeline import Categorical, TimelineFrame
from survival.surv import SurvObject, is_Surv
from survival.surv_split import (
    _apply_subset,
    _as_table,
    _build_response,
    _column_len,
    _parse_surv_lhs,
    _status_factor,
)

_UNSET = object()


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


def _has_cluster_term(formula: str) -> bool:
    return bool(re.search(r"\bcluster\s*\(", formula, flags=re.IGNORECASE))


def _col_values(col: Any) -> list[Any]:
    if isinstance(col, Categorical):
        return list(col.values)
    if isinstance(col, np.ndarray):
        return col.tolist()
    return list(col)


def _same_or_missing(a: Any, b: Any) -> bool:
    if a is None or (isinstance(a, float) and np.isnan(a)):
        return b is None or (isinstance(b, float) and np.isnan(b))
    if b is None or (isinstance(b, float) and np.isnan(b)):
        return False
    return a == b


def _consecutive_same(col: Any, order: np.ndarray) -> np.ndarray:
    x = _col_values(col)
    x_ord = [x[i] for i in order]
    n = len(x_ord)
    out = np.zeros(n, dtype=bool)
    for i in range(n - 1):
        out[i] = _same_or_missing(x_ord[i], x_ord[i + 1])
    return out


def _rle(values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if values.size == 0:
        return np.array([], dtype=int), np.array([], dtype=bool)
    lengths: list[int] = []
    runs: list[bool] = []
    count = 1
    for i in range(1, values.size):
        if bool(values[i]) == bool(values[i - 1]):
            count += 1
        else:
            lengths.append(count)
            runs.append(bool(values[i - 1]))
            count = 1
    lengths.append(count)
    runs.append(bool(values[-1]))
    return np.asarray(lengths, dtype=int), np.asarray(runs, dtype=bool)


def _adjust_start_times(Y: np.ndarray, droprow: np.ndarray, order: np.ndarray) -> None:
    temp1_len, temp1_val = _rle(droprow)
    if temp1_len.size == 0:
        return
    temp2 = np.cumsum(temp1_len)
    if not np.any(droprow):
        return
    if temp2.size == 2:
        Y[order[temp2[0]], 0] = Y[order[0], 0]
        return
    if temp2.size == 3:
        Y[order[temp2[1]], 0] = Y[order[temp2[0]], 0]
        return
    if temp1_val[0]:
        j = temp2[np.arange(0, temp2.size - 1, 2)]
        k = 1 + np.concatenate([[0], temp2[np.arange(1, temp2.size - 1, 2)]])
    else:
        j = temp2[np.arange(1, temp2.size - 1, 2)]
        k = 1 + temp2[np.arange(0, temp2.size - 2, 2)]
    for jj, kk in zip(j, k):
        Y[order[int(jj)], 0] = Y[order[int(kk) - 1], 0]


def _build_model_frame(
    formula_text: str,
    data: Mapping[str, Any] | TimelineFrame,
    *,
    subset=None,
    weights=None,
    id: str | None = None,
) -> TimelineFrame:
    if id is None:
        raise ValueError("id is required")
    if "~" not in formula_text:
        raise ValueError("A formula argument is required")
    lhs, rhs = formula_text.split("~", 1)
    lhs = lhs.strip()
    rhs = rhs.strip()
    is_surv2, lhs_names = _parse_surv_lhs(lhs)
    if is_surv2:
        raise ValueError("the response must be a Surv object")
    table = _as_table(data)
    table, _ = _apply_subset(table, subset)
    response = _build_response(table, False, lhs_names)
    term_names = _split_rhs_terms(rhs)
    for name in term_names:
        if name not in table:
            raise ValueError(f"variable {name!r} not found in data")
    mf_names = [lhs, *term_names]
    mf_cols: list[Any] = [response]
    for name in term_names:
        mf_cols.append(table[name])
    if isinstance(id, str):
        if id not in table:
            raise ValueError(f"id variable {id!r} not found in data")
        mf_names.append("(id)")
        mf_cols.append(table[id])
    else:
        raise ValueError("invalid value for id")
    specials: dict[str, Any] = {"id": mf_cols[-1]}
    if weights is not None:
        if isinstance(weights, str):
            if weights not in table:
                raise ValueError(f"weights variable {weights!r} not found in data")
            wt_col = table[weights]
            wt_name = weights
        else:
            wt_col = weights
            wt_name = "(weights)"
        mf_names.append("(weights)")
        mf_cols.append(wt_col)
        specials["weights"] = wt_col
        specials["weights_name"] = wt_name
    return TimelineFrame(mf_names, mf_cols, specials)


def _lhs_is_surv_call(formula_text: str) -> bool:
    lhs = formula_text.split("~", 1)[0].strip()
    return lhs.startswith("Surv(")


def survcondense(
    formula,
    data=None,
    subset=None,
    weights=None,
    na_action=None,
    id=None,
    start=_UNSET,
    end=_UNSET,
    event=_UNSET,
):
    """Shorten a (time1, time2) survival dataset by merging adjacent intervals."""
    if id is None:
        raise ValueError("id is required")
    if formula is None or not isinstance(formula, str):
        raise ValueError("A formula argument is required")
    if data is None:
        raise ValueError("the data argument is required")
    if _has_cluster_term(formula):
        raise ValueError("function does not handle cluster() terms")
    if na_action is not None and na_action not in ("na.pass",):
        raise NotImplementedError("na.action is not supported yet")

    mf = _build_model_frame(formula, data, subset=subset, weights=weights, id=id)
    Y_obj = mf.columns[0]
    if not is_Surv(Y_obj):
        raise ValueError("the response must be a Surv object")
    if Y_obj.type not in ("counting", "mcounting"):
        raise ValueError("invalid survival type")
    Y = np.array(Y_obj.columns, dtype=float, copy=True)
    if np.any(np.isnan(Y)):
        raise ValueError("response cannot have missing values")

    id_col = mf.specials.get("id")
    id_arr = np.asarray(id_col, dtype=object)
    n = Y.shape[0]
    order = np.lexsort((Y[:, 1], id_arr))

    nvar = len(mf.names)
    xdup = np.ones(n, dtype=bool)
    for col_index in range(1, nvar):
        same = _consecutive_same(mf.columns[col_index], order)
        xdup &= same

    y_ord = Y[order]
    ydup = np.zeros(n, dtype=bool)
    ydup[:-1] = y_ord[:-1, 1] == y_ord[1:, 0]
    droprow = xdup & ydup

    _adjust_start_times(Y, droprow, order)

    mfname = list(mf.names)
    id_name = id if isinstance(id, str) else str(id)
    for i, name in enumerate(mfname):
        if name == "(id)":
            mfname[i] = id_name
        elif name == "(weights)":
            wt_name = mf.specials.get("weights_name", "(weights)")
            mfname[i] = str(wt_name)

    drop_rows = order[droprow]
    keep = np.ones(n, dtype=bool)
    keep[drop_rows] = False

    seen: set[str] = set()
    drop_cols = {0}
    for i, name in enumerate(mfname):
        if i == 0:
            continue
        if name in seen:
            drop_cols.add(i)
        else:
            seen.add(name)

    new_names: list[str] = []
    new_cols: list[Any] = []
    for i, (name, col) in enumerate(zip(mfname, mf.columns)):
        if i in drop_cols:
            continue
        if isinstance(col, (SurvObject,)):
            continue
        col_vals = _col_values(col)
        kept = [col_vals[r] for r in range(n) if keep[r]]
        if isinstance(col, Categorical):
            new_cols.append(Categorical(kept, col.levels))
        elif isinstance(col, np.ndarray):
            new_cols.append(np.asarray(kept, dtype=col.dtype))
        else:
            new_cols.append(kept)
        new_names.append(name)

    Y = Y[keep]
    states = Y_obj.states
    status = _status_factor(Y[:, 2], states)

    lhs_names = _parse_surv_lhs(formula.split("~", 1)[0].strip())[1]
    if _lhs_is_surv_call(formula):
        out_start = lhs_names[0] if start is _UNSET else start
        if end is _UNSET:
            out_end = lhs_names[1] if len(lhs_names) >= 2 else "tstop"
        else:
            out_end = end
        if event is _UNSET:
            out_event = lhs_names[2] if len(lhs_names) >= 3 else "event"
        else:
            out_event = event
        new_cols.append(Y[:, 0])
        new_names.append(out_start)
        new_cols.append(Y[:, 1])
        new_names.append(out_end)
        new_cols.append(status)
        new_names.append(out_event)
    else:
        raise ValueError("left hand side not recognized")

    return TimelineFrame(new_names, new_cols)


def survcondense_table(formula, data=None, **kwargs) -> dict[str, Any]:
    """Return survcondense output as a column dictionary."""
    frame = survcondense(formula, data, **kwargs)
    return {name: col for name, col in zip(frame.names, frame.columns)}
