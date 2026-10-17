"""Deprecated ratetable() model terms (survival::ratetable)."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any

import numpy as np

from survival.fromtimeline import Categorical
from survival.ratetable_date import RtableDate, ratetableDate


class Ratetable2:
    """Matrix of ratetable dimensions (R class ``ratetable2``)."""

    __slots__ = ("values", "colnames", "is_date", "levlist")

    class_ = "ratetable2"

    def __init__(
        self,
        values: np.ndarray,
        colnames: list[str],
        is_date: list[bool],
        levlist: list[list[str] | None],
    ) -> None:
        self.values = np.asarray(values, dtype=float)
        self.colnames = list(colnames)
        self.is_date = list(is_date)
        self.levlist = list(levlist)


def _datecheck(x: Any) -> bool:
    if isinstance(x, (date, datetime)):
        return True
    if isinstance(x, (list, tuple)) and x:
        return _datecheck(x[0])
    if isinstance(x, np.ndarray):
        if x.dtype.kind == "M":
            return True
        if x.size and isinstance(x.reshape(-1)[0], (date, datetime)):
            return True
    label = getattr(x, "class_", None)
    if label is None and hasattr(x, "__class__"):
        name = x.__class__.__name__
        if name in ("Date", "POSIXct", "POSIXlt"):
            return True
    if isinstance(label, str):
        base = label.split(".")[0]
        return base in ("Date", "POSIXt", "date", "chron", "dates")
    if isinstance(label, (list, tuple)):
        tags = {str(item).split(".")[0] for item in label}
        return bool(tags & {"Date", "POSIXt", "date", "chron", "dates"})
    return False


def _arg_length(x: Any) -> int:
    if isinstance(x, (str, bytes)):
        return 1
    if isinstance(x, np.ndarray):
        return 0 if x.size == 0 else int(x.reshape(-1).size)
    if isinstance(x, Categorical):
        return len(x.values)
    if isinstance(x, (list, tuple)):
        return len(x)
    return 1


def _inherits_category(x: Any) -> bool:
    label = getattr(x, "class_", None)
    if label is None:
        return False
    if isinstance(label, str):
        return label in ("cateogory", "category")
    if isinstance(label, (list, tuple)):
        return any(str(item) in ("cateogory", "category") for item in label)
    return False


def _is_factor(x: Any) -> bool:
    if isinstance(x, Categorical):
        return True
    label = getattr(x, "class_", None)
    return label == "factor"


def _as_factor(x: Any) -> Categorical:
    if isinstance(x, Categorical):
        return x
    if isinstance(x, str):
        return Categorical([x], [x])
    if isinstance(x, np.ndarray) and x.dtype.kind in ("U", "S", "O"):
        values = x.tolist()
    elif isinstance(x, (list, tuple)):
        values = list(x)
    else:
        values = [x]
    levels = sorted({str(v) for v in values})
    return Categorical([str(v) for v in values], levels)


def _factor_codes(x: Categorical) -> np.ndarray:
    index = {level: code for code, level in enumerate(x.levels, start=1)}
    return np.asarray([index[value] for value in x.values], dtype=float)


def _numeric_column(x: Any) -> np.ndarray:
    converted = ratetableDate(x)
    if isinstance(converted, RtableDate):
        return np.asarray(converted.values, dtype=float).reshape(-1)
    if isinstance(converted, np.ndarray):
        return np.asarray(converted, dtype=float).reshape(-1)
    return np.asarray([float(converted)], dtype=float)


def ratetable(**kwargs: Any) -> Ratetable2:
    """Build a ratetable2 matrix from named dimension columns."""
    if not kwargs:
        return Ratetable2(np.zeros((0, 0), dtype=float), [], [], [])

    names = list(kwargs.keys())
    args = list(kwargs.values())
    nargs = len(args)
    lengths = [_arg_length(arg) for arg in args]
    n = max(lengths)

    is_date = [_datecheck(arg) for arg in args]
    levlist: list[list[str] | None] = [None] * nargs
    matrix = np.zeros((n, nargs), dtype=float)

    for i, arg in enumerate(args):
        length = lengths[i]
        if length == 1:
            if _is_factor(arg) or isinstance(arg, (str, bytes)) or _inherits_category(arg):
                if isinstance(arg, str):
                    work: Any = [arg] * n
                elif isinstance(arg, Categorical):
                    work = Categorical([arg.values[0]] * n, arg.levels)
                else:
                    work = [arg] * n
            elif isinstance(arg, np.ndarray) and arg.size == 1:
                work = np.full(n, arg.reshape(-1)[0])
            elif isinstance(arg, (list, tuple)) and len(arg) == 1:
                work = list(arg) * n
            else:
                work = [arg] * n
        elif length != n:
            raise ValueError(f"Aguments do not all have the same length (arg {i + 1})")
        else:
            work = arg

        if _inherits_category(work) or isinstance(work, (str, bytes)):
            work = _as_factor(work)
        elif isinstance(work, (list, tuple)) and work and all(isinstance(v, str) for v in work):
            work = _as_factor(work)
        elif isinstance(work, np.ndarray) and work.size and work.dtype.kind in ("U", "S", "O"):
            work = _as_factor(work)

        if _is_factor(work):
            cat = work if isinstance(work, Categorical) else _as_factor(work)
            levlist[i] = list(cat.levels)
            matrix[:, i] = _factor_codes(cat)
        else:
            matrix[:, i] = _numeric_column(work)

    return Ratetable2(matrix, names, is_date, levlist)
