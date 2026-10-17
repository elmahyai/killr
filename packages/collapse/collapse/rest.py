"""The rest of collapse: grouping, frames, summaries, and small helpers.

Arrays are NumPy. A data frame is a dict of columns, or a ``DF``. A grouped
lag still comes from ``series``. Several factors are centered by alternating
projections; collapse itself sends that path to fixest.
"""

from __future__ import annotations

import csv
import math
import os
import re
from pathlib import Path

import numpy as np

from collapse.fast import (
    CollapseError,
    Frame,
    Mat,
    Vec,
    _fmt,
    _level_key,
    _level_name,
    _missing,
    _nth,
    _vector,
    factor,
    ffirst,
    flast,
    fmax,
    fmean,
    fmin,
    fsum,
    fvar,
)
from collapse.series import fbetween, fdiff, fgrowth, flag, fscale, fwithin

DATA = Path(__file__).resolve().parent / "data"

_OPTIONS = {
    "nthreads": 1,
    "na.rm": True,
    "sort": True,
    "stable.algo": True,
    "mask": None,
    "remove": None,
    "stub": True,
    "verbose": 1,
    "digits": 2,
}


def _opt(name):
    return _OPTIONS[name]


# ---------------------------------------------------------------------------
# containers
# ---------------------------------------------------------------------------


class DF:
    """A data frame. Columns keep their dtype. ``rows`` are optional names."""

    def __init__(self, columns, rows=None, groups=None, index=None):
        self.columns = {}
        for name, values in dict(columns).items():
            self.columns[str(name)] = _as_col(values)
        self.rows = None if rows is None else [str(name) for name in rows]
        self.groups = groups
        self.index = index
        self.labels = {}

    def __repr__(self):
        return str(self)

    def __str__(self):
        names = list(self.columns)
        lines = [" ".join(names)]
        nrow = self.nrow
        for i in range(nrow):
            body = " ".join(_cell(self.columns[name][i]) for name in names)
            if self.rows:
                body = f"{self.rows[i]} {body}"
            lines.append(body)
        return "\n".join(lines)

    @property
    def nrow(self):
        if not self.columns:
            return 0
        return int(len(next(iter(self.columns.values()))))

    def copy(self):
        copied = DF(
            {name: values.copy() for name, values in self.columns.items()},
            self.rows,
            self.groups,
            self.index,
        )
        copied.labels = dict(self.labels)
        return copied


class Group:
    """Group ids. ``codes`` is 1-based and follows ``levels``."""

    def __init__(self, codes, levels, sizes, vars=None):
        self.codes = np.asarray(codes, dtype=np.int32)
        self.levels = [str(level) for level in levels]
        self.sizes = np.asarray(sizes, dtype=np.int32)
        self.vars = vars
        self.n = int(len(self.levels))

    def __repr__(self):
        return f"GRP(n={self.n})"


class Acf:
    def __init__(self, acf, kind, n_used, lag, series):
        self.acf = np.asarray(acf, dtype=np.float64)
        self.type = kind
        self.n_used = int(n_used)
        self.lag = np.asarray(lag, dtype=np.float64)
        self.series = series

    def __str__(self):
        return " ".join(_fmt(value) for value in np.ravel(self.acf, order="F"))


def _as_col(values):
    if isinstance(values, Vec):
        return np.array(values.values, copy=True)
    if isinstance(values, np.ndarray):
        return values.copy() if values.dtype != object else values.copy()
    array = np.asarray(values)
    if array.dtype.kind in "UOS":
        return np.asarray(list(values), dtype=object)
    return array


def _cell(value):
    if _missing(value) or value is None:
        return "NA"
    if isinstance(value, (bool, np.bool_)):
        return "TRUE" if bool(value) else "FALSE"
    if isinstance(value, (float, np.floating)):
        return _fmt(float(value))
    if isinstance(value, (int, np.integer)):
        return str(int(value))
    return str(value)


def _is_df(x):
    return isinstance(x, (DF, dict, Frame))


def _columns(x):
    if isinstance(x, DF):
        return x.columns
    if isinstance(x, Frame):
        return x.columns
    if isinstance(x, dict):
        return {str(name): _as_col(values) for name, values in x.items()}
    raise CollapseError("expected a data frame")


def _df(x):
    if isinstance(x, DF):
        return x
    return DF(_columns(x))


def _nrow(x):
    if isinstance(x, DF):
        return x.nrow
    if isinstance(x, Mat):
        return int(x.values.shape[0])
    if isinstance(x, np.ndarray) and x.ndim == 2:
        return int(x.shape[0])
    columns = _columns(x)
    if not columns:
        return 0
    return int(len(next(iter(columns.values()))))


def _numeric_col(values):
    try:
        out = np.asarray(values, dtype=np.float64)
    except (TypeError, ValueError):
        return None
    if out.ndim != 1:
        return None
    return out


def _is_numeric_col(values):
    return _numeric_col(values) is not None and np.asarray(values).dtype.kind in "iufb"


def _object_list(values):
    if isinstance(values, np.ndarray) and values.dtype == object:
        return list(values)
    if isinstance(values, np.ndarray) and values.dtype.kind in "iufb":
        return [None if math.isnan(float(v)) else (int(v) if float(v).is_integer() else float(v)) for v in values]
    return list(values)


# ---------------------------------------------------------------------------
# TRA
# ---------------------------------------------------------------------------


_TRA = {
    "replace_na": 0, "na": 0, "replace_NA": 0, "NA": 0,
    "replace_fill": 1, "fill": 1,
    "replace": 2,
    "-": 3, "-+": 4, "/": 5, "%": 6, "+": 7, "*": 8, "%%": 9, "-%%": 10,
}


def _tra_code(fun):
    if fun is None:
        fun = "-"
    if isinstance(fun, (int, np.integer)):
        return int(fun)
    key = str(fun)
    if key not in _TRA:
        raise CollapseError(f"unknown transformation: {fun}")
    return _TRA[key]


def _trunc(value):
    if not math.isfinite(value):
        return value
    return float(math.trunc(value))


def _one_tra(x, stat, code):
    if code == 0:
        return stat if _missing(x) or (isinstance(x, float) and math.isnan(x)) else x
    if code == 1:
        return stat
    if code == 2:
        return x if _missing(x) or (isinstance(x, float) and math.isnan(x)) else stat
    if not math.isfinite(x):
        return x
    if code == 3:
        return x - stat
    if code == 5:
        return x / stat
    if code == 6:
        return x * (100.0 / stat)
    if code == 7:
        return x + stat
    if code == 8:
        return x * stat
    if code == 9:
        z = x * (1.0 / stat)
        return x - _trunc(z) * stat if math.isfinite(z) else z
    if code == 10:
        z = x * (1.0 / stat)
        return _trunc(z) * stat if math.isfinite(z) else z
    return x - stat


def _tra_1d(values, stats, code, codes):
    values = np.asarray(values, dtype=np.float64).reshape(-1)
    stats = np.asarray(stats, dtype=np.float64).reshape(-1)
    out = np.empty(values.shape[0], dtype=np.float64)
    if codes is None:
        if stats.size != 1:
            raise CollapseError("if g is missing, STATS must have length 1")
        stat = float(stats[0])
        for i, value in enumerate(values):
            out[i] = _one_tra(float(value), stat, code)
        return out
    if code == 4:
        acc = 0.0
        n = 0
        for i, value in enumerate(values):
            stat = float(stats[int(codes[i])])
            if math.isfinite(value):
                out[i] = value - stat
                if math.isfinite(stat):
                    acc += stat
                    n += 1
            else:
                out[i] = value
        if n:
            out += acc / n
        return out
    for i, value in enumerate(values):
        out[i] = _one_tra(float(value), float(stats[int(codes[i])]), code)
    return out


def _stat_values(stats):
    if isinstance(stats, Vec):
        return stats.values
    if isinstance(stats, Mat):
        return stats.values
    if isinstance(stats, Frame):
        return stats.columns
    if isinstance(stats, DF):
        return {name: _numeric_col(values) for name, values in stats.columns.items()}
    return np.asarray(stats, dtype=np.float64)


def apply_tra(x, stats, fun, g, layout):
    """Apply a collapse transformation. ``stats`` is already reduced."""
    code = _tra_code(fun)
    codes = None if g is None else factor(g)[0]
    if layout == "vector":
        base = x.values if isinstance(x, Vec) else _vector(x)
        return Vec(_tra_1d(base, _stat_values(stats), code, codes))
    if layout == "matrix":
        values = x.values if isinstance(x, Mat) else np.asarray(x, dtype=np.float64)
        reduced = _stat_values(stats)
        if reduced.ndim == 1:
            reduced = reduced.reshape(1, -1)
        if reduced.ndim == 0 or reduced.size == 1:
            reduced = np.full((1, values.shape[1]), float(np.reshape(reduced, -1)[0]))
        elif reduced.ndim == 1:
            reduced = reduced.reshape(1, -1) if reduced.size == values.shape[1] else reduced.reshape(-1, values.shape[1])
        columns = []
        for j in range(values.shape[1]):
            columns.append(_tra_1d(values[:, j], reduced[:, j] if reduced.shape[0] > 1 else reduced[0, j : j + 1], code, codes))
        return Mat(np.column_stack(columns))
    columns = _columns(x)
    reduced = _stat_values(stats)
    out = {}
    for name, column in columns.items():
        numeric = _numeric_col(column)
        stat = reduced[name] if isinstance(reduced, dict) else reduced
        stat = np.asarray(stat, dtype=np.float64).reshape(-1)
        out[name] = _tra_1d(numeric, stat, code, codes)
    return DF(out)


def TRA(x, STATS, FUN="-", g=None, set=False):
    code = _tra_code(FUN)
    if _is_df(x):
        result = apply_tra(x, STATS, code, g, "frame")
    elif isinstance(x, Mat) or (isinstance(x, np.ndarray) and np.asarray(x).ndim == 2):
        result = apply_tra(x, STATS, code, g, "matrix")
    else:
        result = apply_tra(x, STATS, code, g, "vector")
    if set and isinstance(x, np.ndarray):
        x[...] = result.values if not isinstance(result, DF) else x
    return result


def TRA_default(x, STATS, FUN="-", g=None, set=False):
    return TRA(x, STATS, FUN, g, set)


def TRA_matrix(x, STATS, FUN="-", g=None, set=False):
    return apply_tra(x, STATS, FUN, g, "matrix")


def TRA_data_frame(x, STATS, FUN="-", g=None, set=False):
    return apply_tra(x, STATS, FUN, g, "frame")


def setTRA(x, STATS, FUN="-", g=None):
    TRA(x, STATS, FUN, g, True)
    return x


def _row_op(x, v, fun):
    return TRA(x, v, fun)


def op_rr(X, v):
    return _row_op(X, v, "replace_fill")


def op_radd(X, v):
    return _row_op(X, v, "+")


def op_rsub(X, v):
    return _row_op(X, v, "-")


def op_rmul(X, v):
    return _row_op(X, v, "*")


def op_rdiv(X, v):
    return _row_op(X, v, "/")


def _col_op(X, V, fun):
    if _is_df(X):
        columns = _columns(X)
        if _is_df(V):
            other = _columns(V)
            return DF({name: _numeric_col(columns[name]) + 0 if fun == "replace_fill" else TRA(columns[name], other[name], fun).values for name in columns})
        if fun == "replace_fill":
            return DF({name: np.full(len(column), V, dtype=np.float64) for name, column in columns.items()})
        return DF({name: TRA(column, V, fun).values for name, column in columns.items()})
    values = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
    if values.ndim == 2:
        scalar = float(np.asarray(V, dtype=np.float64).reshape(-1)[0])
        if fun == "replace_fill":
            return Vec(np.full(values.shape[1], scalar))
        code = _tra_code(fun)
        if code == 7:
            return Mat(values + scalar)
        if code == 3:
            return Mat(values - scalar)
        if code == 8:
            return Mat(values * scalar)
        if code == 5:
            return Mat(values / scalar)
        return Mat(np.array([[_one_tra(float(item), scalar, code) for item in row] for row in values]))
    if fun == "replace_fill":
        return Vec(np.full(values.shape, float(V)))
    return TRA(values.reshape(-1), V, fun)


def op_cr(X, V):
    return _col_op(X, V, "replace_fill")


def op_cadd(X, V):
    return _col_op(X, V, "+")


def op_csub(X, V):
    return _col_op(X, V, "-")


def op_cmul(X, V):
    return _col_op(X, V, "*")


def op_cdiv(X, V):
    return _col_op(X, V, "/")


# ---------------------------------------------------------------------------
# grouping
# ---------------------------------------------------------------------------


def _raw_values(x):
    if isinstance(x, np.ndarray):
        if x.dtype.kind in "iufb":
            return [None if (isinstance(v, (float, np.floating)) and math.isnan(float(v))) else v.item() for v in x]
        return [None if v is None else v.item() if hasattr(v, "item") else v for v in x]
    return [None if _missing(v) else v for v in x]


def q_levels(x, na_exclude=True, sort=True):
    values = _raw_values(x)
    levels = []
    seen = {}
    for value in values:
        if value is None or _missing(value):
            continue
        key = _level_key(value)
        if key not in seen:
            seen[key] = len(levels)
            levels.append(value)
    order = list(range(len(levels)))
    if sort:
        order = sorted(order, key=lambda i: _level_key(levels[i]))
    remap = {old: new for new, old in enumerate(order)}
    levels = [levels[i] for i in order]
    codes = []
    for value in values:
        if value is None or _missing(value):
            codes.append(None if na_exclude else len(levels) + 1)
        else:
            codes.append(remap[seen[_level_key(value)]] + 1)
    if not na_exclude and any(code is not None and code == len(levels) + 1 for code in codes):
        levels = levels + [None]
    return codes, [_level_name(level) if level is not None else "NA" for level in levels]


def qF(x, ordered=False, na_exclude=True, sort=None, drop=False, keep_attr=True, method="auto"):
    del ordered, keep_attr, method
    if sort is None:
        sort = _opt("sort")
    codes, levels = q_levels(x, na_exclude=na_exclude, sort=sort)
    if drop:
        used = {code for code in codes if code is not None}
        keep = [i for i in range(len(levels)) if (i + 1) in used]
        remap = {old + 1: new + 1 for new, old in enumerate(keep)}
        levels = [levels[i] for i in keep]
        codes = [None if code is None else remap[code] for code in codes]
    out = np.array([np.nan if code is None else code for code in codes], dtype=np.float64)
    return Vec(out, levels)


def qG(x, ordered=False, na_exclude=True, sort=None, return_groups=False, method="auto"):
    del ordered, method
    if sort is None:
        sort = _opt("sort")
    codes, levels = q_levels(x, na_exclude=na_exclude, sort=sort)
    out = np.array([np.nan if code is None else code for code in codes], dtype=np.float64)
    result = Vec(out)
    result.n_groups = len(levels)
    result.groups = levels if return_groups else None
    return result


