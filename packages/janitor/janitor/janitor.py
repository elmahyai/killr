"""Data-frame cleaning and tabyl helpers translated from janitor."""
from __future__ import annotations

import math
import re
import unicodedata
import datetime as _dt
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable, Iterable, Sequence

import numpy as np
import polars as pl


def _copy(df: pl.DataFrame) -> pl.DataFrame:
    return df.clone()


def _numeric(df: pl.DataFrame, explicit=None):
    if explicit is not None:
        return [c for c in explicit if c in df.columns and df[c].dtype.is_numeric()]
    return [c for c in df.columns[1:] if df[c].dtype.is_numeric()]


def _meta(df, key, default=None):
    return getattr(df, "_janitor_meta", {}).get(key, default)


def _setmeta(df, **kwargs):
    # Polars frames do not expose arbitrary attributes reliably; keep metadata
    # in a module cache keyed by object identity for the duration of a pipeline.
    _META[id(df)] = {**_META.get(id(df), {}), **kwargs}
    return df


_META: dict[int, dict[str, Any]] = {}


def as_tabyl(dat: pl.DataFrame, axes: int = 2, row_var_name=None,
             col_var_name=None) -> pl.DataFrame:
    if not isinstance(dat, pl.DataFrame):
        raise TypeError("input must be a data.frame")
    if axes not in (1, 2):
        raise ValueError("axes must be either 1 or 2")
    if not any(dat[c].dtype.is_numeric() for c in dat.columns[1:]):
        raise ValueError("at least one one of columns 2:n must be of class numeric")
    old = _META.get(id(dat), {})
    out = _copy(dat)
    core = old.get("core", dat)
    return _setmeta(out, core=core.clone(), tabyl_type=old.get("tabyl_type", "one_way" if axes == 1 else "two_way"),
                    totals=old.get("totals", []),
                    var_names={"row": row_var_name, "col": col_var_name}
                    if row_var_name is not None or col_var_name is not None else old.get("var_names"))


def untabyl(dat):
    if isinstance(dat, list):
        return [untabyl(x) for x in dat]
    if not isinstance(dat, pl.DataFrame):
        raise TypeError("dat must be a data.frame")
    out = _copy(dat)
    _META.pop(id(out), None)
    return out


def adorn_rounding(dat, digits=1, rounding="half to even", columns=None, **kwargs):
    if isinstance(dat, list):
        return [adorn_rounding(x, digits, rounding, columns) for x in dat]
    if rounding not in ("half to even", "half up"):
        raise ValueError("'rounding' must be one of 'half to even' or 'half up'")
    cols = _numeric(dat, columns)
    exprs = []
    for c in dat.columns:
        if c not in cols:
            exprs.append(pl.col(c))
        elif rounding == "half to even":
            exprs.append(pl.col(c).round(digits).alias(c))
        else:
            # Decimal half-up for both signs, as janitor::round_half_up.
            factor = 10.0 ** digits
            exprs.append((pl.col(c).map_elements(
                lambda x: None if x is None else math.copysign(math.floor(abs(x) * factor + .5), x) / factor,
                return_dtype=dat[c].dtype)).alias(c))
    return _setmeta(dat.select(exprs), **_META.get(id(dat), {}))


def adorn_percentages(dat, denominator="row", na_rm=True, columns=None, **kwargs):
    if isinstance(dat, list):
        return [adorn_percentages(x, denominator, na_rm, columns) for x in dat]
    if denominator not in ("row", "col", "all"):
        raise ValueError("'denominator' must be one of 'row', 'col', or 'all'")
    out = as_tabyl(dat)
    cols = _numeric(out, columns)
    meta = _META.get(id(out), {})
    totals = meta.get("totals", [])
    if "col" in totals and columns is None and cols:
        cols = cols[:-1]
    if denominator == "row":
        den = pl.sum_horizontal([pl.col(c).fill_null(0) for c in cols])
        out = out.with_columns([(pl.col(c) / den).alias(c) for c in cols])
        if "col" in totals and columns is None:
            out = out.with_columns(pl.lit(1.0).alias(dat.columns[-1]))
    elif denominator == "col":
        base = out.drop(out.height - 1) if "row" in totals and out.height else out
        sums = {c: base[c].sum() for c in cols}
        out = out.with_columns([(pl.col(c) / sums[c]).alias(c) for c in cols])
    else:
        base = out.drop(out.height - 1) if "row" in totals and out.height else out
        den = sum((base[c].sum() or 0) for c in cols)
        out = out.with_columns([(pl.col(c) / den).alias(c) for c in cols])
    return _setmeta(out, **_META.get(id(dat), {}))


