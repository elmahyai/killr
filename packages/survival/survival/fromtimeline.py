"""Convert timeline survival data to counting-process form (survival::fromtimeline)."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

import numpy as np

from survival.surv import Surv, SurvObject, is_Surv
from survival.surv2 import Surv2Object


class Categorical:
    """Factor-like column with explicit level order."""

    __slots__ = ("values", "levels")

    def __init__(self, values, levels):
        self.values = list(values)
        self.levels = list(levels)


@dataclass
class TimelineFrame:
    """Minimal model.frame for fromtimeline / surv2counting."""

    names: list[str]
    columns: list[Any]
    specials: dict[str, Any] = field(default_factory=dict)

    def __len__(self):
        return len(self.columns[0]) if self.columns else 0

    def copy(self):
        return TimelineFrame(
            list(self.names),
            [self._copy_col(col) for col in self.columns],
            dict(self.specials),
        )

    @staticmethod
    def _copy_col(col):
        if isinstance(col, (SurvObject, Surv2Object)):
            return col
        if isinstance(col, Categorical):
            return Categorical(list(col.values), list(col.levels))
        if isinstance(col, np.ndarray):
            return np.array(col, copy=True)
        return list(col)

    def subset_rows(self, keep):
        keep = np.asarray(keep, dtype=bool)
        cols = []
        for col in self.columns:
            if isinstance(col, (SurvObject, Surv2Object)):
                mat = col.matrix()[keep]
                if isinstance(col, Surv2Object):
                    cols.append(
                        Surv2Object(
                            mat,
                            states=col.states,
                            clabel=col.clabel,
                            input_attributes=col.input_attributes,
                            repeated=col.repeated,
                            colnames=col.colnames,
                        )
                    )
                else:
                    cols.append(SurvObject(mat, col.type, col.states, col.clabel))
            elif isinstance(col, Categorical):
                cols.append(Categorical([col.values[i] for i, k in enumerate(keep) if k], col.levels))
            elif isinstance(col, np.ndarray):
                cols.append(np.array(col[keep], copy=True))
            else:
                cols.append([col[i] for i, k in enumerate(keep) if k])
        return TimelineFrame(list(self.names), cols, dict(self.specials))

    def reorder_rows(self, order):
        order = np.asarray(order, dtype=int)
        keep = np.zeros(len(self), dtype=bool)
        keep[order] = True
        out = self.subset_rows(keep)
        # subset_rows compresses; rebuild with explicit order
        cols = []
        for col in self.columns:
            if isinstance(col, (SurvObject, Surv2Object)):
                mat = col.matrix()[order]
                if isinstance(col, Surv2Object):
                    cols.append(
                        Surv2Object(
                            mat,
                            states=col.states,
                            clabel=col.clabel,
                            input_attributes=col.input_attributes,
                            repeated=col.repeated,
                            colnames=col.colnames,
                        )
                    )
                else:
                    cols.append(SurvObject(mat, col.type, col.states, col.clabel))
            elif isinstance(col, Categorical):
                cols.append(Categorical([col.values[i] for i in order], col.levels))
            elif isinstance(col, np.ndarray):
                cols.append(np.array(col[order], copy=True))
            else:
                cols.append([col[i] for i in order])
        return TimelineFrame(list(self.names), cols, dict(self.specials))

    def drop_columns(self, names_to_drop):
        drop = set(names_to_drop)
        names = []
        cols = []
        for name, col in zip(self.names, self.columns):
            if name not in drop:
                names.append(name)
                cols.append(col)
        return TimelineFrame(names, cols, dict(self.specials))

    def rename_column(self, old, new):
        names = [new if name == old else name for name in self.names]
        return TimelineFrame(names, list(self.columns), dict(self.specials))

    def set_column(self, index, value):
        cols = list(self.columns)
        cols[index] = value
        return TimelineFrame(list(self.names), cols, dict(self.specials))

    def without_first_column(self):
        return TimelineFrame(list(self.names[1:]), list(self.columns[1:]), dict(self.specials))

    def cbind(self, other: TimelineFrame):
        return TimelineFrame(
            list(self.names) + list(other.names),
            list(self.columns) + list(other.columns),
            dict(self.specials),
        )


def _is_surv2_obj(x):
    return isinstance(x, Surv2Object)


def _casefold(text):
    return str(text).lower()


def _duplicated(values, from_last=False):
    n = len(values)
    out = np.zeros(n, dtype=bool)
    if from_last:
        seen = set()
        for i in range(n - 1, -1, -1):
            key = values[i]
            if key in seen:
                out[i] = True
            else:
                seen.add(key)
    else:
        seen = set()
        for i, key in enumerate(values):
            if key in seen:
                out[i] = True
            else:
                seen.add(key)
    return out


def _tmerge3(idi, miss):
    n = len(idi)
    index = np.zeros(n, dtype=int)
    oldid = None
    k = 0
    for i in range(n):
        if idi[i] != oldid:
            k = 0
            oldid = idi[i]
        if miss[i]:
            index[i] = k
        else:
            index[i] = i + 1
            k = i + 1
    return index


def _column_missing(col):
    if isinstance(col, Categorical):
        col = col.values
    if isinstance(col, np.ndarray):
        if col.dtype == object:
            return np.array([v is None or (isinstance(v, float) and math.isnan(v)) for v in col], dtype=bool)
        return np.isnan(col)
    out = []
    for v in col:
        if v is None:
            out.append(True)
        elif isinstance(v, float) and math.isnan(v):
            out.append(True)
        else:
            out.append(False)
    return np.array(out, dtype=bool)


def _surv_from_event(time, event, levels=None):
    if levels is not None:
        index = {level: code for code, level in enumerate(levels)}
        status = []
        for value in event:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                status.append(math.nan)
            elif value not in index:
                status.append(math.nan)
            else:
                status.append(float(index[value]))
        clabel = levels[0]
        states = levels[1:]
        columns = np.column_stack([np.asarray(time, dtype=float), np.asarray(status, dtype=float)])
        return SurvObject(columns, "mright", states, clabel)
    return Surv(time, event=event)


def _parse_surv_lhs(lhs: str):
    m = re.match(r"Surv2?\s*\(\s*([^,]+)\s*,\s*([^)]+)\s*\)\s*$", lhs.strip())
    if not m:
        raise ValueError("response must be a survival object")
    return m.group(1).strip(), m.group(2).strip(), lhs.strip().startswith("Surv2")


def _parse_formula(formula: str):
    if "~" not in formula:
        raise ValueError("a formula argument is required")
    lhs, rhs = formula.split("~", 1)
    time_name, event_name, is_surv2 = _parse_surv_lhs(lhs)
    rhs = rhs.strip()
    if rhs != ".":
        raise ValueError("only Surv(...) ~ . formulas are supported")
    return time_name, event_name, is_surv2


def _as_table(data: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(data, TimelineFrame):
        return {name: col for name, col in zip(data.names, data.columns)}
    return dict(data)


def _build_model_frame(formula: str, data: Mapping[str, Any], subset=None, id=None):
    if data is None:
        raise ValueError("the data argument is required")
    if id is None:
        raise ValueError("the id argument is required")
    table = _as_table(data)
    time_name, event_name, _ = _parse_formula(formula)
    if time_name not in table or event_name not in table:
        raise ValueError("response must be a survival object")
    id_col = table[id] if isinstance(id, str) else id
    n = len(id_col)
    keep = np.ones(n, dtype=bool)
    if subset is not None:
        if callable(subset):
            keep = np.asarray(subset(table), dtype=bool)
        else:
            keep = np.asarray(subset, dtype=bool)
    names = list(table.keys())
    cols = {name: table[name] for name in names}
    if keep.shape[0] != n:
        raise ValueError("subset length mismatch")
    for key in cols:
        col = cols[key]
        if isinstance(col, Categorical):
            cols[key] = Categorical([col.values[i] for i in range(n) if keep[i]], col.levels)
        elif isinstance(col, np.ndarray):
            cols[key] = col[keep]
        else:
            cols[key] = [col[i] for i in range(n) if keep[i]]
    id_col = cols[id] if isinstance(id, str) else [id_col[i] for i in range(n) if keep[i]]
    n = len(id_col)
    time = cols[time_name]
    event = cols[event_name]
    levels = event.levels if isinstance(event, Categorical) else None
    response = _surv_from_event(time, event.values if isinstance(event, Categorical) else event, levels)
    resp_name = f"Surv({time_name}, {event_name})"
    covariate_names = [name for name in names if name not in (time_name, event_name)]
    mf_names = [resp_name, *covariate_names, "(id)"]
    mf_cols = [response]
    for name in covariate_names:
        mf_cols.append(cols[name])
    mf_cols.append(list(id_col) if not isinstance(id_col, np.ndarray) else id_col)
    specials = {"id": mf_cols[-1]}
    had_istate = "istate" in cols
    return TimelineFrame(mf_names, mf_cols, specials), had_istate


def _model_response(mf: TimelineFrame):
    return mf.columns[0]


def _model_extract(mf: TimelineFrame, name: str):
    if name == "id":
        return mf.specials.get("id")
    idx = mf.names.index(f"({name})") if f"({name})" in mf.names else None
    if idx is not None:
        return mf.columns[idx]
    if name in mf.names:
        return mf.columns[mf.names.index(name)]
    return None


def _response_matrix(y):
    if _is_surv2_obj(y):
        return y.matrix(), y.states, getattr(y, "repeated", False)
    if is_Surv(y):
        return y.matrix(), y.states, None
    raise ValueError("response must be a survival object")


def _surv2counting(mf: TimelineFrame, repeated=False, lvcf=True):
    y = _model_response(mf)
    mat, states, y_repeated = _response_matrix(y)
    n = mat.shape[0]
    if repeated is False and y_repeated not in (None, False):
        repeated = y_repeated

    id_col = _model_extract(mf, "id")
    if id_col is None or len(id_col) != n:
        raise ValueError("id statement is required")

    if any(v is None or (isinstance(v, float) and math.isnan(v)) for v in id_col):
        raise ValueError("id and time cannot be missing")
    if any(math.isnan(mat[i, 0]) for i in range(n)):
        raise ValueError("id and time cannot be missing")

    isort = np.lexsort((mat[:, 0], np.asarray(id_col, dtype=object)))
    id2 = np.asarray(id_col, dtype=object)[isort]
    y2 = mat[isort]
    first = ~_duplicated(id2, from_last=False)
    last = ~_duplicated(id2, from_last=True)

    seen_pairs = set()
    for i in range(n):
        key = (id2[i], float(y2[i, 0]))
        if key in seen_pairs:
            raise ValueError("duplicated time for an id")
        seen_pairs.add(key)

    mf2 = mf.reorder_rows(isort).subset_rows(~last)
    id3 = id2[~last]

    if isinstance(id3[0], (str, bytes)) or not np.issubdtype(np.asarray(id3).dtype, np.integer):
        _, inv = np.unique(id3, return_inverse=True)
        idi = inv + 1
    else:
        idi = np.asarray(id3, dtype=int)

    if lvcf:
        skip = {0}
        for j, name in enumerate(mf2.names):
            if name.startswith("("):
                skip.add(j)
        for j in range(len(mf2.columns)):
            if j in skip:
                continue
            col = mf2.columns[j]
            miss = _column_missing(col)
            if not np.any(miss):
                continue
            k = _tmerge3(idi, miss)
            update = miss & (k > 0)
            if not np.any(update):
                continue
            src = (k[update] - 1).astype(int)
            if isinstance(col, np.ndarray) and col.ndim == 2:
                col = np.array(col, copy=True)
                col[update] = col[src]
                mf2.columns[j] = col
            elif isinstance(col, np.ndarray):
                col = np.array(col, copy=True)
                col[update] = col[src]
                mf2.columns[j] = col
            elif isinstance(col, Categorical):
                values = list(col.values)
                for u, s in zip(np.where(update)[0], src):
                    values[u] = values[s]
                mf2.columns[j] = Categorical(values, col.levels)
            else:
                values = list(col)
                for u, s in zip(np.where(update)[0], src):
                    values[u] = values[s]
                mf2.columns[j] = values

    if np.any(np.isnan(y2[:, 1])):
        if states is not None:
            y2 = np.array(y2, copy=True)
            y2[:, 1] = np.where(np.isnan(y2[:, 1]), 0.0, y2[:, 1])

    if isinstance(repeated, str) and _casefold(repeated) == "first":
        new_y2 = np.array(y2, copy=True)
        i = 0
        while i < n:
            j = i
            while j + 1 < n and id2[j + 1] == id2[i]:
                j += 1
            seg = y2[i : j + 1, 1]
            seen = set()
            for t in range(len(seg)):
                val = seg[t]
                if val == 0 or (not math.isnan(val) and val in seen):
                    seg[t] = 0
                elif not math.isnan(val):
                    seen.add(val)
            new_y2[i : j + 1, 1] = seg
            i = j + 1
        y2 = new_y2

    censored = np.isnan(y2[:, 1]) | (y2[:, 1] == 0)
    istate2 = None
    if np.all(censored[first]):
        istate2 = None
    elif np.any(censored[first]):
        raise ValueError("everyone or no one should have an initial state")
    else:
        istate2 = y2[~last, 1].copy()
        cens = censored[~last]
        if np.any(cens):
            k = _tmerge3(idi, cens)
            istate2 = np.array(istate2, copy=True)
            istate2[cens] = istate2[k[cens] - 1]
        level_labels = states if states is not None else []
        codes = istate2.astype(int)
        istate_vals = [level_labels[c - 1] if 0 < c <= len(level_labels) else str(c) for c in codes]
        mf2.names = list(mf2.names)
        mf2.columns = list(mf2.columns)
        mf2.names.append("(istate)")
        mf2.columns.append(Categorical(istate_vals, list(level_labels)))

        istate = _model_extract(mf, "istate")
        if istate is not None:
            msg = "istate argument does not agree with initial Surv2 values"
            if isinstance(istate, (int, float, np.integer, np.floating)):
                if np.any(istate2 != istate):
                    raise ValueError(msg)
            else:
                if isinstance(istate, Categorical):
                    ist_fac = istate
                else:
                    istate_arr = np.asarray(istate)
                    ist_fac = Categorical(list(istate_arr), sorted(set(istate_arr), key=str))
                itemp = [ist_fac.levels.index(level) + 1 if level in ist_fac.levels else 0 for level in (states or [])]
                if any(x == 0 for x in itemp):
                    raise ValueError(msg)
                mapped = np.array([itemp[int(v) - 1] if v > 0 else 0 for v in istate2], dtype=float)
                istate_num = np.array(
                    [ist_fac.levels.index(v) + 1 if v in ist_fac.levels else math.nan for v in ist_fac.values],
                    dtype=float,
                )
                if np.any(mapped != istate_num[~last]):
                    raise ValueError(msg)

    status = y2[~first, 1].copy()
    if isinstance(repeated, bool):
        if not repeated and istate2 is not None:
            status[status == istate2] = 0
    elif not (isinstance(repeated, str) and _casefold(repeated) == "first"):
        raise ValueError("invalid value for repeated option")

    if states is not None:
        labels = ["censor", *states]
        status_cat = Categorical(
            [labels[int(s)] if not math.isnan(s) and 0 <= int(s) < len(labels) else math.nan for s in status],
            labels,
        )
    else:
        status_cat = status

    tstart = y2[~last, 0]
    tstop = y2[~first, 0]
    ev = status_cat.values if isinstance(status_cat, Categorical) else status_cat
    lev = status_cat.levels if isinstance(status_cat, Categorical) else None
    if len(np.unique(id3)) == len(id3):
        if lev is not None:
            new_resp = _surv_from_event(tstop, ev, lev)
        else:
            new_resp = Surv(tstop, event=ev)
    elif lev is not None:
        index = {level: code for code, level in enumerate(lev)}
        codes = np.array([float(index[v]) if v in index else math.nan for v in ev], dtype=float)
        columns = np.column_stack([tstart, tstop, codes])
        new_resp = SurvObject(columns, "mcounting", lev[1:], lev[0])
    else:
        new_resp = Surv(tstart, time2=tstop, event=ev)

    mf2 = mf2.set_column(0, new_resp)
    jj = np.argsort(isort[~last])
    return mf2.reorder_rows(jj)


def _guess_yname(formula: str, ny: int, existing_names: Sequence[str], yname_default: Sequence[str]):
    time_name, event_name, _ = _parse_formula(formula)
    yname = list(yname_default)
    if ny == 2:
        yname = [time_name, yname[-1]]
    else:
        yname = [f"{time_name}1", f"{time_name}2", event_name]
    conflict = [i for i, name in enumerate(yname) if name in existing_names]
    for i in conflict:
        yname[i] = f"_{yname[i]}_"
    return yname


def fromtimeline(
    formula,
    data,
    subset=None,
    id=None,
    repeated=False,
    lvcf=True,
    yname=("tstart", "tstop", "status"),
    *,
    _yname_supplied=False,
):
    """Build counting-process data from a timeline-style model frame."""
    if formula is None:
        raise ValueError("a formula argument is required")
    if data is None:
        raise ValueError("the data argument is required")
    if id is None:
        raise ValueError("the id argument is required")

    formula_text = formula if isinstance(formula, str) else str(formula)
    mf, had_istate = _build_model_frame(formula_text, data, subset=subset, id=id)
    y = _model_response(mf)
    if not (is_Surv(y) or _is_surv2_obj(y)):
        raise ValueError("response must be a survival object")
    if is_Surv(y) and y.type in ("counting", "mcounting"):
        raise ValueError("response cannot be of counting process type")
    id_col = _model_extract(mf, "id")
    if id_col is None or not np.any(_duplicated(np.asarray(id_col, dtype=object))):
        raise ValueError("data does not appear to be timeline data")

    new = _surv2counting(mf, repeated=repeated, lvcf=lvcf)

    ii = new.names.index("(istate)") if "(istate)" in new.names else -1
    if ii >= 0 and not had_istate:
        new = new.rename_column("(istate)", "istate")

    new = new.drop_columns(["(id)"])

    yy = new.columns[0]
    states = yy.states
    mat = yy.matrix()
    ny = mat.shape[1]
    if states is None:
        status_vals = mat[:, ny - 1]
        status = status_vals
    else:
        labels = ["censor", *states]
        status = Categorical(
            [labels[int(v)] if not math.isnan(v) and 0 <= int(v) < len(labels) else math.nan for v in mat[:, ny - 1]],
            labels,
        )

    if ny == 3:
        tdata_names = ["tstart", "tstop", "status"]
        tdata_cols = [mat[:, 0], mat[:, 1], status.values if isinstance(status, Categorical) else status]
    else:
        tdata_names = ["tstart", "status"]
        tdata_cols = [mat[:, 0], status.values if isinstance(status, Categorical) else status]

    yname_list = list(yname)
    if _yname_supplied:
        existing = set(new.names)
        if any(name in existing for name in yname_list):
            raise ValueError("element of yname conflicts with an existing name in the data")
        if ny == 2:
            if len(yname_list) not in (2, 3):
                raise ValueError("wrong length for yname")
            tdata_names = [yname_list[0], yname_list[-1]]
        else:
            if len(yname_list) != 3:
                raise ValueError("wrong length for yname")
            tdata_names = yname_list
    else:
        tdata_names = _guess_yname(formula_text, ny, new.names, yname_list)

    tframe = TimelineFrame(tdata_names, tdata_cols)
    return new.without_first_column().cbind(tframe)


def fromtimeline_table(formula, data, **kwargs):
    """Return fromtimeline output as a column dictionary."""
    frame = fromtimeline(formula, data, **kwargs)
    return {name: col for name, col in zip(frame.names, frame.columns)}
