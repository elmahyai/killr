"""Helpers for ``xalign``, ``xdigits``, and ``xdisplay`` on tabular data."""

from __future__ import annotations

import math
from typing import Any

from xtable.caption_replacement import Xtable


class RMatrix:
    """Minimal 2-D matrix wrapper (``length(dim(x)) == 2``)."""

    __slots__ = ("data", "nrow", "ncol")

    def __init__(self, data: list[list[Any]], nrow: int, ncol: int) -> None:
        self.data = data
        self.nrow = nrow
        self.ncol = ncol


def r_length_dim(x: object) -> int:
    if isinstance(x, (Xtable, RMatrix)):
        return 2
    return 0


def as_data_frame_columns(x: object) -> list[list[Any]]:
    if isinstance(x, Xtable):
        if x.ncol == 0:
            return []
        return [x.column(j) for j in range(1, x.ncol + 1)]
    if isinstance(x, RMatrix):
        cols = [[] for _ in range(x.ncol)]
        for r in range(x.nrow):
            for c in range(x.ncol):
                cols[c].append(x.data[r][c])
        return cols
    if isinstance(x, (list, tuple)):
        seq = list(x)
        if not seq:
            return [[]]
        return [seq]
    return [[x]]


def is_numeric_vector(values: list[Any]) -> bool:
    if not values:
        return True
    for item in values:
        if isinstance(item, bool):
            return False
        if isinstance(item, (int, float)) and not isinstance(item, bool):
            continue
        return False
    return True


def r_zapsmall(values: list[float], digits: int) -> list[float]:
    """``base::zapsmall`` (R 4.x rounds by magnitude)."""
    if not values:
        return []
    finite = [v for v in values if v == v]
    if not finite:
        return list(values)
    mx = max(abs(v) for v in finite)
    if mx == 0:
        places = digits
    else:
        places = max(0, int(round(digits - math.log10(mx))))
    out: list[float] = []
    for v in values:
        if v != v:
            out.append(v)
        else:
            out.append(float(round(v, places)))
    return out


def _r_as_character_number(value: float) -> str:
    if value != value:
        return "NA"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        value = 0.0
    if math.isfinite(value) and value == math.trunc(value):
        return "0" if value == 0 else str(int(value))
    return format(value, ".15g")


def r_nchar(value: float) -> int:
    return len(_r_as_character_number(float(value)))