def adorn_pct_formatting(dat, digits=1, rounding="half to even",
                         affix_sign=True, columns=None, **kwargs):
    if isinstance(dat, list):
        return [adorn_pct_formatting(x, digits, rounding, affix_sign, columns) for x in dat]
    cols = _numeric(dat, columns)
    out = adorn_rounding(dat.with_columns([(pl.col(c) * 100).alias(c) for c in cols]),
                         digits, rounding, cols)
    for c in cols:
        out = out.with_columns(pl.col(c).map_elements(
            lambda x: "-" if x is None or (isinstance(x, float) and np.isnan(x))
            else f"{x:.{digits}f}" + ("%" if affix_sign else ""),
            return_dtype=pl.String).alias(c))
    return _setmeta(out, **_META.get(id(dat), {}))


def adorn_ns(dat, position="rear", ns=None, format_func=None, columns=None, **kwargs):
    if isinstance(dat, list):
        return [adorn_ns(x, position, None, format_func, columns) for x in dat]
    if position not in ("front", "rear"):
        raise ValueError('"position" must be one of "front" or "rear"')
    if ns is None:
        ns = _META.get(id(dat), {}).get("core")
    if ns is None or ns.shape != dat.shape:
        raise ValueError("Ns must have the same dimensions as dat")
    fmt = format_func or (lambda x: f"{x:,}")
    cols = columns or _numeric(dat)
    out = dat.clone()
    for c in cols:
        vals = [f"{fmt(n)}" for n in ns[c].to_list()]
        vals = [f"({x})" for x in vals]
        out = out.with_columns(pl.Series(c, [
            f"{a} {b}" if position == "rear" else f"{b} {a}"
            for a, b in zip(dat[c].cast(pl.String).to_list(), vals)
        ]))
    return _setmeta(out, **_META.get(id(dat), {}))


def adorn_totals(dat, where="row", fill="-", na_rm=True, name="Total", columns=None, **kwargs):
    if isinstance(dat, list):
        return [adorn_totals(x, where, fill, na_rm, name, columns) for x in dat]
    if "both" in where:
        where = ("row", "col")
    if isinstance(where, str):
        where = (where,)
    cols = _numeric(dat, columns)
    out = dat.clone()
    names = [name, name] if isinstance(name, str) else list(name)
    if "row" in where:
        vals = []
        for c in out.columns:
            if c in cols:
                vals.append(out[c].sum())
            else:
                vals.append(names[0] if c == out.columns[0] else (fill if isinstance(fill, str) else None))
        out = pl.concat([out, pl.DataFrame([dict(zip(out.columns, vals))])], how="vertical_relaxed")
    if "col" in where:
        out = out.with_columns(pl.sum_horizontal([pl.col(c).fill_null(0) for c in cols]).alias(names[1]))
    return _setmeta(out, core=_META.get(id(dat), {}).get("core", dat.clone()),
                    totals=list(_META.get(id(dat), {}).get("totals", [])) + list(where))


def adorn_title(dat, placement="top", row_name=None, col_name=None):
    if isinstance(dat, list):
        return [adorn_title(x, placement, row_name, col_name) for x in dat]
    if placement not in ("top", "combined"):
        raise ValueError('"placement" must be one of "top" or "combined"')
    meta = _META.get(id(dat), {})
    vars_ = meta.get("var_names") or {}
    row = row_name or vars_.get("row") or dat.columns[0]
    col = col_name or vars_.get("col")
    if col is None:
        raise ValueError("col_name is required for a non-tabyl input")
    if placement == "combined":
        out = dat.rename({dat.columns[0]: f"{row}/{col}"})
    else:
        out = pl.concat([pl.DataFrame([{c: c for c in dat.columns}]), dat.cast({c: pl.String for c in dat.columns})],
                        how="vertical_relaxed")
        out = out.rename({c: ("" if i == 0 or i > 1 else col) for i, c in enumerate(out.columns)})
    return out


