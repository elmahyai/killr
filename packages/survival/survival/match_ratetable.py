"""Align subject data with a ratetable (survival::match.ratetable)."""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, Mapping, Sequence

import numpy as np

from survival.fromtimeline import Categorical
from survival.is_ratetable import is_ratetable


class _RtableDate:
    """Numeric day vector tagged like R's rtabledate class."""

    __slots__ = ("values",)

    class_ = "rtabledate"

    def __init__(self, values):
        self.values = np.asarray(values, dtype=float)


def _datecheck(x: Any) -> bool:
    if isinstance(x, (_RtableDate, date, datetime)):
        return True
    if isinstance(x, np.ndarray):
        return x.dtype.kind == "M"
    if isinstance(x, (list, tuple)) and x:
        return isinstance(x[0], (date, datetime, _RtableDate))
    return getattr(x, "class_", None) in ("Date", "POSIXt", "date", "chron", "rtabledate")


def _casefold(text: Any) -> str:
    return str(text).casefold()


def _charmatch(needles: Sequence[str], haystack: Sequence[str]) -> list[int | float]:
    folded_h = [_casefold(h) for h in haystack]
    out: list[int | float] = []
    for needle in needles:
        fn = _casefold(needle)
        hits = [j + 1 for j, h in enumerate(folded_h) if h == fn]
        if not hits:
            out.append(math.nan)
        elif len(hits) > 1:
            out.append(0)
        else:
            out.append(hits[0])
    return out


def _rtfun(x) -> _RtableDate:
    return _RtableDate(np.asarray(x, dtype=float).reshape(-1))


def _ratetable_date(x: Any) -> Any:
    if isinstance(x, _RtableDate):
        return x
    if isinstance(x, date) and not isinstance(x, datetime):
        return _rtfun(x.toordinal() + 719163)
    if isinstance(x, datetime):
        return _rtfun(x.date().toordinal() + 719163)
    if isinstance(x, np.ndarray):
        if x.dtype.kind == "M":
            days = (x.astype("datetime64[D]").astype(np.int64) - np.datetime64("1970-01-01", "D")).astype(float)
            return _rtfun(days)
        if np.issubdtype(x.dtype, np.integer):
            return _rtfun(x.astype(float) - 3653)
        return x
    if isinstance(x, (list, tuple)):
        if not x:
            return x
        if isinstance(x[0], (date, datetime)):
            vals = []
            for item in x:
                if isinstance(item, datetime):
                    d = item.date()
                else:
                    d = item
                vals.append(d.toordinal() + 719163)
            return _rtfun(vals)
        return np.asarray(x, dtype=float)
    return x


def _unclass_column(col: Any) -> np.ndarray:
    if isinstance(col, Categorical):
        raise TypeError("expected numeric column")
    if isinstance(col, np.ndarray):
        return np.asarray(col, dtype=float)
    if isinstance(col, (list, tuple)):
        return np.asarray(col, dtype=float)
    if hasattr(col, "__len__") and not isinstance(col, (str, bytes)):
        return np.asarray(list(col), dtype=float)
    return np.asarray(col, dtype=float)


def _levels_for_column(col: Any) -> list[str]:
    if isinstance(col, Categorical):
        return [str(v) for v in col.levels]
    return []


def _factor_codes(col: Categorical, level_map: Sequence[int | float]) -> np.ndarray:
    codes = []
    for value in col.values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            codes.append(np.nan)
            continue
        idx = col.levels.index(value)
        codes.append(float(level_map[idx]))
    return np.asarray(codes, dtype=float)