def _grp_from_values(values, sort=True):
    codes, levels = q_levels(values, na_exclude=False, sort=sort)
    ids = np.array([len(levels) if code is None else code for code in codes], dtype=np.int32)
    sizes = np.bincount(ids, minlength=len(levels) + 1)[1:]
    return Group(ids, levels, sizes)


def GRP_default(X, by=None, sort=None, decreasing=False, na_last=True, return_groups=True, return_order=False, method="auto", call=True):
    del decreasing, na_last, return_groups, return_order, method, call
    if sort is None:
        sort = _opt("sort")
    if isinstance(X, Group):
        return X
    if _is_df(X):
        frame = _df(X)
        names = list(frame.columns) if by is None else [by] if isinstance(by, str) else list(by)
        if len(names) == 1:
            grouped = _grp_from_values(frame.columns[names[0]], sort=sort)
        else:
            rows = [tuple(_cell(frame.columns[name][i]) for name in names) for i in range(frame.nrow)]
            grouped = _grp_from_values(rows, sort=sort)
        grouped.vars = names
        return grouped
    grouped = _grp_from_values(X, sort=sort)
    grouped.vars = None
    return grouped


def GRP(X, by=None, sort=None, **kwargs):
    return GRP_default(X, by=by, sort=sort, **kwargs)


def GRPnames(x, force_char=True, sep="."):
    del force_char
    if not isinstance(x, Group):
        x = GRP(x)
    return list(x.levels) if sep else list(x.levels)


def GRPid(x, sort=False, g=None, **kwargs):
    del sort, kwargs
    obj = g if isinstance(g, Group) else x if isinstance(x, Group) else GRP(x)
    return Vec(obj.codes.astype(np.float64))


def GRPN(x, expand=True, g=None, **kwargs):
    del kwargs
    obj = g if isinstance(g, Group) else x if isinstance(x, Group) else GRP_default(x, sort=False)
    if expand:
        return Vec(obj.sizes[obj.codes - 1].astype(np.float64))
    return Vec(obj.sizes.astype(np.float64))


def groupid(x, o=None, start=1, na_skip=False, check_o=True):
    values = _raw_values(x)
    n = len(values)
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return Vec(out)

    def at(i):
        return values[i]

    order = list(range(n)) if o is None else [int(v) - 1 for v in o]
    ident = start
    prev = None
    begun = False
    for pos in order:
        value = at(pos)
        missing = value is None or _missing(value)
        if na_skip and missing:
            out[pos] = np.nan
            continue
        if not begun:
            out[pos] = ident
            prev = value
            begun = True
            continue
        if missing or value != prev:
            ident += 1
        out[pos] = ident
        prev = value
    result = Vec(out)
    result.n_groups = ident - start + 1
    del check_o
    return result


def seqid(x, o=None, del_=1, start=1, na_skip=False, skip_seq=False, check_o=True):
    values = [None if v is None or _missing(v) else int(v) for v in _raw_values(np.asarray(x))]
    n = len(values)
    out = np.empty(n, dtype=np.float64)
    order = list(range(n)) if o is None else [int(v) - 1 for v in o]
    ident = start
    prev = None
    begun = False
    nafill = 2**31 - 10**7
    for pos in order:
        value = values[pos]
        if na_skip and value is None:
            out[pos] = np.nan
            if skip_seq and begun and prev is not None:
                prev += del_
            continue
        current = nafill if value is None else value
        if not begun:
            out[pos] = ident
            prev = current
            begun = True
            continue
        if current - prev != del_:
            ident += 1
        out[pos] = ident
        prev = current
    result = Vec(out)
    result.n_groups = ident - start + 1
    del check_o
    return result


def timeid(x, factor=False, ordered=None, extra=False):
    if ordered is None:
        ordered = factor
    values = np.asarray(x, dtype=np.float64)
    if np.isnan(values).any():
        raise CollapseError("a time variable may not contain missing values")
    uniq, first = np.unique(values, return_index=True)
    order = np.argsort(first, kind="stable")
    uniq = uniq[order]
    # map each observation to its first-appearance unique slot, then scale
    slots = {float(value): i for i, value in enumerate(uniq)}
    # recompute unique in sorted order for the step
    ordered_u = np.sort(uniq)
    if ordered_u.size == 1:
        gcd = 1.0
    else:
        steps = np.diff(ordered_u)
        gcd = float(_gcd_list(steps))
    lo, hi = float(ordered_u[0]), float(ordered_u[-1])
    scaled = ordered_u.copy()
    if lo != 1 or gcd != 1:
        scaled = scaled - (lo - gcd)
    if gcd != 1:
        scaled = scaled / gcd
    scaled = np.rint(scaled)
    lookup = {float(ordered_u[i]): scaled[i] for i in range(ordered_u.size)}
    out = np.array([lookup[float(v)] for v in values], dtype=np.float64)
    result = Vec(out)
    result.n_groups = int(round((hi - lo) / gcd)) + 1
    result.unique_ints = scaled
    del factor, ordered, extra
    return result


def _gcd_list(steps):
    def gcd(a, b):
        a, b = abs(int(round(float(a)))), abs(int(round(float(b))))
        while b:
            a, b = b, a % b
        return a
    value = 0
    for step in steps:
        value = gcd(value, step)
    return value or 1


def is_irregular(x, any_id=True):
    del any_id
    tid = timeid(x, extra=True)
    return bool(tid.n_groups != len(tid.unique_ints))


def finteraction(*args, sort=None, **kwargs):
    del kwargs
    if sort is None:
        sort = _opt("sort")
    cols = [_raw_values(arg) for arg in args]
    labels = [".".join(_cell(col[i]) for col in cols) for i in range(len(cols[0]))]
    codes, levels = q_levels(labels, na_exclude=False, sort=sort)
    return Vec(np.array(codes, dtype=np.float64), levels)


def itn(*args, **kwargs):
    return finteraction(*args, **kwargs)


def group(*args, starts=False, group_sizes=False, **kwargs):
    del starts, group_sizes
    return Vec(finteraction(*args, **kwargs).values)


def groupv(x, cols=None, starts=False, group_sizes=False, **kwargs):
    del starts, group_sizes
    frame = _df(x)
    names = list(frame.columns) if cols is None else list(cols)
    return Vec(finteraction(*[frame.columns[name] for name in names], **kwargs).values)


def _order_index(columns, na_last=True, decreasing=False):
    cols = [np.asarray(column) for column in columns]
    n = len(cols[0])
    dec = list(decreasing) if isinstance(decreasing, (list, tuple, np.ndarray)) else [bool(decreasing)] * len(cols)
    keys = []
    for i in range(n):
        parts = []
        for column, down in zip(cols, dec):
            value = column[i]
            missing = value is None or (isinstance(value, (float, np.floating)) and math.isnan(float(value))) or (isinstance(value, str) and value == "NA")
            if na_last is None:
                rank = 0
            elif na_last:
                rank = 1 if missing else 0
            else:
                rank = 0 if missing else 1
            token = "" if missing else _cell(value)
            if down and not missing:
                token = "".join(chr(0x10FFFF - ord(ch)) for ch in token) if isinstance(value, str) else -float(value)
            parts.append((rank, token if isinstance(token, str) else float(token) if not isinstance(token, str) else token))
        keys.append((parts, i))
    ordered = sorted(range(n) if na_last is not None else [i for i in range(n) if not any(_isna(cols[c][i]) for c in range(len(cols)))], key=lambda i: keys[i][0])
    return [i + 1 for i in ordered]


def _isna(value):
    if value is None:
        return True
    if isinstance(value, (float, np.floating)) and math.isnan(float(value)):
        return True
    return False


def radixorder(*cols, na_last=True, decreasing=False, starts=False, group_sizes=False, sort=True):
    del sort
    order = _order_index(cols, na_last=na_last, decreasing=decreasing)
    if not starts and not group_sizes:
        return Vec(np.array(order, dtype=np.float64))
    return {"order": order, "starts": starts, "group_sizes": group_sizes}


def radixorderv(X, na_last=True, decreasing=False, **kwargs):
    if _is_df(X):
        frame = _df(X)
        return radixorder(*frame.columns.values(), na_last=na_last, decreasing=decreasing, **kwargs)
    return radixorder(X, na_last=na_last, decreasing=decreasing, **kwargs)


def funique_default(x, sort=False, method="auto"):
    del method
    values = _raw_values(x)
    seen = []
    found = set()
    for value in values:
        key = "NA" if value is None or _missing(value) else _cell(value)
        if key not in found:
            found.add(key)
            seen.append(value)
    if sort:
        present = [value for value in seen if not (value is None or _missing(value))]
        missing = [value for value in seen if value is None or _missing(value)]
        present.sort(key=_level_key)
        seen = present + missing
    if seen and all(isinstance(v, (int, float, np.integer, np.floating)) or v is None for v in seen):
        return Vec([np.nan if v is None or _missing(v) else float(v) for v in seen])
    return seen


def funique_data_frame(x, cols=None, sort=False, method="auto"):
    frame = _df(x)
    names = list(frame.columns) if cols is None else list(cols)
    rows = []
    seen = set()
    keep = []
    for i in range(frame.nrow):
        key = tuple(_cell(frame.columns[name][i]) for name in names)
        if key not in seen:
            seen.add(key)
            rows.append(key)
            keep.append(i)
    if sort:
        order = sorted(range(len(keep)), key=lambda i: rows[i])
        keep = [keep[i] for i in order]
    return DF({name: frame.columns[name][keep] for name in frame.columns})


def funique(x, sort=False, method="auto", cols=None):
    if _is_df(x):
        return funique_data_frame(x, cols=cols, sort=sort, method=method)
    return funique_default(x, sort=sort, method=method)


def fduplicated(x, cols=None):
    if _is_df(x):
        frame = _df(x)
        names = list(frame.columns) if cols is None else list(cols)
        seen = set()
        out = []
        for i in range(frame.nrow):
            key = tuple(_cell(frame.columns[name][i]) for name in names)
            out.append(key in seen)
            seen.add(key)
        return np.array(out, dtype=bool)
    seen = set()
    out = []
    for value in _raw_values(x):
        key = "NA" if value is None or _missing(value) else _cell(value)
        out.append(key in seen)
        seen.add(key)
    return np.array(out, dtype=bool)


def any_duplicated(x, cols=None):
    return bool(np.any(fduplicated(x, cols=cols)))


def fnunique(x):
    uniq = funique_default(x)
    if isinstance(uniq, Vec):
        return float(uniq.values.size)
    return float(len(list(uniq)))


def fdroplevels_factor(x, levels=None):
    del levels
    if isinstance(x, Vec) and x.names:
        used = []
        for value in x.values:
            if math.isnan(value):
                continue
            name = x.names[int(value) - 1]
            if name not in used:
                used.append(name)
        remap = {x.names.index(name) + 1: i + 1 for i, name in enumerate(used)}
        codes = [np.nan if math.isnan(v) else remap[int(v)] for v in x.values]
        return Vec(codes, used)
    return qF(x, drop=True)


def fdroplevels_data_frame(x):
    frame = _df(x)
    return DF({name: column for name, column in frame.columns.items()})


def fdroplevels(x, **kwargs):
    if _is_df(x):
        return fdroplevels_data_frame(x)
    return fdroplevels_factor(x, **kwargs)


def as_factor_GRP(x, ordered=False, na_exclude=True):
    del ordered
    obj = x if isinstance(x, Group) else GRP(x)
    if na_exclude:
        levels = [level for level in obj.levels if level != "NA"]
    else:
        levels = list(obj.levels)
    return Vec(obj.codes.astype(np.float64), levels)


def as_factor_qG(x, ordered=False, na_exclude=True):
    del ordered, na_exclude
    if isinstance(x, Vec):
        return x
    return qF(x)


def as_numeric_factor(x):
    if isinstance(x, Vec) and x.names:
        out = []
        for name in x.names:
            try:
                out.append(float(name))
            except ValueError:
                return Vec(np.full(x.values.shape, np.nan))
        return Vec([np.nan if math.isnan(v) else out[int(v) - 1] for v in x.values])
    try:
        return Vec([float(v) for v in x])
    except (TypeError, ValueError):
        return Vec(np.full(len(list(x)), np.nan))


def as_integer_factor(x):
    """Integer form of the level labels, the same coercion as ``as.integer(levels)[x]``."""
    if isinstance(x, Vec) and x.names:
        try:
            levels = [int(float(name)) for name in x.names]
        except ValueError:
            return Vec(np.full(x.values.shape, np.nan))
        return Vec([np.nan if math.isnan(value) else levels[int(value) - 1] for value in x.values])
    codes, levels = q_levels(x, na_exclude=True, sort=True)
    try:
        mapped = [int(float(level)) for level in levels]
    except (TypeError, ValueError):
        return Vec(np.full(len(codes), np.nan))
    return Vec([np.nan if code is None else mapped[code - 1] for code in codes])


def as_character_factor(x):
    if isinstance(x, Vec) and x.names:
        return [None if math.isnan(v) else x.names[int(v) - 1] for v in x.values]
    return [None if _missing(v) else str(v) for v in x]


def fnlevels(x):
    if isinstance(x, Vec) and x.names:
        return float(len(x.names))
    if isinstance(x, Group):
        return float(x.n)
    _codes, levels = q_levels(x, na_exclude=True, sort=True)
    return float(len(levels))


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _same(a, b):
    if _isna(a) and _isna(b):
        return True
    return _cell(a) == _cell(b)


def whichv(x, value, invert=False):
    hits = [i + 1 for i, item in enumerate(_raw_values(x)) if _same(item, value) != invert and (_same(item, value) or invert)]
    if invert:
        hits = [i + 1 for i, item in enumerate(_raw_values(x)) if not _same(item, value)]
    return Vec(np.array(hits, dtype=np.float64))


def whichNA(x, invert=False):
    return whichv(x, None, invert=invert)


def op_eq(x, value):
    return whichv(x, value, invert=False)


def op_ne(x, value):
    return whichv(x, value, invert=True)


def allv(x, value):
    return all(_same(item, value) for item in _raw_values(x))


def anyv(x, value):
    return any(_same(item, value) for item in _raw_values(x))


def allNA(x):
    values = _raw_values(x)
    return bool(values) and all(_isna(item) or item is None for item in values)


def alloc(value, n, simplify=True):
    del simplify
    if isinstance(value, str):
        return [value] * int(n)
    return Vec(np.full(int(n), value, dtype=np.float64))


def frange(x, na_rm=None, finite=False):
    if na_rm is None:
        na_rm = _opt("na.rm")
    values = _vector(x)
    if finite:
        values = values[np.isfinite(values)]
    elif na_rm:
        values = values[np.isfinite(values)]
    elif np.isnan(values).any():
        return Vec([np.nan, np.nan])
    if values.size == 0:
        return Vec([np.inf, -np.inf])
    return Vec([float(np.min(values)), float(np.max(values))])


def dot_range(x, na_rm=True, finite=False):
    return frange(x, na_rm=na_rm, finite=finite)