def _clean_one(s, case="snake", replace=None, ascii=True, allow_dupes=False, **kwargs):
    replace = replace or {"'": "", '"': "", "%": "_percent_", "#": "_number_"}
    for a, b in replace.items():
        s = s.replace(a, b)
    if ascii:
        s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    s = re.sub(r"[\W_]+", "_", s, flags=re.UNICODE).strip("_")
    if case in ("lower_camel", "small_camel"):
        parts = s.lower().split("_")
        s = parts[0] + "".join(x.title() for x in parts[1:])
    elif case in ("upper_camel", "pascal"):
        s = "".join(x.title() for x in s.lower().split("_"))
    elif case == "upper":
        s = s.upper()
    elif case == "lower":
        s = s.lower()
    else:
        s = s.lower()
    if not s or s[0].isdigit():
        s = "x" + s
    return s


def clean_names(dat, case="snake", **kwargs):
    if isinstance(dat, pl.DataFrame):
        names = [_clean_one(c, case, **kwargs) for c in dat.columns]
        if not kwargs.get("allow_dupes", False):
            seen = {}
            names = [n if n not in seen else f"{n}_{seen[n] + 1}" for n in names
                     for seen[n] in [seen.get(n, 0)]]
            for n in names: seen[n] = seen.get(n, 0) + 1
        return dat.rename(dict(zip(dat.columns, names)))
    return [_clean_one(str(x), case, **kwargs) for x in dat]


def describe_class(x, strict_description=True):
    if isinstance(x, pl.Series):
        d = str(x.dtype)
    elif isinstance(x, pl.DataFrame):
        d = "DataFrame"
    else:
        d = type(x).__name__
    return d


def compare_df_cols(*dfs, return_="all", bind_method="bind_rows", strict_description=False, **kwargs):
    names = kwargs.pop("names", None) or [f"df{i+1}" for i in range(len(dfs))]
    frames = [x for d in dfs for x in (d if isinstance(d, list) else [d])]
    labels = [n for n, d in zip(names, dfs) for _ in (d if isinstance(d, list) else [d])]
    allcols = list(dict.fromkeys(c for d in frames for c in d.columns))
    rows = [{"column_name": c, **{lab: (describe_class(d[c]) if c in d.columns else None)
                                  for lab, d in zip(labels, frames)}} for c in allcols]
    out = pl.DataFrame(rows)
    if return_ == "all" or out.width <= 2:
        return out
    dcols = [c for c in out.columns if c != "column_name"]
    mask = []
    for row in out.iter_rows(named=True):
        vals = [row[c] for c in dcols]
        valid = vals if bind_method == "rbind" else [v for v in vals if v is not None]
        mask.append(len(set(valid)) <= 1)
    return out.filter(pl.Series(mask if return_ == "match" else [not x for x in mask]))


def compare_df_cols_same(*dfs, bind_method="bind_rows", verbose=True, **kwargs):
    return compare_df_cols(*dfs, return_="mismatch", bind_method=bind_method).height == 0


def _excel_date(x, out="date", tz="UTC", round_seconds=True):
    # janitor uses Excel's modern (1899-12-30) system.
    dt = datetime(1899, 12, 30, tzinfo=timezone.utc) + timedelta(days=float(x))
    if round_seconds:
        dt = dt.replace(microsecond=0)
    return dt.date() if out == "date" else dt.astimezone(timezone.utc)


def _convert(x, out, tz="UTC", character_fun=None, string_conversion_failure="error", **kwargs):
    if x is None:
        return None
    if isinstance(x, (datetime, date)):
        return x.date() if out == "date" and isinstance(x, datetime) else (datetime.combine(x, datetime.min.time(), timezone.utc) if out == "datetime" and isinstance(x, date) else x)
    if isinstance(x, (int, float, np.number)) and not isinstance(x, bool):
        return _excel_date(x, out, tz, kwargs.get("round_seconds", True))
    s = str(x)
    if re.fullmatch(r"[0-9]{5}(?:\.[0-9]*)?", s):
        return _excel_date(float(s), out, tz, kwargs.get("round_seconds", True))
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.date() if out == "date" else dt.replace(tzinfo=dt.tzinfo or timezone.utc)
    except ValueError:
        if string_conversion_failure == "warning":
            return None
        raise ValueError(f"Not all character strings converted to class {out}: {s!r}")


def convert_to_date(x, **kwargs):
    if isinstance(x, (list, tuple, np.ndarray, pl.Series)):
        return [_convert(v, "date", **kwargs) for v in x]
    return _convert(x, "date", **kwargs)


def convert_to_datetime(x, tz="UTC", **kwargs):
    if isinstance(x, (list, tuple, np.ndarray, pl.Series)):
        return [_convert(v, "datetime", tz=tz, **kwargs) for v in x]
    return _convert(x, "datetime", tz=tz, **kwargs)

