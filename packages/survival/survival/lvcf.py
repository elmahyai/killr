"""Last value carried forward by subject (survival::lvcf)."""

from __future__ import annotations

import math
from typing import Any

from survival.fromtimeline import Categorical
from survival.strata import StrataFactor


def _is_missing(item: Any) -> bool:
    if item is None:
        return True
    if isinstance(item, float) and math.isnan(item):
        return True
    return False


def _is_factor(x: Any) -> bool:
    return isinstance(x, (StrataFactor, Categorical))


def _as_mutable_list(x: Any) -> tuple[list[Any], str, Any]:
    """Return (values, kind, meta) where kind is atomic, strata, or categorical."""
    if isinstance(x, StrataFactor):
        return list(x.codes), "strata", x.levels
    if isinstance(x, Categorical):
        level_index = {level: code for code, level in enumerate(x.levels, start=1)}
        codes = []
        for value in x.values:
            if _is_missing(value):
                codes.append(None)
            else:
                codes.append(level_index.get(value))
        return codes, "categorical", (x.levels, list(x.values))
    if isinstance(x, list):
        return list(x), "atomic", None
    return list(x), "atomic", None


def _wrap_result(values: list[Any], kind: str, meta: Any) -> Any:
    if kind == "strata":
        return StrataFactor(values, meta)
    if kind == "categorical":
        levels, _orig = meta
        index_to_level = {code: level for code, level in enumerate(levels, start=1)}
        out_values = []
        for code in values:
            if code is None:
                out_values.append(None)
            else:
                out_values.append(index_to_level.get(code))
        return Categorical(out_values, levels)
    return values


def _is_logical_vector(values: list[Any]) -> bool:
    for item in values:
        if _is_missing(item):
            continue
        if not isinstance(item, bool):
            return False
    return True


def _is_zero_one_numeric(values: list[Any]) -> bool:
    for item in values:
        if _is_missing(item):
            continue
        if isinstance(item, bool):
            return False
        if not isinstance(item, (int, float)) or item not in (0, 1, 0.0, 1.0):
            return False
    return True


def lvcf(id, x, time=None, first=True):
    """Replace missing covariate values with the last non-missing value per id."""
    id_list = list(id)
    values, kind, meta = _as_mutable_list(x)
    n = len(values)
    if len(id_list) != n:
        raise ValueError("wrong length for x or id")

    if time is None:
        indx = sorted(range(n), key=lambda i: id_list[i])
    else:
        time_list = list(time)
        if len(time_list) != n:
            raise ValueError("wrong length for time")
        indx = sorted(range(n), key=lambda i: (id_list[i], time_list[i]))

    obs1: list[int] = []
    seen_ids: set[Any] = set()
    for j in indx:
        subj = id_list[j]
        if subj not in seen_ids:
            seen_ids.add(subj)
            obs1.append(j)

    if first and any(_is_missing(values[j]) for j in obs1):
        if _is_logical_vector(values):
            for j in obs1:
                if _is_missing(values[j]):
                    values[j] = False
        elif _is_zero_one_numeric(values):
            for j in obs1:
                if _is_missing(values[j]):
                    values[j] = 0

    jlag = indx[0]
    current = values[jlag]
    for i, j in enumerate(indx):
        if i == 0 or not _is_missing(values[j]) or id_list[j] != id_list[jlag]:
            current = values[j]
        else:
            values[j] = current
        jlag = j

    return _wrap_result(values, kind, meta)
