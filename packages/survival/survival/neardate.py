"""Nearest date index within matching ids (survival::neardate)."""

from __future__ import annotations

import bisect
import math
from datetime import date, datetime
from typing import Any


def _is_factor_vector(x: Any) -> bool:
    return hasattr(x, "codes") and hasattr(x, "levels") and not isinstance(x, (str, bytes))


def _match_arg(value, choices):
    if isinstance(value, (list, tuple)) and list(value) == list(choices):
        return choices[0]
    text = value[0] if isinstance(value, (list, tuple)) else value
    if text in choices:
        return text
    hits = [c for c in choices if c.startswith(str(text))]
    if len(hits) == 1:
        return hits[0]
    raise ValueError(f"'{value}' should be one of {choices}")


def _as_list(x: Any) -> list[Any]:
    if isinstance(x, str):
        return [x]
    return list(x)


def _is_missing(item: Any) -> bool:
    if item is None:
        return True
    if isinstance(item, float) and math.isnan(item):
        return True
    return False


def _is_posix(x: Any) -> bool:
    return isinstance(x, (datetime, date))


def _coerce_posix_pair(y1: list[Any], y2: list[Any]) -> tuple[list[Any], list[Any]]:
    y1_posix = any(_is_posix(v) for v in y1 if not _is_missing(v))
    y2_posix = any(_is_posix(v) for v in y2 if not _is_missing(v))
    if y1_posix and not y2_posix:
        if any(isinstance(v, datetime) for v in y1 if not _is_missing(v)):
            y2 = [
                datetime(v.year, v.month, v.day) if isinstance(v, date) and not isinstance(v, datetime) else v
                for v in y2
            ]
        else:
            y2 = [v.date() if isinstance(v, datetime) else v for v in y2]
    elif y2_posix and not y1_posix:
        if any(isinstance(v, datetime) for v in y2 if not _is_missing(v)):
            y1 = [
                datetime(v.year, v.month, v.day) if isinstance(v, date) and not isinstance(v, datetime) else v
                for v in y1
            ]
        else:
            y1 = [v.date() if isinstance(v, datetime) else v for v in y1]
    return y1, y2


def _match(x: list[Any], table: list[Any]) -> list[int | None]:
    first: dict[Any, int] = {}
    for index, value in enumerate(table, start=1):
        if value not in first:
            first[value] = index
    return [None if _is_missing(value) else first.get(value) for value in x]


def _find_interval(values: list[float], vec: list[float], *, left_open: bool = False) -> list[int | None]:
    out: list[int | None] = []
    for value in values:
        if math.isnan(value):
            out.append(None)
            continue
        if left_open:
            out.append(bisect.bisect_left(vec, value))
        else:
            out.append(bisect.bisect_right(vec, value))
    return out


def neardate(
    id1,
    id2,
    y1,
    y2,
    best=("after", "prior"),
    nomatch=None,
):
    """Index in the reference set with the closest orderable value per id."""
    if id1 is None:
        raise ValueError("id1 argument is required")
    if id2 is None:
        raise ValueError("id2 argument is required")
    if y1 is None:
        raise ValueError("y1 argument is required")
    if y2 is None:
        raise ValueError("y2 argument is required")

    if _is_factor_vector(y1) or _is_factor_vector(y2):
        raise ValueError("y1 and y2 must be sortable")

    id1 = _as_list(id1)
    id2 = _as_list(id2)
    y1 = _as_list(y1)
    y2 = _as_list(y2)

    if len(id1) != len(y1):
        raise ValueError("id1 and y1 have different lengths")
    if len(id2) != len(y2):
        raise ValueError("id2 and y2 have different lengths")

    best = _match_arg(best, ("after", "prior"))

    y1, y2 = _coerce_posix_pair(y1, y2)

    alldate = sorted(set(y1) | set(y2), key=lambda item: (_is_missing(item), item))
    y1_codes = _match(y1, alldate)
    y2_codes = _match(y2, alldate)

    rowid = list(range(1, len(y2) + 1))
    if any(_is_missing(code) for code in y2_codes):
        keep = [not _is_missing(code) for code in y2_codes]
        y2_codes = [code for code, ok in zip(y2_codes, keep) if ok]
        id2 = [value for value, ok in zip(id2, keep) if ok]
        rowid = [value for value, ok in zip(rowid, keep) if ok]

    n2 = len(y2_codes)
    if n2 == 0:
        raise ValueError("No valid entries in data set 2")

    indx1 = _match(id2, id1)
    keep = [code is not None for code in indx1]
    if not all(keep):
        id2 = [value for value, ok in zip(id2, keep) if ok]
        y2_codes = [code for code, ok in zip(y2_codes, keep) if ok]
        indx1 = [code for code, ok in zip(indx1, keep) if ok]
        rowid = [value for value, ok in zip(rowid, keep) if ok]

    n2 = len(y2_codes)
    if n2 == 0:
        raise ValueError("No valid entries in data set 2")

    delta = 1.0 + len(alldate)
    hash1 = []
    for first, code in zip(_match(id1, id1), y1_codes):
        if first is None or code is None:
            hash1.append(float("nan"))
        else:
            hash1.append(float(first * delta + code))
    hash2 = [float(first * delta + code) for first, code in zip(indx1, y2_codes)]

    indx3 = sorted(range(n2), key=lambda i: hash2[i])
    sorted_hash2 = [hash2[i] for i in indx3]
    indx3_one = [i + 1 for i in indx3]

    if best == "prior":
        indx2_raw = _find_interval(hash1, sorted_hash2, left_open=False)
        indx2 = []
        for pos in indx2_raw:
            if pos is None or pos == 0:
                indx2.append(None)
            else:
                indx2.append(indx3_one[pos - 1])
    else:
        indx2_raw = _find_interval(hash1, sorted_hash2, left_open=True)
        pad = indx3_one + [0]
        indx2 = []
        for pos in indx2_raw:
            if pos is None or pos == n2:
                indx2.append(None)
            else:
                indx2.append(pad[pos])

    out: list[Any] = []
    for i, hit in enumerate(indx2):
        if hit is None:
            out.append(nomatch)
            continue
        pos = hit - 1
        if id1[i] == id2[pos]:
            out.append(rowid[pos])
        else:
            out.append(nomatch)
    return out