def excel_numeric_to_date(date_num: Any, date_system: str = "modern",
                          include_time: bool = False, round_seconds: bool = True,
                          tz: str | None = None) -> list[Any]:
    """Convert Excel serials, preserving R's 1900 leap-year correction."""
    values = np.asarray(date_num if isinstance(date_num, (list, tuple, np.ndarray)) else [date_num], dtype=float)
    out: list[Any] = []
    origin = _dt.date(1899, 12, 30) if date_system == "modern" else _dt.date(1904, 1, 1)
    if date_system not in ("modern", "mac pre-2011"):
        raise ValueError("date_system must be 'modern' or 'mac pre-2011'")
    for value in values:
        if np.isnan(value):
            out.append(None)
            continue
        days = math.floor(value)
        if date_system == "modern" and days == 60:
            out.append(None)
            continue
        if date_system == "modern" and days < 60:
            days += 1
        day = origin + _dt.timedelta(days=days)
        if include_time:
            seconds = (value - math.floor(value)) * 86400
            if round_seconds:
                seconds = round(seconds)
            out.append(_dt.datetime.combine(day, _dt.time()) + _dt.timedelta(seconds=seconds))
        else:
            out.append(day)
    return out


def _frame(dat: pl.DataFrame | dict[str, Any]) -> pl.DataFrame:
    return dat if isinstance(dat, pl.DataFrame) else pl.DataFrame(dat)


def get_dupes(dat: pl.DataFrame, *columns: str) -> pl.DataFrame:
    frame = _frame(dat)
    keys = list(columns) if columns else frame.columns
    counts = frame.group_by(keys, maintain_order=True).len(name="dupe_count")
    return (frame.join(counts, on=keys, how="left")
            .filter(pl.col("dupe_count") > 1)
            .select(keys + ["dupe_count"] + [c for c in frame.columns if c not in keys])
            .sort(["dupe_count"] + keys, descending=[True] + [False] * len(keys)))


def _value_order(s: pl.Series) -> pl.Series:
    seen: dict[Any, int] = {}
    result = []
    for value in s.to_list():
        key = ("null",) if value is None else ("value", value)
        if key not in seen:
            seen[key] = len(seen) + 1
        result.append(seen[key])
    return pl.Series(s.name, result, dtype=pl.Int64)


def get_one_to_one(dat: pl.DataFrame) -> list[list[str]]:
    frame = _frame(dat)
    if not frame.width:
        raise ValueError("dat must have at least one column")
    codes = {c: _value_order(frame[c]).to_list() for c in frame.columns}
    groups: list[list[str]] = []
    remaining = list(frame.columns)
    while remaining:
        first = remaining.pop(0)
        group = [first]
        for c in remaining[:]:
            if codes[c] == codes[first]:
                group.append(c)
                remaining.remove(c)
        if len(group) > 1:
            groups.append(group)
    return groups


def add_totals_col(dat: pl.DataFrame, name: str = "Total", na_rm: bool = True,
                   columns: Sequence[str] | None = None) -> pl.DataFrame:
    frame = _frame(dat)
    cols = list(columns) if columns is not None else [
        c for c, t in zip(frame.columns, frame.dtypes)
        if t.is_numeric() and c != frame.columns[0]
    ]
    exprs = [pl.col(c).fill_null(0) for c in cols]
    total = sum(exprs, pl.lit(0))
    return frame.with_columns(total.alias(name))


def add_totals_row(dat: pl.DataFrame, name: str = "Total", fill: Any = "-",
                   na_rm: bool = True, columns: Sequence[str] | None = None) -> pl.DataFrame:
    frame = _frame(dat)
    cols = list(columns) if columns is not None else [
        c for c, t in zip(frame.columns, frame.dtypes)
        if t.is_numeric() and c != frame.columns[0]
    ]
    values: dict[str, Any] = {}
    for c, dtype in zip(frame.columns, frame.dtypes):
        if c in cols and dtype.is_numeric():
            values[c] = frame[c].sum() if na_rm else frame[c].sum()
        elif c == frame.columns[0]:
            values[c] = name
        else:
            values[c] = fill
    return pl.concat([frame, pl.DataFrame([values]).cast({c: frame[c].dtype for c in frame.columns if c in values and frame[c].dtype == pl.String})],
                     how="vertical_relaxed")


def adorn_crosstab(dat: pl.DataFrame, *args: Any, **kwargs: Any) -> pl.DataFrame:
    """Compatibility wrapper: a crosstab is already a Polars frame."""
    return _frame(dat)