def fquantile(x, probs=None, w=None, o=None, na_rm=None, type=7, names=True, check_o=True):
    del o, check_o
    if na_rm is None:
        na_rm = _opt("na.rm")
    if probs is None:
        probs = [0, 0.25, 0.5, 0.75, 1]
    if int(type) < 4:
        raise CollapseError(f"fquantile only supports continuous quantile types 4-9. You requested type: {type}")
    ties = {4: "q4", 5: "q5", 6: "q6", 7: "q7", 8: "q8", 9: "q9"}[int(type)]
    values = _vector(x)
    out = [_nth(values, None if w is None else _vector(w), na_rm, float(p), ties) for p in probs]
    labels = [f"{float(p) * 100:g}%" for p in probs] if names else None
    return Vec(out, labels)


def dot_quantile(x, probs=None, w=None, o=None, na_rm=True, type=7, names=False, check_o=False):
    return fquantile(x, probs=probs, w=w, o=o, na_rm=na_rm, type=type, names=names, check_o=check_o)


def fdist(x, v=None, method="euclidean", nthreads=1):
    del nthreads
    matrix = np.asarray(x if not _is_df(x) else np.column_stack([_numeric_col(c) for c in _columns(x).values()]), dtype=np.float64)
    if v is None:
        if matrix.ndim != 2 or matrix.shape[0] < 2:
            raise CollapseError("if v is left empty, x needs to be a matrix with at least 2 rows")
        rows = matrix
    else:
        rows = np.vstack([matrix.reshape(1, -1), np.asarray(v, dtype=np.float64).reshape(1, -1)])
    def dist(a, b):
        d = a - b
        if method == "euclidean":
            return float(np.sqrt(np.nansum(d * d)))
        if method == "manhattan":
            return float(np.nansum(np.abs(d)))
        if method == "maximum":
            return float(np.nanmax(np.abs(d)))
        raise CollapseError(f"unknown distance: {method}")
    out = []
    for i in range(1, rows.shape[0]):
        for j in range(i):
            out.append(dist(rows[i], rows[j]))
    return Vec(out)


def vgcd(x):
    return float(_gcd_list(_vector(x)))


def seq_row(x):
    return Vec(np.arange(1, _nrow(x) + 1, dtype=np.float64))


def seq_col(x):
    if isinstance(x, Mat) or (isinstance(x, np.ndarray) and np.asarray(x).ndim == 2):
        n = np.asarray(x.values if isinstance(x, Mat) else x).shape[1]
    elif _is_df(x):
        n = len(_columns(x))
    else:
        n = 1
    return Vec(np.arange(1, n + 1, dtype=np.float64))


def fnrow(x):
    if isinstance(x, Vec):
        return float(x.values.size)
    if not _is_df(x) and not isinstance(x, (Mat, np.ndarray)):
        return float(len(_raw_values(x)))
    return float(_nrow(x))


def fncol(x):
    if _is_df(x):
        return float(len(_columns(x)))
    if isinstance(x, Mat):
        return float(x.values.shape[1])
    array = np.asarray(x)
    if array.ndim == 2:
        return float(array.shape[1])
    return 1.0


def fdim(x):
    return Vec([fnrow(x), fncol(x)])


def dot_c(*names):
    return [str(name) for name in names]


def cinv(x):
    matrix = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    chol = np.linalg.cholesky(matrix)
    eye = np.eye(matrix.shape[0])
    inv = np.linalg.solve(chol.T, np.linalg.solve(chol, eye))
    return Mat(inv)


def na_rm(x):
    if _is_df(x):
        frame = _df(x)
        keep = []
        for i in range(frame.nrow):
            if not any(_isna(frame.columns[name][i]) for name in frame.columns):
                keep.append(i)
        return DF({name: column[keep] for name, column in frame.columns.items()})
    values = _raw_values(x)
    kept = [np.nan if v is None else v for v in values if not (v is None or _isna(v))]
    try:
        return Vec(np.array(kept, dtype=np.float64))
    except (TypeError, ValueError):
        return kept


def na_locf(x, set=False):
    values = _vector(x).copy()
    last = np.nan
    for i, value in enumerate(values):
        if math.isnan(value):
            values[i] = last
        else:
            last = value
    if set and isinstance(x, np.ndarray):
        x[...] = values
    return Vec(values)


def na_focb(x, set=False):
    values = _vector(x).copy()
    nxt = np.nan
    for i in range(values.size - 1, -1, -1):
        if math.isnan(values[i]):
            values[i] = nxt
        else:
            nxt = values[i]
    if set and isinstance(x, np.ndarray):
        x[...] = values
    return Vec(values)


def na_omit(X, cols=None, na_attr=False, prop=0):
    del na_attr, prop
    if not _is_df(X) and not (isinstance(X, np.ndarray) and np.asarray(X).ndim == 2):
        return na_rm(X)
    frame = _df(X) if _is_df(X) else DF({f"V{i+1}": X[:, i] for i in range(X.shape[1])})
    names = list(frame.columns) if cols is None else list(cols)
    keep = []
    for i in range(frame.nrow):
        if not any(_isna(frame.columns[name][i]) for name in names):
            keep.append(i)
    return DF({name: column[keep] for name, column in frame.columns.items()})


def na_insert(X, prop=0.1, value=None, set=False):
    # collapse draws the positions with sample.int. These are the first floor(n * prop) rows.
    count = int(math.floor(prop * (fnrow(X) if _is_df(X) else len(_raw_values(X)))))
    if _is_df(X):
        frame = _df(X).copy()
        for column in frame.columns.values():
            if _is_numeric_col(column):
                column[:count] = np.nan if value is None else value
        return frame
    values = _vector(X).copy()
    values[:count] = np.nan if value is None else value
    if set and isinstance(x_is_array := isinstance(X, np.ndarray), bool) and x_is_array:
        X[...] = values
    return Vec(values)


def replace_na(x, value=0):
    if _is_df(x):
        frame = _df(x).copy()
        for name, column in frame.columns.items():
            if _is_numeric_col(column):
                column = column.astype(np.float64, copy=True)
                column[np.isnan(column)] = value
                frame.columns[name] = column
        return frame
    values = _vector(x).copy()
    values[np.isnan(values)] = value
    return Vec(values)


def replace_NA(x, value=0):
    return replace_na(x, value)


def replace_inf(x, value=None):
    values = _vector(x).copy()
    values[~np.isfinite(values)] = np.nan if value is None else value
    # finite NaN stays; only inf
    original = _vector(x)
    values = original.copy()
    values[np.isinf(values)] = np.nan if value is None else value
    return Vec(values)


def replace_Inf(x, value=None):
    return replace_inf(x, value)


def replace_outliers(X, limits, value=None, single_limit=None):
    lo, hi = (float(limits[0]), float(limits[1])) if single_limit is None else (None, None)
    if single_limit == "SDs":
        stats = qsu(X)
        center, scale = float(stats.values[1]), float(stats.values[2])
        lo, hi = center - float(limits) * scale, center + float(limits) * scale
    values = _vector(X).copy()
    fill = np.nan if value is None else value
    values[(values < lo) | (values > hi)] = fill
    return Vec(values)


def recode_num(x, **repl):
    values = _vector(x).copy()
    for key, value in repl.items():
        values[values == float(key)] = float(value)
    return Vec(values)


def recode_char(x, **repl):
    return [repl.get(str(v), v) for v in x]


def pad(X, i, value=None, method="auto"):
    values = _vector(X)
    index = np.asarray(i)
    fill = np.nan if value is None else value
    if index.dtype == bool or str(method) == "vpos":
        raise CollapseError("logical pad is not in this check")
    if index.size == values.size and float(index[0]) > 0 and method != "vpos":
        n = int(np.max(index))
        out = np.full(n, fill, dtype=np.float64)
        for dest, src in zip(index, values):
            out[int(dest) - 1] = src
        return Vec(out)
    return Vec(values)


def copyv(X, v, R, invert=False, vind1=False, xlist=False):
    del xlist, vind1
    values = _vector(X).copy()
    hit = np.isclose(values, float(v)) if not invert else ~np.isclose(values, float(v))
    values[hit] = float(R)
    return Vec(values)


def setv(X, v, R, invert=False, vind1=False, xlist=False):
    updated = copyv(X, v, R, invert=invert, vind1=vind1, xlist=xlist)
    if isinstance(X, np.ndarray):
        X[...] = updated.values
        return X
    return updated


def setop(X, op, V, rowwise=False):
    del rowwise
    code = {"+": "+", "-": "-", "*": "*", "/": "/"}[op]
    updated = TRA(X, V, code)
    if isinstance(X, np.ndarray):
        X[...] = updated.values
        return X
    return updated


def op_addeq(X, V):
    return setop(X, "+", V)


def op_subeq(X, V):
    return setop(X, "-", V)


def op_muleq(X, V):
    return setop(X, "*", V)


def op_diveq(X, V):
    return setop(X, "/", V)


def massign(nam, values, envir=None):
    if envir is None:
        raise CollapseError("massign needs an explicit envir dict")
    if len(nam) != len(values):
        raise CollapseError("length(nam) must equal length(values)")
    for name, value in zip(nam, values):
        envir[str(name)] = value
    return None


def op_massign(nam, values, envir=None):
    return massign(nam, values, envir)


def missing_cases(X, cols=None, prop=0, count=False):
    del prop
    if _is_df(X) or isinstance(X, dict):
        frame = _df(X)
        names = list(frame.columns) if cols is None else list(cols)
        out = []
        for i in range(frame.nrow):
            n = sum(_isna(frame.columns[name][i]) for name in names)
            out.append(float(n) if count else bool(n))
        return np.array(out, dtype=np.float64 if count else bool)
    values = _raw_values(X)
    if count:
        return Vec([1.0 if _isna(v) or v is None else 0.0 for v in values])
    return np.array([_isna(v) or v is None for v in values], dtype=bool)


def all_identical(*args):
    items = list(args[0]) if len(args) == 1 and isinstance(args[0], (list, tuple)) else list(args)
    return all(items[0] == item for item in items[1:])


def all_obj_equal(*args):
    items = list(args[0]) if len(args) == 1 and isinstance(args[0], (list, tuple)) else list(args)
    tol = math.sqrt(np.finfo(float).eps)
    def close(a, b):
        try:
            return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
        except (TypeError, ValueError):
            return a == b
    return all(close(items[0], item) for item in items[1:])


def all_funs(expr):
    """Function names in a call, in the order collapse walks the expression."""
    text = str(expr)
    found = []

    def parse(src):
        src = src.strip()
        if not src:
            return
        # outermost call name(...)
        match = re.match(r"([A-Za-z.][\w.]*)\((.*)\)\s*$", src)
        if match and _balanced(match.group(2)):
            found.append(match.group(1))
            args = _split_args(match.group(2))
            for arg in args:
                parse(arg)
            return
        for op in ("+", "-", "*", "/", "^"):
            parts = _split_op(src, op)
            if parts is not None:
                found.append(op)
                parse(parts[0])
                parse(parts[1])
                return

    def _balanced(body):
        depth = 0
        for ch in body:
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
                if depth < 0:
                    return False
        return depth == 0

    def _split_args(body):
        parts, depth, start = [], 0, 0
        for i, ch in enumerate(body):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "," and depth == 0:
                parts.append(body[start:i])
                start = i + 1
        parts.append(body[start:])
        return [part for part in parts if part.strip()]

    def _split_op(src, op):
        depth = 0
        for i, ch in enumerate(src):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == op and depth == 0 and i not in (0, len(src) - 1):
                return src[:i], src[i + 1 :]
        return None

    parse(text)
    return found


def vlabels(X, attrn="label", use_names=True):
    del attrn, use_names
    if _is_df(X):
        frame = _df(X)
        stored = frame.labels if isinstance(frame, DF) else {}
        return ["NA" if stored.get(name) is None else stored[name] for name in frame.columns]
    return getattr(X, "label", "NA")


def setLabels(X, value=None, attrn="label", cols=None):
    del attrn
    if _is_df(X):
        frame = _df(X)
        names = list(frame.columns) if cols is None else [list(frame.columns)[i] if isinstance(i, int) else i for i in cols]
        values = list(value) if value is not None else [None] * len(names)
        if not isinstance(frame, DF):
            frame = DF(frame.columns)
        for name, label in zip(names, values):
            frame.labels[name] = label
        return frame
    return X


def vlabels_assign(X, value, attrn="label"):
    return setLabels(X, value, attrn)


def vclasses(X, use_names=True):
    del use_names
    if not _is_df(X):
        return _class_name(X)
    return [_class_name(column) for column in _columns(X).values()]


def _class_name(column):
    if isinstance(column, np.ndarray) and column.dtype.kind in "iuf":
        return "numeric"
    if isinstance(column, np.ndarray) and column.dtype == bool:
        return "logical"
    return "character"


def vtypes(X, use_names=True):
    del use_names
    if not _is_df(X):
        return _type_name(X)
    return [_type_name(column) for column in _columns(X).values()]


def _type_name(column):
    if isinstance(column, np.ndarray) and column.dtype.kind == "i":
        return "integer"
    if isinstance(column, np.ndarray) and column.dtype.kind == "f":
        return "double"
    if isinstance(column, np.ndarray) and column.dtype == bool:
        return "logical"
    return "character"


def vlengths(X, use_names=True):
    del use_names
    if isinstance(X, dict) and not isinstance(X, DF):
        return Vec([float(len(np.atleast_1d(v))) for v in X.values()])
    if _is_df(X):
        return Vec([float(len(column)) for column in _columns(X).values()])
    return float(len(_raw_values(X)))


def namlab(X, class_=False, attrn="label", N=False, Ndistinct=False):
    frame = _df(X)
    columns = {"Variable": np.array(list(frame.columns), dtype=object)}
    if class_:
        columns["Class"] = np.array(vclasses(frame), dtype=object)
    if N:
        columns["N"] = np.array([fmode_count(column) for column in frame.columns.values()], dtype=np.float64)
    del Ndistinct, attrn
    columns["Label"] = np.array(vlabels(frame), dtype=object)
    return DF(columns)


def fmode_count(column):
    numeric = _numeric_col(column)
    if numeric is None:
        return float(sum(not _isna(v) for v in column))
    return float(np.sum(np.isfinite(numeric)))


def add_stub(X, stub, pre=True, cols=None):
    if not isinstance(stub, str):
        return X
    frame = _df(X)
    names = list(frame.columns)
    chosen = set(names if cols is None else cols)
    renamed = {}
    for name in names:
        if name in chosen:
            renamed[f"{stub}{name}" if pre else f"{name}{stub}"] = frame.columns[name]
        else:
            renamed[name] = frame.columns[name]
    return DF(renamed, frame.rows)


def rm_stub(X, stub, pre=True, regex=False, cols=None):
    if not isinstance(stub, str):
        return X
    frame = _df(X)
    renamed = {}
    for name, column in frame.columns.items():
        new = name
        if regex:
            new = re.sub(stub, "", name)
        elif pre and name.startswith(stub):
            new = name[len(stub):]
        elif not pre and name.endswith(stub):
            new = name[: -len(stub)]
        renamed[new] = column
    return DF(renamed, frame.rows)


def setRownames(object, nm=None):
    frame = _df(object)
    frame.rows = [str(v) for v in (nm if nm is not None else range(1, frame.nrow + 1))]
    return frame


