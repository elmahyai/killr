"""Reservation fac197e0 janitor data-frame utilities."""
from __future__ import annotations
import datetime as dt
import math
import re
import unicodedata
from collections import Counter
from typing import Any
import numpy as np
import polars as pl

def excel_numeric_to_date(x, date_system="modern", include_time=False,
                          round_seconds=True, tz=None):
    vals = np.asarray(x if isinstance(x, (list, tuple, np.ndarray)) else [x], dtype=float)
    origin = dt.date(1899, 12, 30) if date_system == "modern" else dt.date(1904, 1, 1)
    if date_system not in ("modern", "mac pre-2011"):
        raise ValueError("invalid date_system")
    out = []
    for v in vals:
        if np.isnan(v): out.append(None); continue
        n = math.floor(v)
        if date_system == "modern" and n == 60: out.append(None); continue
        if date_system == "modern" and n < 60: n += 1
        day = origin + dt.timedelta(days=n)
        if include_time:
            sec = (v - math.floor(v))*86400
            if round_seconds: sec = round(sec)
            out.append(dt.datetime.combine(day, dt.time()) + dt.timedelta(seconds=sec))
        else: out.append(day)
    return out

def get_dupes(dat, *columns):
    keys = list(columns) or dat.columns
    counts = dat.group_by(keys, maintain_order=True).len(name="dupe_count")
    return (dat.join(counts, on=keys).filter(pl.col("dupe_count") > 1)
            .select(keys + ["dupe_count"] + [c for c in dat.columns if c not in keys])
            .sort(["dupe_count"] + keys, descending=[True] + [False]*len(keys)))

def _codes(s):
    ids, out = {}, []
    for v in s:
        k = ("null",) if v is None else ("v", repr(v))
        ids.setdefault(k, len(ids)+1); out.append(ids[k])
    return out

def get_one_to_one(dat):
    codes = {c: _codes(dat[c].to_list()) for c in dat.columns}
    remaining, result = list(dat.columns), []
    while remaining:
        c = remaining.pop(0); group = [c]
        for d in remaining[:]:
            if codes[c] == codes[d]: group.append(d); remaining.remove(d)
        if len(group) > 1: result.append(group)
    return result

def add_totals_col(dat, name="Total", na_rm=True, columns=None):
    cols = list(columns) if columns is not None else [
        c for c, t in zip(dat.columns, dat.dtypes) if t.is_numeric() and c != dat.columns[0]]
    expr = sum((pl.col(c).fill_null(0) for c in cols), pl.lit(0))
    return dat.with_columns(expr.alias(name))

def add_totals_row(dat, name="Total", fill="-", na_rm=True, columns=None):
    cols = list(columns) if columns is not None else [
        c for c, t in zip(dat.columns, dat.dtypes) if t.is_numeric() and c != dat.columns[0]]
    row = {c: (dat[c].sum() if c in cols else (name if c == dat.columns[0] else fill))
           for c in dat.columns}
    return pl.concat([dat, pl.DataFrame([row])], how="vertical_relaxed")

def adorn_crosstab(dat, *args, **kwargs): return dat

def convert_to_NA(dat, value="", values=None):
    vals = values if values is not None else value
    vals = list(vals) if isinstance(vals, (list, tuple, set)) else [vals]
    return dat.with_columns([pl.when(pl.col(c).is_in(vals)).then(None).otherwise(pl.col(c)).alias(c)
                             for c in dat.columns])

def crosstab(x, y, show_na=True, show_missing_levels=True):
    pairs = [(a,b) for a,b in zip(x,y) if show_na or (a is not None and b is not None)]
    rows, cols = list(dict.fromkeys(a for a,_ in pairs)), list(dict.fromkeys(b for _,b in pairs))
    counts = Counter(pairs)
    data = {"x": rows}
    for c in cols: data["NA_" if c is None else str(c)] = [counts[(r,c)] for r in rows]
    return pl.DataFrame(data)

def remove_empty_rows(dat, cutoff=1, quiet=True):
    return dat.filter(pl.sum_horizontal(pl.all().is_not_null()) > (0 if cutoff == 1 else cutoff*dat.width))

def remove_empty_cols(dat, cutoff=1, quiet=True):
    keep = [(dat[c].null_count() != dat.height if cutoff == 1 else
             dat[c].drop_nulls().len()/dat.height > cutoff) for c in dat.columns]
    return dat.select([c for c,k in zip(dat.columns, keep) if k])

def remove_empty(dat, which=("rows","cols"), cutoff=1, quiet=True):
    if "rows" in which: dat = remove_empty_rows(dat, cutoff, quiet)
    if "cols" in which: dat = remove_empty_cols(dat, cutoff, quiet)
    return dat

def use_first_valid_of(*values):
    values = tuple(values[0]) if len(values)==1 and isinstance(values[0], (list,tuple,np.ndarray)) else values
    return next((v for v in values if v is not None and not (isinstance(v,float) and math.isnan(v))), None)

def make_clean_names(string, case="snake", replace=None, ascii=True,
                     use_make_names=True, allow_dupes=False, **kwargs):
    repl = {"'":"","\"":"","%":"_percent_","#":"_number_"}; repl.update(replace or {})
    out=[]
    for raw in string:
        s=str(raw)
        for a,b in repl.items(): s=s.replace(a,b)
        if ascii: s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
        s=re.sub(r"^[\W_]+","",s); s=re.sub(r"[\W_]+","_",s)
        if use_make_names and s and s[0].isdigit(): s="X"+s
        if case in ("snake","old_janitor"): s=s.lower()
        out.append(s)
    if not allow_dupes:
        seen=Counter()
        for i,s in enumerate(out):
            seen[s]+=1
            if seen[s]>1: out[i]=f"{s}_{seen[s]}"
    return out

def remove_constant(dat, na_rm=False, quiet=True):
    keep=[]
    for c in dat.columns:
        vals=dat[c].drop_nulls().to_list() if na_rm else dat[c].to_list()
        keep.append(len({repr(v) for v in vals})>1)
    return dat.select([c for c,k in zip(dat.columns,keep) if k])

__all__=[n for n in globals() if not n.startswith("_")]