def convert_to_NA(dat: pl.DataFrame, value: Any = "", values: Any = None) -> pl.DataFrame:
    frame = _frame(dat)
    targets = values if values is not None else value
    targets = targets if isinstance(targets, (list, tuple, set)) else [targets]
    return frame.with_columns([
        pl.when(pl.col(c).is_in(list(targets))).then(None).otherwise(pl.col(c)).alias(c)
        for c in frame.columns
    ])


def crosstab(x: Sequence[Any], y: Sequence[Any], show_na: bool = True,
             show_missing_levels: bool = True) -> pl.DataFrame:
    xv, yv = list(x), list(y)
    if not show_na:
        pairs = [(a, b) for a, b in zip(xv, yv) if a is not None and b is not None]
        xv, yv = zip(*pairs) if pairs else ([], [])
    counts = Counter(zip(xv, yv))
    rows = list(dict.fromkeys(xv))
    cols = list(dict.fromkeys(yv))
    result = {str(c) if c is not None else "NA_": [counts[(r, c)] for r in rows] for c in cols}
    result[str(x.__class__.__name__) if False else "x"] = rows
    return pl.DataFrame(result).select(["x"] + [c for c in result if c != "x"])


def remove_empty_cols(dat: pl.DataFrame, cutoff: float = 1, quiet: bool = True) -> pl.DataFrame:
    frame = _frame(dat)
    if cutoff == 1:
        keep = [frame[c].null_count() != frame.height for c in frame.columns]
    else:
        keep = [frame[c].drop_nulls().len() / frame.height > cutoff for c in frame.columns]
    return frame.select([c for c, ok in zip(frame.columns, keep) if ok])


def remove_empty_rows(dat: pl.DataFrame, cutoff: float = 1, quiet: bool = True) -> pl.DataFrame:
    frame = _frame(dat)
    if cutoff == 1:
        return frame.filter(pl.sum_horizontal(pl.all().is_not_null()) > 0)
    return frame.filter(pl.sum_horizontal(pl.all().is_not_null()) / frame.width > cutoff)


def remove_empty(dat: pl.DataFrame, which: Sequence[str] = ("rows", "cols"),
                 cutoff: float = 1, quiet: bool = True) -> pl.DataFrame:
    frame = _frame(dat)
    if "rows" in which:
        frame = remove_empty_rows(frame, cutoff, quiet)
    if "cols" in which:
        frame = remove_empty_cols(frame, cutoff, quiet)
    return frame


def use_first_valid_of(*values: Any) -> Any:
    if len(values) == 1 and isinstance(values[0], (list, tuple, np.ndarray)):
        values = tuple(values[0])
    for value in values:
        if value is not None and not (isinstance(value, float) and math.isnan(value)):
            return value
    return None


def make_clean_names(string: Iterable[Any], case: str = "snake",
                     replace: dict[str, str] | None = None, ascii: bool = True,
                     use_make_names: bool = True, allow_dupes: bool = False,
                     **_: Any) -> list[str]:
    replacements = {"'": "", '"': "", "%": "_percent_", "#": "_number_"}
    if replace:
        replacements.update(replace)
    out: list[str] = []
    for raw in string:
        value = str(raw)
        for old, new in replacements.items():
            value = value.replace(old, new)
        if ascii:
            value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
        value = re.sub(r"^[\W_]+", "", value, flags=re.UNICODE)
        value = re.sub(r"[\W_]+", ".", value, flags=re.UNICODE)
        if use_make_names and value and value[0].isdigit():
            value = "X" + value
        if case in ("snake", "old_janitor"):
            value = re.sub(r"[.\s]+", "_", value).lower()
        elif case in ("lower", "small_camel"):
            value = value.lower()
        elif case in ("upper", "title"):
            value = value.title()
        out.append(value)
    if not allow_dupes:
        seen: Counter[str] = Counter()
        for i, value in enumerate(out):
            seen[value] += 1
            if seen[value] > 1:
                out[i] = f"{value}_{seen[value]}"
    return out


def remove_constant(dat: pl.DataFrame, na_rm: bool = False, quiet: bool = True) -> pl.DataFrame:
    frame = _frame(dat)
    keep = []
    for c in frame.columns:
        values = frame[c].drop_nulls().to_list() if na_rm else frame[c].to_list()
        keep.append(len({repr(v) for v in values}) > 1)
    return frame.select([c for c, ok in zip(frame.columns, keep) if ok])


__all__ = [name for name in globals() if not name.startswith("_")]