def setColnames(object, nm):
    frame = _df(object)
    return DF(dict(zip(nm, frame.columns.values())), frame.rows)


def setDimnames(object, dn, which=None):
    if isinstance(object, Mat):
        if which is None:
            object.rows, object.columns = dn[0], dn[1]
        elif which == 1:
            object.rows = list(dn)
        else:
            object.columns = list(dn)
        return object
    return object


def unattrib(object):
    if isinstance(object, (Vec, Mat, DF)):
        return object
    return object


def setAttrib(object, a):
    return object


def setattrib(object, a):
    del a
    return object


def copyAttrib(to, from_):
    del from_
    return to


def copyMostAttrib(to, from_):
    del from_
    return to


def is_categorical(x):
    return not _is_numeric_col(np.asarray(x, dtype=object) if not isinstance(x, np.ndarray) else x) if not isinstance(x, str) else True


def is_date(x):
    import datetime
    return isinstance(x, (datetime.date, datetime.datetime, np.datetime64))


def is_GRP(x):
    return isinstance(x, Group)


def is_qG(x):
    return isinstance(x, Vec) and hasattr(x, "n_groups")


def is_unlistable(l, DF_as_list=False):
    del DF_as_list
    return not isinstance(l, (list, tuple, dict)) or all(not isinstance(v, (list, tuple, dict)) for v in (l.values() if isinstance(l, dict) else l))


def ldepth(l, DF_as_list=False):
    del DF_as_list
    if not isinstance(l, (list, tuple, dict)):
        return 0
    kids = list(l.values()) if isinstance(l, dict) else list(l)
    if not kids:
        return 1
    return 1 + max(ldepth(kid) for kid in kids)


def _walk_names(l):
    if isinstance(l, dict):
        names = list(l)
        for value in l.values():
            if isinstance(value, (dict, list, tuple)):
                names.extend(_walk_names(value))
        return names
    if isinstance(l, (list, tuple)):
        names = []
        for value in l:
            if isinstance(value, (dict, list, tuple)):
                names.extend(_walk_names(value))
        return names
    return []


def has_elem(l, elem, recursive=True, DF_as_list=False, regex=False):
    del DF_as_list
    if callable(elem):
        def walk(node):
            if elem(node):
                return True
            if isinstance(node, dict):
                return any(walk(v) for v in node.values())
            if isinstance(node, (list, tuple)):
                return any(walk(v) for v in node)
            return False
        return walk(l) if recursive else any(elem(v) for v in (l.values() if isinstance(l, dict) else l))
    names = _walk_names(l) if recursive else list(l)
    if regex:
        return any(re.search(elem, name) for name in names)
    return any(name in elem if isinstance(elem, (list, tuple, set)) else name == elem for name in names)


def get_elem(l, elem, recursive=True, DF_as_list=False, regex=False):
    del DF_as_list, recursive
    if isinstance(l, dict) and elem in l and not regex:
        return l[elem]
    found = []
    def walk(node):
        if isinstance(node, dict):
            for name, value in node.items():
                if (re.search(elem, name) if regex else name == elem):
                    found.append(value)
                elif isinstance(value, (dict, list)):
                    walk(value)
    walk(l)
    return found[0] if len(found) == 1 else found


def list_elem(l, return_="sublist", keep_class=False):
    del keep_class
    items = [(name, value) for name, value in l.items()] if isinstance(l, dict) else list(enumerate(l))
    chosen = [(name, value) for name, value in items if isinstance(value, (list, tuple, dict))]
    if return_ == "names":
        return [name for name, _ in chosen]
    if return_ == "indices":
        return [i + 1 for i, (name, _) in enumerate(items) if isinstance(name, int) or (isinstance(l, dict) and isinstance(l[name], (list, tuple, dict)))]
    return dict(chosen) if isinstance(l, dict) else [value for _, value in chosen]


def atomic_elem(l, return_="sublist", keep_class=False):
    del keep_class
    items = list(l.items()) if isinstance(l, dict) else list(enumerate(l))
    chosen = [(name, value) for name, value in items if not isinstance(value, (list, tuple, dict))]
    if return_ == "names":
        return [name for name, _ in chosen]
    return dict(chosen) if isinstance(l, dict) else [value for _, value in chosen]


def list_elem_assign(l, value):
    keys = [name for name, item in (l.items() if isinstance(l, dict) else enumerate(l)) if isinstance(item, (list, tuple, dict))]
    vals = list(value) if isinstance(value, (list, tuple)) else [value]
    for key, item in zip(keys, vals):
        l[key] = item
    return l


def atomic_elem_assign(l, value):
    keys = [name for name, item in (l.items() if isinstance(l, dict) else enumerate(l)) if not isinstance(item, (list, tuple, dict))]
    vals = list(value) if isinstance(value, (list, tuple)) else [value]
    for key, item in zip(keys, vals):
        l[key] = item
    return l


def _leaves(node):
    if isinstance(node, dict):
        found = []
        for value in node.values():
            found.extend(_leaves(value))
        return found
    if isinstance(node, (list, tuple)):
        if any(isinstance(value, (list, tuple, dict)) for value in node):
            found = []
            for value in node:
                found.extend(_leaves(value))
            return found
        return list(node)
    return [node]


def reg_elem(l, recursive=True, keep_tree=False, keep_class=False):
    del recursive, keep_tree, keep_class
    return _leaves(l)


def irreg_elem(l, recursive=True, keep_tree=False, keep_class=False):
    del recursive, keep_tree, keep_class
    found = []

    def walk(node):
        if isinstance(node, dict):
            lengths = [len(value) for value in node.values() if isinstance(value, (list, tuple)) and value and not isinstance(value[0], (list, tuple, dict))]
            if lengths and len(set(lengths)) > 1:
                found.append(node)
            for value in node.values():
                if isinstance(value, (list, tuple, dict)):
                    walk(value)

    walk(l)
    return found


def rapply2d(l, FUN, classes=None):
    del classes
    if isinstance(l, dict):
        return {name: rapply2d(value, FUN) if isinstance(value, (dict, list)) else FUN(value) for name, value in l.items()}
    if isinstance(l, list):
        return [rapply2d(value, FUN) if isinstance(value, (dict, list)) else FUN(value) for value in l]
    return FUN(l)


def t_list(l):
    if isinstance(l, dict):
        keys = list(l)
        n = len(next(iter(l.values())))
        return [{key: l[key][i] for key in keys} for i in range(n)]
    cols = list(zip(*l))
    return cols


def unlist2d(x, idcols=None, recursive=True, id_name="id"):
    del recursive, id_name
    if isinstance(x, dict):
        return x
    rows = [dict(item) for item in x if isinstance(item, dict)]
    if not rows:
        return x
    names = list(rows[0])
    out = {name: [row.get(name) for row in rows] for name in names}
    if idcols not in (None, False):
        label = ".id" if idcols is True else str(idcols)
        out = {label: list(range(1, len(rows) + 1)), **out}
    return DF(out)


def gsplit(x, g):
    codes, levels = factor(g)
    buckets = {level: [] for level in levels}
    values = _raw_values(x)
    for value, code in zip(values, codes):
        buckets[levels[int(code)]].append(value)
    return buckets


def greorder(x, g, **kwargs):
    """Put a group-sorted vector back in the original row order."""
    del kwargs
    order_obj = radixorder(g)
    order = np.asarray(order_obj.values if isinstance(order_obj, Vec) else order_obj, dtype=int) - 1
    inverse = np.empty(order.size, dtype=int)
    inverse[order] = np.arange(order.size)
    values = _raw_values(x)
    return [values[i] for i in inverse]


def rsplit_default(x, g=None):
    if g is None:
        return list(_raw_values(x))
    return gsplit(x, g)


def rsplit_matrix(x, g=None):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    rows = [list(values[i]) for i in range(values.shape[0])]
    if g is None:
        return rows
    return gsplit(rows, g)


def rsplit_data_frame(x, g=None):
    frame = _df(x)
    rows = [{name: frame.columns[name][i] for name in frame.columns} for i in range(frame.nrow)]
    if g is None:
        return rows
    return gsplit(rows, g)


def rsplit(x, g=None):
    if _is_df(x):
        return rsplit_data_frame(x, g)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return rsplit_matrix(x, g)
    return rsplit_default(x, g)


def mctl(X, names=False, return_="list"):
    values = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
    cols = [values[:, j] for j in range(values.shape[1])]
    labels = [f"V{j+1}" for j in range(values.shape[1])]
    if return_ == "data.frame":
        return DF(dict(zip(labels, cols)))
    if names:
        return dict(zip(labels, cols))
    return cols


def mrtl(X, names=False, return_="list"):
    values = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
    rows = [values[i] for i in range(values.shape[0])]
    if return_ == "data.frame":
        return DF({f"V{i+1}": row for i, row in enumerate(rows)})
    if names:
        return {f"V{i+1}": row for i, row in enumerate(rows)}
    return rows


def vec(X):
    if _is_df(X):
        parts = [_numeric_col(column) for column in _columns(X).values()]
        return Vec(np.concatenate(parts))
    if isinstance(X, (Mat, Vec)):
        return Vec(np.ravel(X.values, order="F"))
    return Vec(_vector(X))


def ss(x, i, j=None):
    index = np.asarray(i, dtype=int) - 1
    if _is_df(x):
        frame = _df(x)
        names = list(frame.columns) if j is None else [list(frame.columns)[k - 1] if isinstance(k, (int, np.integer)) else k for k in j]
        return DF({name: frame.columns[name][index] for name in names})
    if isinstance(x, np.ndarray) and x.ndim == 2:
        return Mat(x[index])
    return Vec(_vector(x)[index])


def fmatch(x, table, nomatch=None, count=False, overid=1):
    del overid
    pool = {}
    for i, value in enumerate(_raw_values(table)):
        key = "NA" if value is None or _isna(value) else _cell(value)
        pool.setdefault(key, []).append(i + 1)
    out = []
    for value in _raw_values(x):
        key = "NA" if value is None or _isna(value) else _cell(value)
        hits = pool.get(key, [])
        if count:
            out.append(float(len(hits)))
        elif hits:
            out.append(float(hits[0]))
        else:
            out.append(np.nan if nomatch is None else float(nomatch))
    return Vec(out)


def ckmatch(x, table, e="Unknown columns:"):
    matched = fmatch(x, table)
    if np.isnan(matched.values).any():
        missing = [str(a) for a, b in zip(x, matched.values) if math.isnan(b)]
        raise CollapseError(f"{e} {', '.join(missing)}")
    return matched


def not_in(x, table):
    matched = fmatch(x, table)
    return np.isnan(matched.values)


def iin(x, table):
    matched = fmatch(x, table)
    return whichNA(matched.values, invert=True)


def not_iin(x, table):
    matched = fmatch(x, table)
    return whichNA(matched.values, invert=False)


def dapply(X, FUN, **kwargs):
    if _is_df(X):
        return DF({name: _call_fun(FUN, column, **kwargs) for name, column in _columns(X).items()})
    if isinstance(X, (Mat, np.ndarray)) and np.asarray(getattr(X, "values", X)).ndim == 2:
        values = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
        cols = [_call_fun(FUN, values[:, j], **kwargs) for j in range(values.shape[1])]
        return Mat(np.column_stack([np.asarray(c, dtype=np.float64).reshape(-1) for c in cols]))
    return _call_fun(FUN, X, **kwargs)


def _call_fun(fun, *args, **kwargs):
    if isinstance(fun, str):
        fun = globals()[fun]
    result = fun(*args, **kwargs)
    if isinstance(result, Vec):
        return result.values
    return result


# ---------------------------------------------------------------------------
# statistics that were still open
# ---------------------------------------------------------------------------


def _mode_one(values, weights, na_rm, ties):
    pairs = []
    for i, value in enumerate(values):
        if value is None or _isna(value):
            if na_rm:
                continue
        weight = 1.0 if weights is None else float(weights[i])
        if weights is not None and math.isnan(weight):
            continue
        pairs.append((value, weight, i))
    if not pairs:
        return np.nan
    scores = {}
    order = []
    for value, weight, _i in pairs:
        key = "NA" if value is None or _isna(value) else _cell(value)
        if key not in scores:
            scores[key] = [0.0, value, _i]
            order.append(key)
        scores[key][0] += weight
    best_key = order[0]
    best = scores[best_key]
    for key in order[1:]:
        score, value, idx = scores[key]
        if score > best[0] + 1e-12:
            best_key, best = key, scores[key]
        elif abs(score - best[0]) <= 1e-12:
            if ties == "last":
                best_key, best = key, scores[key]
            elif ties == "min" and _level_key(value) < _level_key(best[1]):
                best_key, best = key, scores[key]
            elif ties == "max" and _level_key(value) > _level_key(best[1]):
                best_key, best = key, scores[key]
    chosen = best[1]
    if chosen is None or _isna(chosen):
        return np.nan
    try:
        return float(chosen)
    except (TypeError, ValueError):
        return chosen


def fmode_default(x, g=None, w=None, TRA=None, na_rm=None, use_g_names=True, ties="first", nthreads=1):
    del nthreads
    if na_rm is None:
        na_rm = _opt("na.rm")
    values = _raw_values(x)
    weights = None if w is None else _vector(w)
    if g is None:
        result = _mode_one(values, weights, na_rm, ties)
        out = Vec([result] if isinstance(result, float) else [np.nan])
        if not isinstance(result, float):
            out = result
        else:
            out = Vec([result])
    else:
        codes, levels = factor(g)
        grouped = []
        for level_i in range(len(levels)):
            pick = [values[i] for i in range(len(values)) if int(codes[i]) == level_i]
            wpick = None if weights is None else weights[codes == level_i]
            grouped.append(_mode_one(pick, wpick, na_rm, ties))
        numeric = []
        for item in grouped:
            try:
                numeric.append(float(item))
            except (TypeError, ValueError):
                numeric.append(np.nan)
        out = Vec(numeric, levels if use_g_names else None)
    if TRA is not None:
        return apply_tra(x, out, TRA, g, "vector")
    return out


def fmode_matrix(x, g=None, w=None, TRA=None, na_rm=None, use_g_names=True, drop=True, ties="first", nthreads=1):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    cols = [fmode_default(values[:, j], g=g, w=w, na_rm=na_rm, use_g_names=use_g_names, ties=ties, nthreads=nthreads) for j in range(values.shape[1])]
    stacked = np.column_stack([col.values for col in cols])
    result = Vec(stacked.ravel()) if drop and g is None else Mat(stacked, rows=cols[0].names, columns=None)
    if TRA is not None:
        return apply_tra(values, result, TRA, g, "matrix")
    return result


def fmode_data_frame(x, g=None, w=None, TRA=None, na_rm=None, use_g_names=True, drop=True, ties="first", nthreads=1):
    columns = {}
    for name, column in _columns(x).items():
        columns[name] = fmode_default(column, g=g, w=w, na_rm=na_rm, use_g_names=use_g_names, ties=ties, nthreads=nthreads).values
    if drop and g is None:
        return Vec(np.concatenate(list(columns.values())), list(columns))
    rows = None
    if g is not None and use_g_names:
        rows = factor(g)[1]
    result = DF(columns, rows=rows)
    if TRA is not None:
        return apply_tra(x, result, TRA, g, "frame")
    return result


