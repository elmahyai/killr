"""Best matching between two label vectors (``mapClass``)."""

from __future__ import annotations

import warnings
from typing import Any, Sequence

import numpy as np

__all__ = ["mapClass"]


def mapClass(a: Sequence[Any], b: Sequence[Any]) -> dict[str, dict[str, list[Any]]]:
    """Map levels of ``a`` to levels of ``b`` by agreement or cross-tabulation."""
    a_vals = _coerce_vector(a)
    b_vals = _coerce_vector(b)
    if len(a_vals) != len(b_vals):
        warnings.warn("unequal lengths", RuntimeWarning, stacklevel=2)
        na = float("nan")
        return {"aTOb": {str(na): [na]}, "bTOa": {str(na): [na]}}

    if _is_r_factor(a) and _is_r_factor(b) and len(a.levels) == len(b.levels):  # type: ignore[attr-defined]
        a_levels = list(a.levels)  # type: ignore[attr-defined]
        b_levels = list(b.levels)  # type: ignore[attr-defined]
        a_to_b = {_as_char(a_levels[i]): [b_levels[i]] for i in range(len(a_levels))}
        b_to_a = {
            _as_char(b_levels[i]): [_coerce_level_value(_as_char(a_levels[i]), b_vals)]
            for i in range(len(b_levels))
        }
        return {"aTOb": a_to_b, "bTOa": b_to_a}

    if _is_character_vector(a_vals) and _is_character_vector(b_vals):
        ua = _unique_preserve(a_vals)
        ub = _unique_preserve(b_vals)
        if len(ua) == len(ub):
            ua_s = [_as_char(v) for v in ua]
            ub_s = [_as_char(v) for v in ub]
            a_to_b = {ua_s[i]: [ub[i]] for i in range(len(ua_s))}
            b_to_a = {ub_s[i]: [_from_char(ua_s[i], b_vals)] for i in range(len(ub_s))}
            return {"aTOb": a_to_b, "bTOa": b_to_a}

    tab, ua, ub = _cross_table(a_vals, b_vals)
    a_to_b: dict[str, list[Any]] = {_as_char(u): [] for u in ua}
    for i, row_name in enumerate(ua):
        row = tab[i, :]
        max_val = float(np.max(row))
        j = int(np.where(row == max_val)[0][0])
        target = ub[j]
        if _is_numeric_vector(b_vals):
            a_to_b[_as_char(row_name)] = [_numeric_like(target, b_vals)]
        else:
            a_to_b[_as_char(row_name)] = [_as_char(target)]

    b_to_a: dict[str, list[Any]] = {_as_char(u): [] for u in ub}
    for j, col_name in enumerate(ub):
        col = tab[:, j]
        max_val = float(np.max(col))
        i = int(np.where(col == max_val)[0][0])
        source = ua[i]
        if _is_numeric_vector(a_vals):
            b_to_a[_as_char(col_name)] = [_numeric_like(source, a_vals)]
        else:
            b_to_a[_as_char(col_name)] = [_as_char(source)]

    return {"aTOb": a_to_b, "bTOa": b_to_a}


def _cross_table(
    a: Sequence[Any], b: Sequence[Any]
) -> tuple[np.ndarray, list[Any], list[Any]]:
    if _is_r_factor(b):  # type: ignore[arg-type]
        ub = list(b.levels)  # type: ignore[attr-defined]
    else:
        ub = _sorted_unique(b)
    ua = _sorted_unique(a)
    ua_index = {_canonical(u): i for i, u in enumerate(ua)}
    ub_index = {_canonical(u): j for j, u in enumerate(ub)}
    tab = np.zeros((len(ua), len(ub)), dtype=float)
    for av, bv in zip(a, b):
        i = ua_index[_canonical(av)]
        j = ub_index[_canonical(bv)]
        tab[i, j] += 1.0
    return tab, ua, ub


def _coerce_vector(values: Sequence[Any]) -> list[Any]:
    if _is_r_factor(values):
        return list(values.labels())  # type: ignore[attr-defined]
    return np.asarray(values, dtype=object).ravel().tolist()


def _is_r_factor(obj: Any) -> bool:
    return hasattr(obj, "levels") and hasattr(obj, "codes") and not isinstance(obj, (str, bytes))


def _is_character_vector(values: Sequence[Any]) -> bool:
    if _is_r_factor(values):
        return True
    items = list(values)
    if not items:
        return True
    return all(isinstance(v, (str, np.str_)) for v in items)


def _is_numeric_vector(values: Sequence[Any]) -> bool:
    if not values:
        return False
    return all(
        isinstance(v, (int, np.integer, float, np.floating)) and not isinstance(v, (bool, np.bool_))
        for v in values
    )


def _sorted_unique(values: Sequence[Any]) -> list[Any]:
    seen: dict[tuple[str, Any], Any] = {}
    for item in values:
        key = _canonical(item)
        if key not in seen:
            seen[key] = item
    items = list(seen.values())
    if items and all(_canonical(v)[0] == "num" for v in items):
        return sorted(items, key=lambda v: _canonical(v)[1])
    if items and all(isinstance(v, (str, np.str_)) for v in items):
        return sorted(items, key=str)
    return sorted(items, key=lambda v: (_canonical(v)[0], _canonical(v)[1]))


def _unique_preserve(values: Sequence[Any]) -> list[Any]:
    seen: set[tuple[str, Any]] = set()
    out: list[Any] = []
    for item in values:
        key = _canonical(item)
        if key not in seen:
            seen.add(key)
            out.append(item)
    return out


def _canonical(value: Any) -> tuple[str, Any]:
    if isinstance(value, (str, np.str_)):
        return ("str", str(value))
    if isinstance(value, (bool, np.bool_)):
        return ("bool", bool(value))
    if isinstance(value, (int, np.integer, float, np.floating)):
        return ("num", float(value))
    return ("str", str(value))


def _as_char(value: Any) -> str:
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _numeric_like(value: Any, template: Sequence[Any]) -> Any:
    if _is_numeric_vector(template):
        if isinstance(value, (str, np.str_)):
            text = str(value)
            if text.isdigit() or (text.startswith("-") and text[1:].isdigit()):
                return int(text)
            return float(text)
        if isinstance(value, (int, np.integer)):
            return int(value)
        if isinstance(value, (float, np.floating)):
            return float(value)
    return value


def _from_char(text: str, template: Sequence[Any]) -> Any:
    if _is_numeric_vector(template):
        return _numeric_like(text, template)
    return text


def _coerce_level_value(level: str, template: Sequence[Any]) -> Any:
    if _is_numeric_vector(template):
        return _numeric_like(level, template)
    return level
