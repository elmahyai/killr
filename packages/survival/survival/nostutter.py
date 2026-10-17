"""Remove repeated state visits (survival::nostutter)."""

from __future__ import annotations

import math
from typing import Any

from survival.fromtimeline import Categorical
from survival.strata import StrataFactor, _as_factor


def _is_missing(item: Any) -> bool:
    if item is None:
        return True
    if isinstance(item, float) and math.isnan(item):
        return True
    return False


def _level_text(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if value == int(value):
            return str(int(value))
        return str(value)
    return str(value)


def _censor_matches(label: str | None, censor: Any) -> bool:
    if label is None:
        return False
    return label == _level_text(censor)


def _newlev(censor: Any, levels: list[str]) -> list[str]:
    """``unique(c(censor, levels(x)))`` with R-style coercion."""
    out: list[str] = []
    seen: set[str] = set()
    for item in [censor, *levels]:
        text = _level_text(item)
        if text not in seen:
            seen.add(text)
            out.append(text)
    return out


def _code_to_label(code: int, sorted_codes: list[int], labels: list[str]) -> str:
    index = sorted_codes.index(code)
    return labels[index]


def nostutter(id, x, censor=0, single=False):
    """Mark consecutive identical states per subject as censored."""
    id_list = list(id)
    if isinstance(x, Categorical):
        fact = _as_factor_from_categorical(x)
    elif isinstance(x, StrataFactor):
        fact = x
    elif isinstance(x, (str, int, float, list, tuple)):
        fact = _as_factor(x)
    else:
        try:
            fact = _as_factor(x)
        except TypeError as exc:
            raise TypeError("invalid variable type") from exc

    orig_levels = list(fact.levels)
    label_for_code = {code: level for code, level in enumerate(orig_levels, start=1)}
    newlev = _newlev(censor, orig_levels)

    codes: list[int | None] = []
    for code in fact.codes:
        if code is None:
            codes.append(None)
            continue
        label = label_for_code.get(code)
        if _censor_matches(label, censor):
            codes.append(0)
        else:
            codes.append(int(code))

    n = len(codes)
    if len(id_list) != n:
        raise ValueError("wrong length for x or id")

    if single:
        used = [False] * (1 + len(orig_levels))
        for i in range(n):
            idx = i + 1
            if idx == 1 or (
                id_list[i] != id_list[i - 1]
                and (codes[i] is None or not used[codes[i]])
            ):
                if codes[i] is None:
                    current = 0
                else:
                    current = codes[i]
                    used[codes[i]] = True
            elif codes[i] is not None:
                if codes[i] == current:
                    codes[i] = 0
                elif codes[i] > 0:
                    current = codes[i]
    else:
        current = 0
        for i in range(n):
            if i == 0 or id_list[i] != id_list[i - 1]:
                if codes[i] is None:
                    current = 0
                else:
                    current = codes[i]
            elif codes[i] is not None:
                if codes[i] == current:
                    codes[i] = 0
                elif codes[i] > 0:
                    current = codes[i]

    observed = sorted({code for code in codes if code is not None})

    out_values: list[Any] = []
    for code in codes:
        if code is None:
            out_values.append(None)
        else:
            out_values.append(_code_to_label(code, observed, newlev))

    return Categorical(out_values, newlev)


def _as_factor_from_categorical(x: Categorical) -> StrataFactor:
    level_index = {level: code for code, level in enumerate(x.levels, start=1)}
    codes: list[int | None] = []
    for value in x.values:
        if _is_missing(value):
            codes.append(None)
        else:
            codes.append(level_index.get(str(value)))
    return StrataFactor(codes, list(x.levels))