def fmode(x, g=None, w=None, TRA=None, na_rm=None, use_g_names=True, drop=True, ties="first", nthreads=1):
    if _is_df(x):
        return fmode_data_frame(x, g, w, TRA, na_rm, use_g_names, drop, ties, nthreads)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return fmode_matrix(x, g, w, TRA, na_rm, use_g_names, drop, ties, nthreads)
    return fmode_default(x, g, w, TRA, na_rm, use_g_names, ties, nthreads)


def _ndistinct_one(values, na_rm):
    seen = set()
    na = False
    for value in values:
        if value is None or _isna(value):
            na = True
            continue
        seen.add(_cell(value))
    return float(len(seen) + (0 if na_rm or not na else 1))


def fndistinct_default(x, g=None, TRA=None, na_rm=None, use_g_names=True, nthreads=1):
    del nthreads
    if na_rm is None:
        na_rm = _opt("na.rm")
    values = _raw_values(x)
    if g is None:
        out = Vec([_ndistinct_one(values, na_rm)])
    else:
        codes, levels = factor(g)
        counts = [_ndistinct_one([values[i] for i in range(len(values)) if int(codes[i]) == k], na_rm) for k in range(len(levels))]
        out = Vec(counts, levels if use_g_names else None)
    if TRA is not None:
        return apply_tra(x, out, TRA, g, "vector")
    return out


def fndistinct_matrix(x, g=None, TRA=None, na_rm=None, use_g_names=True, drop=True, nthreads=1):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    cols = [fndistinct_default(values[:, j], g, None, na_rm, use_g_names, nthreads) for j in range(values.shape[1])]
    stacked = np.column_stack([col.values for col in cols])
    result = Vec(stacked.ravel()) if drop and g is None else Mat(stacked, rows=cols[0].names)
    if TRA is not None:
        return apply_tra(values, result, TRA, g, "matrix")
    return result


def fndistinct_data_frame(x, g=None, TRA=None, na_rm=None, use_g_names=True, drop=True, nthreads=1):
    columns = {name: fndistinct_default(column, g, None, na_rm, use_g_names, nthreads).values for name, column in _columns(x).items()}
    if drop and g is None:
        return Vec(np.concatenate([np.atleast_1d(v) for v in columns.values()]), list(columns))
    rows = factor(g)[1] if g is not None and use_g_names else None
    result = DF(columns, rows=rows)
    if TRA is not None:
        return apply_tra(x, result, TRA, g, "frame")
    return result


def fndistinct(x, g=None, TRA=None, na_rm=None, use_g_names=True, drop=True, nthreads=1):
    if _is_df(x):
        return fndistinct_data_frame(x, g, TRA, na_rm, use_g_names, drop, nthreads)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return fndistinct_matrix(x, g, TRA, na_rm, use_g_names, drop, nthreads)
    return fndistinct_default(x, g, TRA, na_rm, use_g_names, nthreads)


def fNdistinct(x, *args, **kwargs):
    return fndistinct(x, *args, **kwargs)


def fNdistinct_default(x, *args, **kwargs):
    return fndistinct_default(x, *args, **kwargs)


def fNdistinct_matrix(x, *args, **kwargs):
    return fndistinct_matrix(x, *args, **kwargs)


def fNdistinct_data_frame(x, *args, **kwargs):
    return fndistinct_data_frame(x, *args, **kwargs)


def _varying_one(values):
    seen = None
    for value in values:
        if value is None or _isna(value):
            continue
        token = _cell(value)
        if seen is None:
            seen = token
        elif token != seen:
            return True
    return False


def varying_default(x, g=None, any_group=True, use_g_names=True):
    values = _raw_values(x)
    if len(values) < 2 and g is None:
        return False
    if g is None:
        return _varying_one(values)
    codes, levels = factor(g)
    flags = [_varying_one([values[i] for i in range(len(values)) if int(codes[i]) == k]) for k in range(len(levels))]
    if any_group:
        return any(flags)
    return Vec(np.array(flags, dtype=np.float64), levels if use_g_names else None)


def varying_matrix(x, g=None, any_group=True, use_g_names=True, drop=True):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    cols = [varying_default(values[:, j], g, any_group, use_g_names) for j in range(values.shape[1])]
    if any_group or g is None:
        flags = np.array([1.0 if flag else 0.0 for flag in cols])
        return Vec(flags) if drop else Mat(flags.reshape(1, -1))
    stacked = np.column_stack([col.values for col in cols])
    return Mat(stacked, rows=cols[0].names)


def varying_data_frame(x, by=None, cols=None, any_group=True, use_g_names=True, drop=True):
    frame = _df(x)
    names = list(frame.columns) if cols is None else list(cols)
    part = DF({name: frame.columns[name] for name in names})
    if by is None:
        flags = [bool(varying_default(column, None, True, True)) for column in part.columns.values()]
        return np.array(flags, dtype=bool) if drop else DF({name: [flag] for name, flag in zip(part.columns, flags)})
    return varying_matrix(np.column_stack([_numeric_col(c) for c in part.columns.values()]), by, any_group, use_g_names, drop)


def varying(x, g=None, any_group=True, use_g_names=True, drop=True, by=None, cols=None):
    if _is_df(x):
        return varying_data_frame(x, by if by is not None else g, cols, any_group, use_g_names, drop)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return varying_matrix(x, g, any_group, use_g_names, drop)
    return varying_default(x, g, any_group, use_g_names)


def _higher_moments(x):
    values = _vector(x)
    values = values[np.isfinite(values)]
    n = 0.0
    mean = M2 = M3 = M4 = 0.0
    lo, hi = math.inf, -math.inf
    for i in range(values.size - 1, -1, -1):
        value = float(values[i])
        d1 = value - mean
        n += 1
        dn = d1 / n
        mean += dn
        dn2 = dn * dn
        term1 = d1 * dn * (n - 1)
        M4 += term1 * dn2 * (n * n - 3 * n + 3) + 6 * dn2 * M2 - 4 * dn * M3
        M3 += term1 * dn * (n - 2) - 3 * dn * M2
        M2 += term1
        lo = min(lo, value)
        hi = max(hi, value)
    if n < 2 or M2 == 0:
        sd = skew = kurt = np.nan if n < 2 else 0.0
        if n < 2:
            return [n, mean if n else np.nan, np.nan, lo if n else np.nan, hi if n else np.nan, np.nan, np.nan]
    sd = math.sqrt(M2 / (n - 1))
    skew = (math.sqrt(n) * M3) / math.sqrt(M2 ** 3) if M2 else np.nan
    kurt = (n * M4) / (M2 * M2) if M2 else np.nan
    return [n, mean, sd, lo, hi, skew, kurt]


def qsu_default(x, g=None, pid=None, w=None, higher=False, array=True, stable_algo=None):
    del pid, w, array, stable_algo
    if g is None:
        stats = _higher_moments(x)
        take = stats if higher else stats[:5]
        return Vec(take, ["N", "Mean", "SD", "Min", "Max"] + (["Skew", "Kurt"] if higher else []))
    codes, levels = factor(g)
    values = _vector(x)
    rows = []
    for k in range(len(levels)):
        rows.append(_higher_moments(values[codes == k])[: 7 if higher else 5])
    return Mat(np.vstack(rows), rows=levels, columns=["N", "Mean", "SD", "Min", "Max"] + (["Skew", "Kurt"] if higher else []))


def qsu_matrix(x, g=None, pid=None, w=None, higher=False, array=True, stable_algo=None):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    parts = [qsu_default(values[:, j], g, pid, w, higher, array, stable_algo) for j in range(values.shape[1])]
    if isinstance(parts[0], Vec):
        return Mat(np.vstack([p.values for p in parts]), columns=parts[0].names)
    return parts


def qsu_data_frame(x, by=None, pid=None, w=None, cols=None, higher=False, array=True, labels=False, stable_algo=None):
    del pid, w, array, labels, stable_algo
    frame = _df(x)
    names = [name for name in frame.columns if _is_numeric_col(frame.columns[name])] if cols is None else list(cols)
    columns = {name: qsu_default(frame.columns[name], by, higher=higher).values for name in names}
    return DF(columns)


def qsu(x, g=None, pid=None, w=None, higher=False, array=True, stable_algo=None, by=None, cols=None, labels=False):
    if _is_df(x):
        return qsu_data_frame(x, by if by is not None else g, pid, w, cols, higher, array, labels, stable_algo)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return qsu_matrix(x, g, pid, w, higher, array, stable_algo)
    return qsu_default(x, g, pid, w, higher, array, stable_algo)


def print_qsu(x, digits=None):
    del digits
    return str(x)


def descr_default(X, by=None, w=None, cols=None, Ndistinct=True, higher=True, table=True, sort_table="freq", Qprobs=None, Qtype=7):
    del by, w, table, sort_table
    if Qprobs is None:
        Qprobs = [0.01, 0.05, 0.1, 0.25, 0.5, 0.75, 0.9, 0.95, 0.99]
    frame = _df(X) if _is_df(X) else DF({"x": _vector(X)})
    names = list(frame.columns) if cols is None else list(cols)
    out = {}
    for name in names:
        column = frame.columns[name]
        if not _is_numeric_col(column):
            continue
        stats = _higher_moments(column)
        quant = fquantile(column, Qprobs, type=Qtype, names=False).values
        out[name] = {
            "N": stats[0],
            "Mean": stats[1],
            "SD": stats[2],
            "Min": stats[3],
            "Max": stats[4],
            "Skew": stats[5] if higher else None,
            "Kurt": stats[6] if higher else None,
            "Ndist": _ndistinct_one(_raw_values(column), True) if Ndistinct else None,
            "Quant": quant,
        }
    return out


def descr(X, **kwargs):
    return descr_default(X, **kwargs)


def _pairwise(X, fun):
    matrix = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
    if matrix.ndim == 1:
        matrix = matrix.reshape(-1, 1)
    p = matrix.shape[1]
    out = np.empty((p, p), dtype=np.float64)
    counts = np.empty((p, p), dtype=np.float64)
    for i in range(p):
        for j in range(p):
            mask = np.isfinite(matrix[:, i]) & np.isfinite(matrix[:, j])
            counts[i, j] = float(mask.sum())
            if i == j:
                out[i, j] = 1.0 if fun == "cor" else (float(np.var(matrix[mask, i], ddof=1)) if mask.sum() > 1 else np.nan)
            elif mask.sum() < 2:
                out[i, j] = np.nan
            elif fun == "cor":
                out[i, j] = float(np.corrcoef(matrix[mask, i], matrix[mask, j])[0, 1])
            else:
                out[i, j] = float(np.cov(matrix[mask, i], matrix[mask, j], ddof=1)[0, 1])
    return out, counts


def pwcor(X, w=None, N=False, P=False, array=True, use="pairwise.complete.obs"):
    del w, P, array, use
    corr, counts = _pairwise(X if not _is_df(X) else np.column_stack([_numeric_col(c) for c in _columns(X).values()]), "cor")
    if N:
        return {"r": Mat(corr), "N": Mat(counts)}
    return Mat(corr)


def pwcov(X, w=None, N=False, P=False, array=True, use="pairwise.complete.obs"):
    del w, P, array, use
    cov, counts = _pairwise(X if not _is_df(X) else np.column_stack([_numeric_col(c) for c in _columns(X).values()]), "cov")
    if N:
        return {"cov": Mat(cov), "N": Mat(counts)}
    return Mat(cov)


def pwnobs(X, use="pairwise.complete.obs"):
    del use
    _corr, counts = _pairwise(X if not _is_df(X) else np.column_stack([_numeric_col(c) for c in _columns(X).values()]), "cor")
    return Mat(counts)


def print_pwcor(x, digits=None, sig_level=0.05, show="all", spacing=1, return_=False):
    del digits, sig_level, show, spacing, return_
    return str(x)


def print_pwcov(x, digits=None, sig_level=0.05, show="all", spacing=1, return_=False):
    return print_pwcor(x, digits, sig_level, show, spacing, return_)


def _betacf(a, b, x):
    qab = a + b
    qap = a + 1
    qam = a - 1
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d
    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 3e-12:
            break
    return h