def match_ratetable(R: Any, ratetable: Mapping[str, Any]) -> dict[str, Any]:
    """Map data columns onto ratetable dimensions and return an index matrix."""
    if not is_ratetable(ratetable):
        raise ValueError("Invalid rate table")

    dimid = list(ratetable.get("dimnames_names") or ratetable.get("dimid") or [])
    cutpoints_raw = ratetable["cutpoints"]
    datecut = [_datecheck(cp) for cp in cutpoints_raw]

    rtype = ratetable.get("type")
    if rtype is None:
        temp = ratetable["factor"]
        rtype = []
        for f, is_dt in zip(temp, datecut):
            if f == 1:
                rtype.append(1)
            elif f > 1:
                rtype.append(4)
            elif is_dt:
                rtype.append(3)
            else:
                rtype.append(2)

    matrix_mode = isinstance(R, np.ndarray) and R.ndim == 2
    if matrix_mode:
        att = getattr(R, "_match_ratetable_attrs", None)
        if att is None:
            raise ValueError("matrix R requires _match_ratetable_attrs")
        rnames = list(att["dimnames"][1])
        is_date = list(att["isDate"])
        levlist = list(att["levlist"])
        rcols = [R[:, j] for j in range(R.shape[1])]
    elif isinstance(R, Mapping):
        rnames = list(R.keys())
        levlist = [_levels_for_column(R[k]) for k in rnames]
        is_date = [_datecheck(R[k]) for k in rnames]
        rcols = [R[k] for k in rnames]
    else:
        raise TypeError("R must be a mapping of columns or a matrix")

    ord_idx = []
    for name in dimid:
        try:
            ord_idx.append(rnames.index(name))
        except ValueError:
            ord_idx.append(-1)
    if any(i < 0 for i in ord_idx):
        missing = dimid[next(i for i, v in enumerate(ord_idx) if v < 0)]
        raise ValueError(f"Argument '{missing}' needed by the ratetable was not found in the data")
    if len(set(ord_idx)) != len(ord_idx):
        raise ValueError("A ratetable argument appears twice in the data")

    rcols = [rcols[i] for i in ord_idx]
    levlist = [levlist[i] for i in ord_idx]
    is_date = [is_date[i] for i in ord_idx]

    dtemp = ratetable["dimnames"]

    if any(rt < 3 and idt for rt, idt in zip(rtype, is_date)):
        indx = [dimid[i] for i, (rt, idt) in enumerate(zip(rtype, is_date)) if rt < 3 and idt]
        raise ValueError(
            "Data has a date type variable, but the reference ratetable is not a date variable: "
            + " ".join(indx)
        )

    out_cols = []
    for i, col in enumerate(rcols):
        work = col
        if rtype[i] > 2:
            converted = _ratetable_date(work)
            if isinstance(converted, _RtableDate):
                work = converted.values
            elif isinstance(converted, np.ndarray):
                work = converted
            else:
                work = np.asarray(converted, dtype=float)

        if len(levlist[i]) > 0:
            if rtype[i] != 1:
                raise ValueError(f"for this ratetable, {dimid[i]} must be a continuous variable")
            temp = _charmatch(levlist[i], dtemp[i])
            if any(math.isnan(v) for v in temp):
                raise ValueError(f"Levels do not match for ratetable() variable {dimid[i]}")
            if any(v == 0 for v in temp):
                raise ValueError(f"Non-unique ratetable match for variable {dimid[i]}")
            if isinstance(col, Categorical):
                out_cols.append(_factor_codes(col, temp))
            else:
                raise ValueError(f"Levels do not match for ratetable() variable {dimid[i]}")
        else:
            arr = _unclass_column(work)
            if rtype[i] == 1:
                if np.any(np.floor(arr) != arr) or np.any(arr <= 0) or np.max(arr) > len(dtemp[i]):
                    raise ValueError(f"The variable {dimid[i]} is out of range")
            out_cols.append(arr)

    mat = np.column_stack(out_cols)
    cutpoints = [_ratetable_date(cp) for cp in cutpoints_raw]
    cutpoints_out = []
    for cp in cutpoints:
        if isinstance(cp, _RtableDate):
            cutpoints_out.append(cp.values)
        else:
            cutpoints_out.append(cp)

    summ = ratetable.get("summary")
    out: dict[str, Any] = {"R": mat, "cutpoints": cutpoints_out}
    if summ is not None:
        out["summ"] = summ(mat)
    return out
