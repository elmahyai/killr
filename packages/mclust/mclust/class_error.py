"""Classification error under a minimum-error label map (``classError``)."""

from __future__ import annotations

import warnings
from typing import Any, Mapping, Sequence

import numpy as np

__all__ = ["classError"]


def classError(classification: Sequence[Any], class_: Sequence[Any]) -> dict[str, Any]:
    """Minimum-error classification rate and misclassified indices (1-based)."""
    classification = _coerce_vector(classification)
    class_ = _coerce_vector(class_)
    n = len(classification)
    if n != len(class_):
        warnings.warn("unequal lengths", RuntimeWarning, stacklevel=2)
        return {"misclassified": [float("nan")] * n, "errorRate": float("nan")}

    if _any_na(classification):
        classification = list(classification)
        non_na = [c for c in classification if not _is_na(c)]
        nachar = "".join(_unique_preserve(_as_char(v) for v in non_na))
        classification = [nachar if _is_na(c) else c for c in classification]

    map_out = _map_class(classification, class_)
    if map_out is None:
        return {"misclassified": [float("nan")] * n, "errorRate": float("nan")}

    a_to_b, b_to_a = map_out
    lens = [len(v) for v in a_to_b.values()]
    if all(length == 1 for length in lens):
        c_to_t = _unlist_named(a_to_b)
        one = [
            _values_differ(c_to_t.get(_as_char(cl), None), tr)
            for cl, tr in zip(classification, class_)
        ]
    else:
        one = _best_error_map(a_to_b, lens, class_)

    lens = [len(v) for v in b_to_a.values()]
    if all(length == 1 for length in lens):
        t_to_c = _unlist_named(b_to_a)
        two = [
            _values_differ(t_to_c.get(_as_char(tr), None), cl)
            for tr, cl in zip(class_, classification)
        ]
    else:
        two = _best_error_map(b_to_a, lens, classification)

    err_one = sum(float(v) for v in one)
    err_two = sum(float(v) for v in two)
    err = one if err_one > err_two else two
    bad = [i + 1 for i, flag in enumerate(err) if flag]
    return {"misclassified": bad, "errorRate": len(bad) / n}


def _map_class(a: Sequence[Any], b: Sequence[Any]) -> tuple[dict[str, list[Any]], dict[str, list[Any]]] | None:
    if len(a) != len(b):
        return None

    if _is_r_factor(a) and _is_r_factor(b) and len(a.levels) == len(b.levels):  # type: ignore[attr-defined]
        a_levels = list(a.levels)  # type: ignore[attr-defined]
        b_levels = list(b.levels)  # type: ignore[attr-defined]
        a_to_b = {_as_char(a_levels[i]): [b_levels[i]] for i in range(len(a_levels))}
        b_to_a = {
            _as_char(b_levels[i]): [_coerce_level_value(_as_char(a_levels[i]), b)]
            for i in range(len(b_levels))
        }
        return a_to_b, b_to_a

    a_char = _is_character_vector(a)
    b_char = _is_character_vector(b)
    if a_char and b_char and len(_unique_preserve(a)) == len(_unique_preserve(b)):
        ua = [_as_char(v) for v in _unique_preserve(a)]
        ub = [_as_char(v) for v in _unique_preserve(b)]
        a_to_b = {ua[i]: [ub[i]] for i in range(len(ua))}
        b_to_a = {ub[i]: [_from_char(ua[i], b)] for i in range(len(ub))}
        return a_to_b, b_to_a

    tab, ua, ub = _cross_table(a, b)
    a_to_b: dict[str, list[Any]] = { _as_char(u): [] for u in ua }
    for i, row_name in enumerate(ua):
        row = tab[i, :]
        max_val = float(np.max(row))
        j = int(np.where(row == max_val)[0][0])
        target = ub[j]
        if _is_numeric_vector(b):
            a_to_b[_as_char(row_name)] = [_numeric_like(target, b)]
        else:
            a_to_b[_as_char(row_name)] = [_as_char(target)]

    b_to_a: dict[str, list[Any]] = { _as_char(u): [] for u in ub }
    for j, col_name in enumerate(ub):
        col = tab[:, j]
        max_val = float(np.max(col))
        i = int(np.where(col == max_val)[0][0])
        source = ua[i]
        if _is_numeric_vector(a):
            b_to_a[_as_char(col_name)] = [_numeric_like(source, a)]
        else:
            b_to_a[_as_char(col_name)] = [_as_char(source)]

    return a_to_b, b_to_a