def _betainc(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    ln = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log(1 - x)
    front = math.exp(ln)
    if x < (a + 1) / (a + b + 2):
        return front * _betacf(a, b, x) / a
    return 1 - front * _betacf(b, a, 1 - x) / b


def _pf_survival(stat, d1, d2):
    if not math.isfinite(stat):
        return np.nan
    x = d2 / (d2 + d1 * stat)
    return _betainc(d2 / 2, d1 / 2, x)


def _residuals(y, fl, add_intercept=True):
    y = _vector(y)
    if isinstance(fl, str) or (isinstance(fl, np.ndarray) and fl.dtype.kind in "USO") or (isinstance(fl, list) and fl and isinstance(fl[0], str)):
        return fwithin(y, g=fl, na_rm=False).values
    design = np.asarray(fl, dtype=np.float64)
    if design.ndim == 1:
        design = design.reshape(-1, 1)
    if add_intercept:
        design = np.column_stack([np.ones(design.shape[0]), design])
    coef, *_ = np.linalg.lstsq(design, y, rcond=None)
    return y - design @ coef


def fhdwithin_default(x, fl, w=None, na_rm=None, fill=False, lm_method="qr"):
    del w, lm_method, fill
    if na_rm is None:
        na_rm = _opt("na.rm")
    values = _vector(x)
    several = (
        isinstance(fl, (list, tuple))
        and fl
        and isinstance(fl[0], (list, tuple, np.ndarray))
        and not isinstance(fl[0], (str, bytes))
    )
    if several:
        current = values.copy()
        for _ in range(50):
            previous = current.copy()
            for factor_ in fl:
                current = fwithin(current, g=factor_, na_rm=False).values
            if np.nanmax(np.abs(current - previous)) < 1e-10:
                break
        return Vec(current)
    return Vec(_residuals(values, fl))


def fhdwithin_matrix(x, fl, w=None, na_rm=None, fill=False, lm_method="qr"):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    cols = [fhdwithin_default(values[:, j], fl, w, na_rm, fill, lm_method).values for j in range(values.shape[1])]
    return Mat(np.column_stack(cols))


def fhdwithin_data_frame(x, fl, w=None, na_rm=None, fill=False, variable_wise=False, lm_method="qr"):
    del variable_wise
    frame = _df(x)
    return DF({name: fhdwithin_default(column, fl, w, na_rm, fill, lm_method).values for name, column in frame.columns.items() if _is_numeric_col(column)})


def fhdwithin(x, fl, w=None, na_rm=None, fill=False, lm_method="qr", **kwargs):
    if _is_df(x):
        return fhdwithin_data_frame(x, fl, w, na_rm, fill, kwargs.get("variable_wise", False), lm_method)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return fhdwithin_matrix(x, fl, w, na_rm, fill, lm_method)
    return fhdwithin_default(x, fl, w, na_rm, fill, lm_method)


def fhdbetween_default(x, fl, w=None, na_rm=None, fill=False, lm_method="qr"):
    values = _vector(x)
    within = fhdwithin_default(values, fl, w, na_rm, fill, lm_method).values
    return Vec(values - within)


def fhdbetween_matrix(x, fl, w=None, na_rm=None, fill=False, lm_method="qr"):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    within = fhdwithin_matrix(values, fl, w, na_rm, fill, lm_method).values
    return Mat(values - within)


def fhdbetween_data_frame(x, fl, w=None, na_rm=None, fill=False, variable_wise=False, lm_method="qr"):
    frame = _df(x)
    within = fhdwithin_data_frame(frame, fl, w, na_rm, fill, variable_wise, lm_method)
    return DF({name: _numeric_col(frame.columns[name]) - within.columns[name] for name in within.columns})


def fhdbetween(x, fl, **kwargs):
    if _is_df(x):
        return fhdbetween_data_frame(x, fl, **kwargs)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return fhdbetween_matrix(x, fl, **kwargs)
    return fhdbetween_default(x, fl, **kwargs)


def fHDbetween(x, *args, **kwargs):
    return fhdbetween(x, *args, **kwargs)


def fHDwithin(x, *args, **kwargs):
    return fhdwithin(x, *args, **kwargs)


def fHDbetween_default(x, *args, **kwargs):
    return fhdbetween_default(x, *args, **kwargs)


def fHDbetween_matrix(x, *args, **kwargs):
    return fhdbetween_matrix(x, *args, **kwargs)


def fHDbetween_data_frame(x, *args, **kwargs):
    return fhdbetween_data_frame(x, *args, **kwargs)


def fHDwithin_default(x, *args, **kwargs):
    return fhdwithin_default(x, *args, **kwargs)


def fHDwithin_matrix(x, *args, **kwargs):
    return fhdwithin_matrix(x, *args, **kwargs)


def fHDwithin_data_frame(x, *args, **kwargs):
    return fhdwithin_data_frame(x, *args, **kwargs)


def HDW(x, *args, **kwargs):
    return fhdwithin(x, *args, **kwargs)


def HDB(x, *args, **kwargs):
    return fhdbetween(x, *args, **kwargs)


def flm_default(y, X, w=None, add_icpt=False, return_raw=False, method="lm", eigen_method=3):
    del eigen_method
    if method not in ("lm", "qr", "solve", "chol"):
        raise CollapseError("arma and eigen need RcppArmadillo or RcppEigen, which are not used")
    design = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
    target = np.asarray(y, dtype=np.float64)
    if add_icpt:
        design = np.column_stack([np.ones(design.shape[0]), design])
    if w is not None:
        weight = np.sqrt(_vector(w))
        design = design * weight[:, None]
        target = target * weight
    coef, *_ = np.linalg.lstsq(design, target, rcond=None)
    if return_raw:
        fitted = (design @ coef)
        if w is not None:
            fitted = fitted / weight
            resid = _vector(y) - fitted
        else:
            resid = target - fitted
        return {"coefficients": Vec(coef), "residuals": Vec(resid), "fitted": Vec(np.asarray(y, dtype=np.float64) - resid)}
    return Vec(coef)


def flm(y, X, **kwargs):
    return flm_default(y, X, **kwargs)


def fFtest_default(y, exc, X=None, w=None, full_df=True):
    del w, full_df
    y = _vector(y)
    exc = np.asarray(exc, dtype=np.float64)
    if exc.ndim == 1:
        exc = exc.reshape(-1, 1)
    if X is None:
        within = fhdwithin_default(y, exc, na_rm=False).values
        return Vec([float(np.var(within, ddof=1))])
    base = np.asarray(X, dtype=np.float64)
    if base.ndim == 1:
        base = base.reshape(-1, 1)
    full = np.column_stack([base, exc])
    def r2(design):
        coef, *_ = np.linalg.lstsq(design, y, rcond=None)
        resid = y - design @ coef
        return 1 - float(np.var(resid, ddof=1)) / float(np.var(y, ddof=1))
    r2f = r2(full)
    r2r = r2(base)
    n = float(y.size)
    # cbind(y, X, exc) counts y as the intercept column, then every column of X and exc.
    p = float(exc.shape[1])
    k = 1.0 + float(base.shape[1]) + p
    kr = k - p - 1
    ndff = k - 1
    ddff = n - k
    ddfr = n - kr - 1
    def fstat(rsq, d1, d2):
        if rsq >= 1:
            return math.inf
        return rsq / d1 * d2 / (1 - rsq)
    ff = fstat(r2f, ndff, ddff)
    fr = fstat(r2r, kr, ddfr)
    fe = (r2f - r2r) / p * ddff / (1 - r2f) if r2f < 1 else (math.nan if r2f == r2r else math.inf)
    rows = [
        [r2f, ndff, ddff, ff, _pf_survival(ff, ndff, ddff)],
        [r2r, kr, ddfr, fr, _pf_survival(fr, kr, ddfr)],
        [r2f - r2r, p, ddff, fe, _pf_survival(fe, p, ddff) if math.isfinite(fe) else np.nan],
    ]
    return Mat(rows, rows=["Full Model", "Restricted Model", "Exclusion Rest."], columns=["R-Sq.", "DF1", "DF2", "F-Stat.", "P-Value"])


def fFtest(y=None, exc=None, X=None, **kwargs):
    return fFtest_default(y, exc, X, **kwargs)


def _panel_scale(x, g):
    return fscale(x, g=g).values


def _acf_values(x, g, lag_max, kind, cross=None):
    series = _panel_scale(x, g)
    other = series if cross is None else _panel_scale(cross, g)
    var = float(fvar(series).values[0]) if cross is None else float(np.sqrt(fvar(series).values[0] * fvar(other).values[0]))
    if kind == "covariance":
        lags = list(range(0, lag_max + 1)) if cross is None else list(range(-lag_max, lag_max + 1))
        return [ _cov_pair(series, flag(other, n, g=g).values) for n in lags ]
    if cross is None:
        out = [1.0]
        for n in range(1, lag_max + 1):
            out.append(_cov_pair(series, flag(other, n, g=g).values) / var)
        return out
    out = []
    sx = float(fvar(series).values[0]) ** 0.5
    sy = float(fvar(other).values[0]) ** 0.5
    for n in range(-lag_max, lag_max + 1):
        out.append(_cov_pair(series, flag(other, n, g=g).values) / (sx * sy))
    return out


def _cov_pair(a, b):
    mask = np.isfinite(a) & np.isfinite(b)
    if mask.sum() < 2:
        return np.nan
    return float(np.cov(a[mask], b[mask], ddof=1)[0, 1])


def psacf_default(x, g, t=None, lag_max=None, type="correlation", plot=False, gscale=True):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    values = _vector(x)
    ng = len(factor(g)[1])
    if lag_max is None:
        lag_max = int(round(2 * math.sqrt(values.size / ng)))
    if not gscale:
        series = values
    else:
        series = values
    acf = _acf_values(series, g, lag_max, type)
    if type == "partial":
        acf = _pacf_from_acf(acf)
    result = Acf(acf, type, values.size, np.arange(0 if type != "partial" else 1, len(acf) + (0 if type != "partial" else 1)), "x")
    if plot:
        _stem(result.acf, "Panel Series ACF")
    return result


def psacf_data_frame(x, by, t=None, cols=None, lag_max=None, type="correlation", plot=False, gscale=True):
    frame = _df(x)
    name = list(frame.columns)[0] if cols is None else list(cols)[0]
    group = frame.columns[by] if isinstance(by, str) else by
    return psacf_default(frame.columns[name], group, t, lag_max, type, plot, gscale)


def psacf(x, g=None, by=None, **kwargs):
    if _is_df(x):
        return psacf_data_frame(x, by if by is not None else g, **kwargs)
    return psacf_default(x, g if g is not None else by, **kwargs)


def _pacf_from_acf(acf):
    # Durbin-Levinson on a 1-d acf. Lag 0 is dropped from the returned partials, matching stats::pacf.
    r = list(acf)
    limit = next((i for i, value in enumerate(r) if not math.isfinite(value)), len(r))
    phi = []
    out = []
    for k in range(1, limit):
        if k == 1:
            phi = [r[1]]
        else:
            prev = phi
            acc = r[k]
            for j in range(1, k):
                acc -= prev[j - 1] * r[k - j]
            acc /= 1 - sum(prev[j] * r[j + 1] for j in range(k - 1)) if False else (1 - sum(prev[j] * r[j + 1] for j in range(k - 1)))
            phi = [prev[j] - acc * prev[k - 2 - j] for j in range(k - 1)] + [acc]
        out.append(phi[-1])
    return out + [np.nan] * (len(r) - 1 - len(out))


def pspacf_default(x, g, t=None, lag_max=None, plot=False, gscale=True):
    return psacf_default(x, g, t, lag_max, "partial", plot, gscale)


def pspacf_data_frame(x, by, **kwargs):
    kwargs["type"] = "partial"
    return psacf_data_frame(x, by, **kwargs)


def pspacf(x, g=None, by=None, **kwargs):
    if _is_df(x):
        return pspacf_data_frame(x, by if by is not None else g, **kwargs)
    return pspacf_default(x, g, **kwargs)


def psccf_default(x, y, g, t=None, lag_max=None, type="correlation", plot=False, gscale=True):
    if t is not None:
        raise CollapseError("a time variable is not translated")
    values = _vector(x)
    ng = len(factor(g)[1])
    if lag_max is None:
        lag_max = int(round(2 * math.sqrt(values.size / ng)))
    acf = _acf_values(values, g, lag_max, type, cross=_vector(y))
    result = Acf(acf, type, values.size, np.arange(-lag_max, lag_max + 1), "x & y")
    if plot:
        _stem(result.acf, "Panel Series CCF")
    del gscale
    return result


def psccf(x, y, g, **kwargs):
    return psccf_default(x, y, g, **kwargs)


def psmat_default(x, g, t=None, transpose=False, fill=None):
    values = _vector(x)
    if np.isscalar(g) or (isinstance(g, (int, np.integer)) or (isinstance(g, float) and float(g).is_integer() and not isinstance(g, (list, np.ndarray)))):
        n = int(round(float(g)))
        if transpose:
            return Mat(values.reshape(-1, n))
        return Mat(values.reshape(n, -1))
    if t is not None:
        raise CollapseError("a time variable is not translated")
    codes, levels = q_levels(g, na_exclude=False, sort=True)
    groups = {}
    for value, code in zip(values, codes):
        groups.setdefault(code, []).append(value)
    width = max(len(v) for v in groups.values())
    rows = []
    for code in range(1, len(levels) + 1):
        row = groups.get(code, [])
        pad_value = np.nan if fill is None else fill
        rows.append(row + [pad_value] * (width - len(row)))
    return Mat(np.vstack(rows), rows=levels)


def psmat_data_frame(x, by, t=None, cols=None, transpose=False, fill=None, array=True):
    del array
    frame = _df(x)
    group = frame.columns[by] if isinstance(by, str) else by
    names = [name for name in frame.columns if name != by] if cols is None else list(cols)
    return {name: psmat_default(frame.columns[name], group, t, transpose, fill) for name in names}


def psmat(x, g=None, by=None, **kwargs):
    if _is_df(x):
        return psmat_data_frame(x, by if by is not None else g, **kwargs)
    return psmat_default(x, g, **kwargs)


def plot_psmat(x, **kwargs):
    matrix = x.values if isinstance(x, Mat) else np.asarray(x, dtype=np.float64)
    _heat(matrix)
    return Mat(matrix)


def _stem(values, title):
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.stem(np.arange(len(values)), np.asarray(values, dtype=float))
    ax.set_title(title)
    return fig


def _heat(values):
    import matplotlib
    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.imshow(np.asarray(values, dtype=float), aspect="auto")
    return fig


# ---------------------------------------------------------------------------
# frames
# ---------------------------------------------------------------------------


def _select_names(frame, names):
    return DF({name: frame.columns[name] for name in names}, frame.rows, frame.groups, frame.index)


def fselect(x, *names, cols=None):
    frame = _df(x)
    chosen = list(names) if names else list(cols)
    return _select_names(frame, chosen)


def slt(x, *names, **kwargs):
    return fselect(x, *names, **kwargs)


def fselect_assign(x, value, cols=None):
    frame = _df(x)
    if isinstance(value, dict):
        frame.columns.update({name: _as_col(column) for name, column in value.items()})
    return frame


def slt_assign(x, value, cols=None):
    return fselect_assign(x, value, cols)


def fsubset_default(x, i):
    return ss(x, np.flatnonzero(np.asarray(i, dtype=bool)) + 1)


def fsubset_matrix(x, i):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    return Mat(values[np.asarray(i, dtype=bool)])


def fsubset_data_frame(x, i):
    frame = _df(x)
    keep = np.flatnonzero(np.asarray(i, dtype=bool))
    return DF({name: column[keep] for name, column in frame.columns.items()}, None if frame.rows is None else [frame.rows[k] for k in keep])


def fsubset(x, i):
    if _is_df(x):
        return fsubset_data_frame(x, i)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return fsubset_matrix(x, i)
    return fsubset_default(x, i)


def sbt(x, i):
    return fsubset(x, i)


def ftransform(x, **columns):
    frame = _df(x).copy()
    for name, value in columns.items():
        if callable(value):
            value = value(frame)
        frame.columns[name] = _as_col(value.values if isinstance(value, Vec) else value)
    return frame


def tfm(x, **columns):
    return ftransform(x, **columns)


def ftransformv(x, cols, value):
    frame = _df(x).copy()
    for name in cols:
        frame.columns[name] = _as_col(value(frame.columns[name]) if callable(value) else value)
    return frame


def tfmv(x, cols, value):
    return ftransformv(x, cols, value)


def ftransform_assign(x, **columns):
    return ftransform(x, **columns)


def tfm_assign(x, **columns):
    return ftransform(x, **columns)


def settransform(x, **columns):
    updated = ftransform(x, **columns)
    if isinstance(x, DF):
        x.columns.update(updated.columns)
        return x
    return updated


def settfm(x, **columns):
    return settransform(x, **columns)


def settransformv(x, cols, value):
    updated = ftransformv(x, cols, value)
    if isinstance(x, DF):
        x.columns.update(updated.columns)
        return x
    return updated


def settfmv(x, cols, value):
    return settransformv(x, cols, value)


def fmutate(x, **columns):
    return ftransform(x, **columns)


def mtt(x, **columns):
    return ftransform(x, **columns)


def fcompute(x, **columns):
    frame = _df(x)
    out = {}
    for name, value in columns.items():
        got = value(frame) if callable(value) else value
        out[name] = _as_col(got.values if isinstance(got, Vec) else got)
    return DF(out)


def fcomputev(x, cols, value):
    frame = _df(x)
    return DF({name: _as_col(value(frame.columns[name]) if callable(value) else value) for name in cols})


def fsummarise(x, by=None, **reductions):
    frame = _df(x)
    if by is None:
        out = {}
        for name, value in reductions.items():
            got = value(frame) if callable(value) else value
            out[name] = np.atleast_1d(got.values if isinstance(got, Vec) else got)
        return DF(out)
    groups = GRP(frame.columns[by] if isinstance(by, str) else by)
    rows = {level: [] for level in groups.levels}
    # build one reduced row per group by filtering
    out_cols = {name: [] for name in reductions}
    labels = []
    for level_i, level in enumerate(groups.levels):
        mask = groups.codes == (level_i + 1)
        part = DF({name: column[mask] for name, column in frame.columns.items()})
        labels.append(level)
        for name, value in reductions.items():
            got = value(part) if callable(value) else value
            scalar = got.values[0] if isinstance(got, Vec) else got
            out_cols[name].append(scalar)
    if isinstance(by, str) and by not in out_cols:
        out_cols = {by: np.array(labels, dtype=object), **{name: np.array(vals, dtype=np.float64) for name, vals in out_cols.items()}}
    else:
        out_cols = {name: np.array(vals, dtype=np.float64) for name, vals in out_cols.items()}
    return DF(out_cols)


def fsummarize(x, by=None, **reductions):
    return fsummarise(x, by=by, **reductions)


def smr(x, by=None, **reductions):
    return fsummarise(x, by=by, **reductions)


def collap(X, by, FUN=None, catFUN=None, cols=None, w=None, wFUN=None, custom=None):
    del w, wFUN, custom
    frame = _df(X)
    group_name = by if isinstance(by, str) else None
    group = frame.columns[by] if isinstance(by, str) else by
    names = list(frame.columns) if cols is None else list(cols)
    out = {}
    if group_name:
        uniq = funique_default(group, sort=True)
        out[group_name] = np.array(uniq if isinstance(uniq, list) else uniq.values, dtype=object)
    for name in names:
        if name == group_name:
            continue
        column = frame.columns[name]
        if _is_numeric_col(column):
            reduced = (FUN or fmean)(column, g=group)
            out[name] = reduced.values
        else:
            reduced = (catFUN or fmode)(column, g=group)
            out[name] = reduced.values if isinstance(reduced, Vec) else np.array(reduced)
    # column order: numeric reductions then group, matching collap's default of keeping by on the left
    if group_name:
        ordered = {group_name: out[group_name]}
        # probe of collap(~g) on y,g returned means then the group labels, so data columns first
        ordered = {name: out[name] for name in names if name != group_name}
        ordered[group_name] = out[group_name]
        return DF(ordered)
    return DF(out)


def collapv(X, by, cols=None, FUN=None, catFUN=None):
    return collap(X, by, FUN=FUN, catFUN=catFUN, cols=cols)


def collapg(X, FUN=None, catFUN=None):
    if not isinstance(X, DF) or X.groups is None or not X.groups.vars:
        raise CollapseError("collapg needs a grouped data frame")
    names = list(X.groups.vars)
    out = collap(X, names[0] if len(names) == 1 else X.groups.codes, FUN=FUN, catFUN=catFUN)
    front = [name for name in names if name in out.columns]
    rest = [name for name in out.columns if name not in front]
    return DF({name: out.columns[name] for name in front + rest})


def BY_default(x, g, FUN, use_g_names=True, sort=None, reorder=True, expand_wide=False, parallel=False, return_="same"):
    del reorder, parallel
    if sort is None:
        sort = _opt("sort")
    groups = GRP(g, sort=sort)
    parts = []
    values = _vector(x)
    for level_i in range(groups.n):
        mask = groups.codes == (level_i + 1)
        piece = values[mask]
        got = FUN(piece)
        parts.append(got.values if isinstance(got, Vec) else np.atleast_1d(got))
    if return_ == "list":
        return {level: part for level, part in zip(groups.levels, parts)} if use_g_names else parts
    flat = np.array([float(np.asarray(part).reshape(-1)[0]) for part in parts])
    return Vec(flat, groups.levels if use_g_names else None)


def BY_matrix(x, g, FUN, **kwargs):
    values = np.asarray(x.values if isinstance(x, Mat) else x, dtype=np.float64)
    cols = [BY_default(values[:, j], g, FUN, **kwargs) for j in range(values.shape[1])]
    return Mat(np.column_stack([col.values for col in cols]), rows=cols[0].names)


def BY_data_frame(x, g, FUN, **kwargs):
    frame = _df(x)
    columns = {name: BY_default(column, g if not isinstance(g, str) else frame.columns[g], FUN, **kwargs).values for name, column in frame.columns.items() if _is_numeric_col(column)}
    return DF(columns)


def BY(x, g, FUN, **kwargs):
    if _is_df(x):
        return BY_data_frame(x, g, FUN, **kwargs)
    if isinstance(x, (Mat, np.ndarray)) and np.asarray(getattr(x, "values", x)).ndim == 2:
        return BY_matrix(x, g, FUN, **kwargs)
    return BY_default(x, g, FUN, **kwargs)


def fcount(x, *cols, w=None, name="N", add=False, sort=False, decreasing=False, drop=True):
    del w, decreasing, drop
    frame = _df(x) if _is_df(x) else DF({"x": x})
    names = list(cols) if cols else list(frame.columns)
    keys = []
    for i in range(frame.nrow):
        keys.append(tuple(_cell(frame.columns[name][i]) for name in names))
    counts = {}
    order = []
    for key in keys:
        if key not in counts:
            counts[key] = 0
            order.append(key)
        counts[key] += 1
    if sort:
        order = sorted(order, reverse=bool(decreasing) if isinstance(decreasing, bool) else False)
    out = {name: np.array([key[j] for key in order], dtype=object) for j, name in enumerate(names)}
    out[name] = np.array([counts[key] for key in order], dtype=np.float64)
    result = DF(out)
    if add:
        return ftransform(frame, **{name: result.columns[name][0]})
    return result


def fcountv(x, cols=None, w=None, name="N", add=False, sort=False, drop=True, **kwargs):
    chosen = list(cols) if cols is not None else []
    return fcount(x, *chosen, w=w, name=name, add=add, sort=sort, drop=drop)


def fslice(x, by=None, n=1, how="first", order_by=None, na_rm=None, sort=False, with_ties=False):
    del sort, with_ties
    if na_rm is None:
        na_rm = _opt("na.rm")
    if _is_df(x):
        frame = _df(x)
        if by is None:
            if how == "first":
                keep = list(range(int(n)))
            elif how == "last":
                keep = list(range(frame.nrow - int(n), frame.nrow))
            else:
                order = np.argsort(_numeric_col(frame.columns[order_by] if isinstance(order_by, str) else order_by))
                keep = list(order[: int(n)] if how == "min" else order[::-1][: int(n)])
            return DF({name: column[keep] for name, column in frame.columns.items()})
        group = frame.columns[by] if isinstance(by, str) else by
        if how == "first":
            picked = ffirst(np.arange(1, frame.nrow + 1, dtype=float), g=group, na_rm=False)
        elif how == "last":
            picked = flast(np.arange(1, frame.nrow + 1, dtype=float), g=group, na_rm=False)
        else:
            values = _numeric_col(frame.columns[order_by] if isinstance(order_by, str) else order_by)
            target = (fmin if how == "min" else fmax)(values, g=group, na_rm=na_rm)
            codes, _levels = factor(group)
            picked_idx = []
            for k, stat in enumerate(target.values):
                for i, code in enumerate(codes):
                    if int(code) == k and values[i] == stat:
                        picked_idx.append(i)
                        break
            return DF({name: column[picked_idx] for name, column in frame.columns.items()})
        index = [int(v) - 1 for v in picked.values]
        return DF({name: column[index] for name, column in frame.columns.items()})
    values = _vector(x)
    if how == "first":
        return Vec(values[: int(n)])
    if how == "last":
        return Vec(values[-int(n):])
    return Vec(values)


def fslicev(x, cols=None, n=1, how="first", order_by=None, na_rm=None, sort=False, with_ties=False):
    return fslice(x, by=cols, n=n, how=how, order_by=order_by, na_rm=na_rm, sort=sort, with_ties=with_ties)


def _take_types(frame, kind):
    out = {}
    for name, column in frame.columns.items():
        numeric = _is_numeric_col(column)
        if kind == "num" and numeric:
            out[name] = column
        elif kind == "cat" and not numeric:
            out[name] = column
        elif kind == "char" and not numeric:
            out[name] = column
        elif kind == "logi" and isinstance(column, np.ndarray) and column.dtype == bool:
            out[name] = column
        elif kind == "date":
            continue
        elif kind == "fact" and isinstance(column, Vec):
            out[name] = column
    return DF(out) if out else DF({})


def num_vars(X):
    return _take_types(_df(X), "num")


def nv(X):
    return num_vars(X)


def cat_vars(X):
    return _take_types(_df(X), "cat")


def char_vars(X):
    return _take_types(_df(X), "char")


def logi_vars(X):
    return _take_types(_df(X), "logi")


def fact_vars(X):
    return _take_types(_df(X), "fact")


def date_vars(X):
    return _take_types(_df(X), "date")


def num_vars_assign(X, value):
    return ftransform(X, **value)


def nv_assign(X, value):
    return num_vars_assign(X, value)


def cat_vars_assign(X, value):
    return ftransform(X, **value)


def char_vars_assign(X, value):
    return ftransform(X, **value)


def logi_vars_assign(X, value):
    return ftransform(X, **value)


def fact_vars_assign(X, value):
    return ftransform(X, **value)


def date_vars_assign(X, value):
    return ftransform(X, **value)


def get_vars(X, vars, return_="data", regex=False):
    frame = _df(X)
    if callable(vars):
        names = [name for name, column in frame.columns.items() if vars(column)]
    elif regex:
        names = [name for name in frame.columns if re.search(vars, name)]
    elif isinstance(vars, (list, tuple)):
        names = list(vars)
    else:
        names = [vars]
    part = DF({name: frame.columns[name] for name in names})
    if return_ == "names":
        return names
    return part


def gv(X, vars, **kwargs):
    return get_vars(X, vars, **kwargs)


def gvr(X, vars, **kwargs):
    kwargs["regex"] = True
    return get_vars(X, vars, **kwargs)


def get_vars_assign(X, vars, value):
    return ftransform(X, **({vars: value} if isinstance(vars, str) else value))


def gv_assign(X, vars, value):
    return get_vars_assign(X, vars, value)


def gvr_assign(X, vars, value):
    frame = _df(X)
    names = [name for name in frame.columns if re.search(str(vars), name)]
    return ftransform(frame, **{name: value for name in names})


def add_vars(X, **columns):
    return ftransform(X, **columns)


def av(X, **columns):
    return add_vars(X, **columns)


def add_vars_assign(X, **columns):
    return settransform(X, **columns)


def av_assign(X, **columns):
    return add_vars_assign(X, **columns)


def roworder(X, *cols, na_last=True, verbose=1):
    del verbose
    frame = _df(X)
    decreasing = []
    names = []
    for col in cols:
        text = str(col)
        decreasing.append(text.startswith("-"))
        names.append(text[1:] if text.startswith("-") else text)
    order = _order_index([frame.columns[name] for name in names], na_last=na_last, decreasing=decreasing)
    index = [i - 1 for i in order]
    return DF({name: column[index] for name, column in frame.columns.items()})


def roworderv(X, cols, na_last=True, decreasing=False):
    return roworder(X, *list(cols), na_last=na_last)


def colorder(X, *cols, pos="front"):
    frame = _df(X)
    chosen = [str(col) for col in cols]
    rest = [name for name in frame.columns if name not in chosen]
    if pos == "end":
        names = rest + chosen
    else:
        names = chosen + rest
    return DF({name: frame.columns[name] for name in names}, frame.rows)


def colorderv(X, cols, pos="front"):
    frame = _df(X)
    chosen = [frame.columns and list(frame.columns)[i - 1] if isinstance(i, (int, np.integer)) else i for i in cols]
    return colorder(frame, *chosen, pos=pos)


def frename(X, **names):
    frame = _df(X)
    mapping = {old: new for old, new in names.items()}
    # accept new=old style: frename(X, a="b") means column b becomes a? R frename uses new = old via NSE.
    # We take old="new" as rename old to new, which is the keyword direction.
    return DF({mapping.get(name, name): column for name, column in frame.columns.items()}, frame.rows)


def rnm(X, **names):
    return frename(X, **names)


def setrename(X, **names):
    updated = frename(X, **names)
    if isinstance(X, DF):
        X.columns.clear()
        X.columns.update(updated.columns)
        return X
    return updated


def relabel(X, **labels):
    frame = _df(X)
    if not isinstance(frame, DF):
        frame = DF(frame.columns)
    for name, label in labels.items():
        frame.labels[name] = label
    return frame


def setrelabel(X, **labels):
    return relabel(X, **labels)


def rowbind(*frames):
    items = [_df(frame) for frame in frames]
    names = list(items[0].columns)
    out = {}
    for name in names:
        cols = [frame.columns[name] for frame in items]
        if _is_numeric_col(cols[0]):
            out[name] = np.concatenate([_numeric_col(col) for col in cols])
        else:
            out[name] = np.concatenate([np.asarray(col, dtype=object) for col in cols])
    return DF(out)


def fgroup_by(X, *cols, sort=None):
    frame = _df(X).copy()
    if sort is None:
        sort = _opt("sort")
    frame.groups = GRP(frame, by=list(cols), sort=sort)
    return frame


def gby(X, *cols, **kwargs):
    return fgroup_by(X, *cols, **kwargs)


def group_by_vars(X, by=None, sort=None):
    if by is None:
        raise CollapseError("by is missing")
    cols = [by] if isinstance(by, str) else list(by)
    return fgroup_by(X, *cols, sort=sort)


def fgroup_vars(X, return_="data"):
    if not isinstance(X, DF) or X.groups is None:
        raise CollapseError("attr(X, 'groups') is not a grouping object")
    names = list(X.groups.vars or [])
    frame = fungroup(X)
    if return_ == "names":
        return names
    if return_ == "logical":
        return np.array([name in names for name in frame.columns], dtype=bool)
    return DF({name: frame.columns[name] for name in names})


def fungroup(X):
    frame = _df(X).copy()
    frame.groups = None
    return frame


def findex_by(X, *cols, single="auto", interact_ids=True):
    del single, interact_ids
    frame = _df(X).copy()
    frame.index = DF({f"id{i+1}": frame.columns[name] for i, name in enumerate(cols)})
    return frame


def iby(X, *cols, **kwargs):
    return findex_by(X, *cols, **kwargs)


def findex(x):
    if isinstance(x, DF) and x.index is not None:
        return x.index
    raise CollapseError("missing index")


def ix(x):
    return findex(x)


def reindex(x, index=None, single="auto"):
    del single
    frame = _df(x).copy()
    frame.index = index if isinstance(index, DF) else _df(index)
    return frame


def unindex(x):
    frame = _df(x).copy()
    frame.index = None
    return frame


def to_plm(x, row_names=False):
    index = findex(x)
    if len(index.columns) < 2:
        raise CollapseError("a plm index needs at least two columns")
    frame = unindex(x)
    if row_names:
        a = list(index.columns.values())[0]
        b = list(index.columns.values())[1]
        frame.rows = [f"{_cell(a[i])}-{_cell(b[i])}" for i in range(frame.nrow)]
    frame.index = index
    return frame


def qDF(X, row_names_col=False, keep_attr=False, class_="data.frame"):
    del keep_attr, class_
    if _is_df(X):
        return _df(X)
    if isinstance(X, (list, tuple)) and X and isinstance(X[0], (list, tuple, np.ndarray)):
        X = np.asarray(X, dtype=np.float64)
    if isinstance(X, (Mat, np.ndarray)) and np.asarray(getattr(X, "values", X)).ndim == 2:
        values = np.asarray(X.values if isinstance(X, Mat) else X, dtype=np.float64)
        names = getattr(X, "columns", None) or [f"V{i+1}" for i in range(values.shape[1])]
        return DF(dict(zip(names, [values[:, j] for j in range(values.shape[1])])))
    values = _vector(X) if not isinstance(X, Vec) else X.values
    return DF({"V1": values})


def qDT(X, **kwargs):
    return qDF(X, **kwargs)


def qTBL(X, **kwargs):
    return qDF(X, **kwargs)


def qM(X, row_names_col=None, keep_attr=False, class_=None, sep="."):
    del row_names_col, keep_attr, class_, sep
    if _is_df(X):
        cols = [_numeric_col(column) for column in _columns(X).values() if _is_numeric_col(column)]
        return Mat(np.column_stack(cols), columns=[name for name, column in _columns(X).items() if _is_numeric_col(column)])
    return Mat(np.asarray(X, dtype=np.float64))


def qtab(*args, w=None, sort=None, na_exclude=True, drop=False):
    del w, drop
    if sort is None:
        sort = _opt("sort")
    factors = [q_levels(arg, na_exclude=na_exclude, sort=sort) for arg in args]
    shape = [len(levels) for _codes, levels in factors]
    table = np.zeros(shape, dtype=np.float64)
    for i in range(len(factors[0][0])):
        if any(factors[k][0][i] is None for k in range(len(factors))):
            continue
        slot = tuple(factors[k][0][i] - 1 for k in range(len(factors)))
        table[slot] += 1
    return Mat(table) if table.ndim == 2 else Vec(table)


def qtable(*args, **kwargs):
    return qtab(*args, **kwargs)


def pivot(data, ids=None, values=None, names=None, how="wider", na_rm=False, fill=None, sort=False):
    frame = _df(data)
    if how in ("wider", "w"):
        id_name = ids
        value_name = values
        name_name = names if isinstance(names, str) else names[0]
        ids_u = funique_default(frame.columns[id_name], sort=sort)
        keys = funique_default(frame.columns[name_name], sort=True)
        key_list = keys if isinstance(keys, list) else [None if math.isnan(v) else (int(v) if float(v).is_integer() else float(v)) for v in keys.values]
        id_list = ids_u if isinstance(ids_u, list) else list(ids_u.values)
        out = {id_name: np.array(id_list, dtype=object)}
        lookup = {}
        for i in range(frame.nrow):
            lookup[(_cell(frame.columns[id_name][i]), _cell(frame.columns[name_name][i]))] = frame.columns[value_name][i]
        for key in key_list:
            column = []
            for ident in id_list:
                column.append(lookup.get((_cell(ident), _cell(key)), np.nan if fill is None else fill))
            out[_cell(key)] = np.array(column, dtype=np.float64)
        return DF(out)
    # longer
    id_names = [] if ids is None else ([ids] if isinstance(ids, str) else list(ids))
    value_names = [name for name in frame.columns if name not in id_names] if values is None else list(values)
    rows_id = []
    rows_name = []
    rows_value = []
    for i in range(frame.nrow):
        for name in value_names:
            value = frame.columns[name][i]
            if na_rm and _isna(value):
                continue
            rows_id.append({idn: frame.columns[idn][i] for idn in id_names})
            rows_name.append(name)
            rows_value.append(value)
    out = {idn: np.array([row[idn] for row in rows_id], dtype=object) for idn in id_names}
    out["name"] = np.array(rows_name, dtype=object)
    out["value"] = np.array(rows_value, dtype=np.float64)
    return DF(out)


def join(x, y, on, how="left", suffix="_y", verbose=False, multiple=False):
    del verbose, multiple
    left, right = _df(x), _df(y)
    keys = [on] if isinstance(on, str) else list(on)
    index = {}
    for i in range(right.nrow):
        key = tuple(_cell(right.columns[name][i]) for name in keys)
        index.setdefault(key, []).append(i)
    pairs = []
    for i in range(left.nrow):
        key = tuple(_cell(left.columns[name][i]) for name in keys)
        hits = index.get(key, [])
        if hits:
            for hit in hits:
                pairs.append((i, hit))
        elif how in ("left", "full"):
            pairs.append((i, None))
    if how in ("right", "full"):
        used = {hit for _i, hit in pairs if hit is not None}
        for j in range(right.nrow):
            if j not in used and how == "right":
                pairs.append((None, j))
    out_names = list(left.columns)
    for name in right.columns:
        if name not in keys and name not in out_names:
            out_names.append(name)
        elif name not in keys and name in out_names:
            out_names.append(name + suffix)
    columns = {name: [] for name in out_names}
    for i, j in pairs:
        for name in left.columns:
            columns[name].append(np.nan if i is None else left.columns[name][i])
        for name in right.columns:
            if name in keys:
                continue
            dest = name if name not in left.columns else name + suffix
            columns[dest].append(np.nan if j is None else right.columns[name][j])
    built = {}
    for name, values in columns.items():
        try:
            built[name] = np.array(values, dtype=np.float64)
        except (TypeError, ValueError):
            built[name] = np.array(values, dtype=object)
    return DF(built)


def L(x, n=1, g=None, **kwargs):
    return flag(x, n=n, g=g, **kwargs)


def D(x, n=1, diff=1, g=None, **kwargs):
    return fdiff(x, n=n, diff=diff, g=g, **kwargs)


def Dlog(x, n=1, diff=1, g=None, **kwargs):
    return fdiff(x, n=n, diff=diff, g=g, log=True, **kwargs)


def G(x, n=1, diff=1, g=None, **kwargs):
    return fgrowth(x, n=n, diff=diff, g=g, **kwargs)


def B(x, g=None, **kwargs):
    return fbetween(x, g=g, **kwargs)


def W(x, g=None, **kwargs):
    return fwithin(x, g=g, **kwargs)


def STD(x, g=None, **kwargs):
    return fscale(x, g=g, **kwargs)


# ---------------------------------------------------------------------------
# options, constants, datasets
# ---------------------------------------------------------------------------


def set_collapse(**opts):
    old = dict(_OPTIONS)
    allowed = set(_OPTIONS)
    unknown = [name for name in opts if name not in allowed]
    if unknown:
        raise CollapseError(f"unknown option: {unknown[0]}")
    for name, value in opts.items():
        if name in ("mask", "remove"):
            _OPTIONS[name] = value
            continue
        _OPTIONS[name] = value
    return old


def get_collapse(opts=None):
    if opts is None:
        return dict(_OPTIONS)
    if isinstance(opts, str):
        return _OPTIONS[opts]
    return {name: _OPTIONS[name] for name in opts}


FAST_FUN = (
    "fmean", "fmedian", "fmode", "fsum", "fprod", "fsd", "fvar", "fmin", "fmax", "fnth",
    "ffirst", "flast", "fnobs", "fndistinct", "fcumsum", "fscale", "fbetween", "fwithin",
    "fhdbetween", "fhdwithin", "flag", "fdiff", "fgrowth",
)
FAST_STAT_FUN = (
    "fmean", "fmedian", "fmode", "fsum", "fprod", "fsd", "fvar", "fmin", "fmax", "fnth",
    "ffirst", "flast", "fnobs", "fndistinct",
)
OPERATOR_FUN = ("STD", "B", "W", "HDB", "HDW", "L", "F", "D", "Dlog", "G")
COLLAPSE_TOPICS = (
    "collapse-documentation", "fast-statistical-functions", "fast-grouping-ordering",
    "fast-data-manipulation", "quick-conversion", "advanced-aggregation",
    "data-transformations", "time-series-panel-series", "list-processing",
    "summary-statistics", "recode-replace", "efficient-programming", "small-helpers", "collapse-options",
)
COLLAPSE_DATA = ("GGDC10S", "wlddev")
COLLAPSE_OLD = ("fNobs", "fNdistinct", "fHDwithin", "fHDbetween", "replace_NA", "replace_Inf")
COLLAPSE_GENERIC = (
    'B',
    'BY',
    'D',
    'Dlog',
    'G',
    'GRP',
    'HDB',
    'HDW',
    'L',
    'STD',
    'TRA',
    'W',
    'descr',
    'fbetween',
    'fcumsum',
    'fdiff',
    'fdroplevels',
    'ffirst',
    'fgrowth',
    'fhdbetween',
    'fhdwithin',
    'flag',
    'flast',
    'fmax',
    'fmean',
    'fmedian',
    'fmin',
    'fmode',
    'fndistinct',
    'fnobs',
    'fnth',
    'fprod',
    'fscale',
    'fsd',
    'fsubset',
    'fsum',
    'funique',
    'fvar',
    'fwithin',
    'psacf',
    'psccf',
    'psmat',
    'pspacf',
    'qsu',
    'rsplit',
    'varying',
)


def _read_table(name):
    path = DATA / f"{name}.csv"
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
    columns = {key: [] for key in reader.fieldnames}
    for row in rows:
        for key, value in row.items():
            columns[key].append(None if value == "NA" or value == "" else value)
    built = {}
    for key, values in columns.items():
        try:
            built[key] = np.array([np.nan if v is None else float(v) for v in values], dtype=np.float64)
        except ValueError:
            built[key] = np.array(values, dtype=object)
    return DF(built)


def wlddev():
    return _read_table("wlddev")


def GGDC10S():
    return _read_table("GGDC10S")


COLLAPSE_ALL = (
    '%!=%',
    '%!iin%',
    '%!in%',
    '%*=%',
    '%+=%',
    '%-=%',
    '%/=%',
    '%=%',
    '%==%',
    '%c*%',
    '%c+%',
    '%c-%',
    '%c/%',
    '%cr%',
    '%iin%',
    '%r*%',
    '%r+%',
    '%r-%',
    '%r/%',
    '%rr%',
    'B',
    'BY',
    'D',
    'Dlog',
    'G',
    'GGDC10S',
    'GRP',
    'GRPN',
    'GRPid',
    'GRPnames',
    'HDB',
    'HDW',
    'L',
    'STD',
    'TRA',
    'W',
    'add_stub',
    'add_vars',
    'add_vars<-',
    'allNA',
    'all_funs',
    'all_identical',
    'all_obj_equal',
    'alloc',
    'allv',
    'any_duplicated',
    'anyv',
    'as_character_factor',
    'as_factor_GRP',
    'as_factor_qG',
    'as_integer_factor',
    'as_numeric_factor',
    'atomic_elem',
    'atomic_elem<-',
    'av',
    'av<-',
    'cat_vars',
    'cat_vars<-',
    'char_vars',
    'char_vars<-',
    'cinv',
    'ckmatch',
    'collap',
    'collapg',
    'collapv',
    'colorder',
    'colorderv',
    'copyAttrib',
    'copyMostAttrib',
    'copyv',
    'dapply',
    'date_vars',
    'date_vars<-',
    'descr',
    'fFtest',
    'fact_vars',
    'fact_vars<-',
    'fbetween',
    'fcompute',
    'fcomputev',
    'fcount',
    'fcountv',
    'fcumsum',
    'fdiff',
    'fdim',
    'fdist',
    'fdroplevels',
    'fduplicated',
    'ffirst',
    'fgroup_by',
    'fgroup_vars',
    'fgrowth',
    'fhdbetween',
    'fhdwithin',
    'findex',
    'findex_by',
    'finteraction',
    'flag',
    'flast',
    'flm',
    'fmatch',
    'fmax',
    'fmean',
    'fmedian',
    'fmin',
    'fmode',
    'fmutate',
    'fncol',
    'fndistinct',
    'fnlevels',
    'fnobs',
    'fnrow',
    'fnth',
    'fnunique',
    'fprod',
    'fquantile',
    'frange',
    'frename',
    'fscale',
    'fsd',
    'fselect',
    'fselect<-',
    'fslice',
    'fslicev',
    'fsubset',
    'fsum',
    'fsummarise',
    'fsummarize',
    'ftransform',
    'ftransform<-',
    'ftransformv',
    'fungroup',
    'funique',
    'fvar',
    'fwithin',
    'gby',
    'get_collapse',
    'get_elem',
    'get_vars',
    'get_vars<-',
    'greorder',
    'group',
    'group_by_vars',
    'groupid',
    'groupv',
    'gsplit',
    'gv',
    'gv<-',
    'gvr',
    'gvr<-',
    'has_elem',
    'iby',
    'irreg_elem',
    'is_GRP',
    'is_categorical',
    'is_date',
    'is_irregular',
    'is_qG',
    'is_unlistable',
    'itn',
    'ix',
    'join',
    'ldepth',
    'list_elem',
    'list_elem<-',
    'logi_vars',
    'logi_vars<-',
    'massign',
    'mctl',
    'missing_cases',
    'mrtl',
    'mtt',
    'na_focb',
    'na_insert',
    'na_locf',
    'na_omit',
    'na_rm',
    'namlab',
    'num_vars',
    'num_vars<-',
    'nv',
    'nv<-',
    'pad',
    'pivot',
    'psacf',
    'psccf',
    'psmat',
    'pspacf',
    'pwcor',
    'pwcov',
    'pwnobs',
    'qDF',
    'qDT',
    'qF',
    'qG',
    'qM',
    'qTBL',
    'qsu',
    'qtab',
    'qtable',
    'radixorder',
    'radixorderv',
    'rapply2d',
    'recode_char',
    'recode_num',
    'reg_elem',
    'reindex',
    'relabel',
    'replace_inf',
    'replace_na',
    'replace_outliers',
    'rm_stub',
    'rnm',
    'rowbind',
    'roworder',
    'roworderv',
    'rsplit',
    'sbt',
    'seq_col',
    'seq_row',
    'seqid',
    'setAttrib',
    'setColnames',
    'setDimnames',
    'setLabels',
    'setRownames',
    'setTRA',
    'set_collapse',
    'setattrib',
    'setop',
    'setrelabel',
    'setrename',
    'settfm',
    'settfmv',
    'settransform',
    'settransformv',
    'setv',
    'slt',
    'slt<-',
    'smr',
    'ss',
    't_list',
    'tfm',
    'tfm<-',
    'tfmv',
    'timeid',
    'to_plm',
    'unattrib',
    'unindex',
    'unlist2d',
    'varying',
    'vclasses',
    'vec',
    'vgcd',
    'vlabels',
    'vlabels<-',
    'vlengths',
    'vtypes',
    'whichNA',
    'whichv',
    'wlddev',
)