def _best_error_map(
    map_dict: Mapping[str, Sequence[Any]],
    lengths: Sequence[int],
    x: Sequence[Any],
) -> list[bool]:
    x_char = [_as_char(v) for v in x]
    map_char: dict[str, list[str]] = {
        k: [_as_char(v) for v in vals] for k, vals in map_dict.items()
    }
    keys = list(map_char.keys())
    y = {k: map_char[k][0] for k in keys}
    best = [_values_differ(y.get(xc, None), xc) for xc in x_char]
    if all(length == 1 for length in lengths):
        return best

    errmin = sum(float(v) for v in best)
    z = {k: map_char[k][-1] for k in keys}
    mask = [length != 1 for length in lengths]
    counter = [0] * len(lengths)
    k = sum(mask)
    if k == 0:
        return best
    j = 0
    y_vec = [y.get(xc, None) for xc in x_char]
    z_vec = [z.get(xc, None) for xc in x_char]
    while y_vec != z_vec:
        i = k - j
        m = mask[i - 1] if i >= 1 else False
        if m:
            counter[i - 1] = (counter[i - 1] % lengths[i - 1]) + 1
            key = keys[i - 1]
            mapped = map_char[key][counter[i - 1] - 1]
            y_vec = [mapped if xc == key else val for xc, val in zip(x_char, y_vec)]
            temp = [_values_differ(mv, xc) for mv, xc in zip(y_vec, x_char)]
            err = sum(float(v) for v in temp)
            if err < errmin:
                errmin = err
                best = temp
        j = (j + 1) % k
    return best


def _cross_table(
    a: Sequence[Any], b: Sequence[Any]
) -> tuple[np.ndarray, list[Any], list[Any]]:
    a_vals = list(a)
    b_vals = list(b)
    if _is_r_factor(b):  # type: ignore[attr-defined]
        ub = list(b.levels)  # type: ignore[attr-defined]
    else:
        ub = _sorted_unique(b_vals)
    ua = _sorted_unique(a_vals)
    ua_index = {_canonical(u): i for i, u in enumerate(ua)}
    ub_index = {_canonical(u): j for j, u in enumerate(ub)}
    tab = np.zeros((len(ua), len(ub)), dtype=float)
    for av, bv in zip(a_vals, b_vals):
        i = ua_index[_canonical(av)]
        j = ub_index[_canonical(bv)]
        tab[i, j] += 1.0
    return tab, ua, ub


def _coerce_vector(values: Sequence[Any]) -> list[Any]:
    if _is_r_factor(values):
        return list(values.labels())  # type: ignore[attr-defined]
    arr = np.asarray(values, dtype=object).ravel()
    return arr.tolist()


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
    items = list(values)
    if not items:
        return False
    return all(isinstance(v, (int, np.integer, float, np.floating)) and not isinstance(v, (bool, np.bool_)) for v in items)


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
    if _is_na(value):
        return "NA"
    if isinstance(value, (float, np.floating)) and float(value).is_integer():
        return str(int(value))
    return str(value)


def _is_na(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, np.floating) and np.isnan(value):
        return True
    return False


def _any_na(values: Sequence[Any]) -> bool:
    return any(_is_na(v) for v in values)


def _unlist_named(mapping: Mapping[str, Sequence[Any]]) -> dict[str, Any]:
    return {k: vals[0] if len(vals) == 1 else list(vals) for k, vals in mapping.items()}


def _values_differ(mapped: Any, truth: Any) -> bool:
    if mapped is None:
        return True
    if isinstance(truth, (int, np.integer, float, np.floating)) and not isinstance(truth, (bool, np.bool_)):
        try:
            return float(mapped) != float(truth)
        except (TypeError, ValueError):
            pass
    return _as_char(mapped) != _as_char(truth)


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

