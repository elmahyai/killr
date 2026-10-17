"""Turn labelled vectors into factors."""

from __future__ import annotations

from haven.labelled import Vector, is_labelled
from haven.tagged import is_na_double, is_tagged_na, na_tag


def _match_arg(value: str) -> str:
    choices = ("default", "labels", "values", "both")
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) != 1:
        raise ValueError(f"`levels` must be one of {', '.join(choices)}")
    return hits[0]


def _sort_key(value):
    if value is None or is_na_double(value):
        return (1, 0, "")
    if isinstance(value, str):
        return (0, 0, value)
    return (0, float(value), "")


def as_factor(x, levels="default", ordered=False, only_labelled=True):
    """Convert labelled values to a factor. A data frame converts labelled columns."""
    if hasattr(x, "columns") and hasattr(x, "names"):
        converted = []
        for column in x.columns:
            if only_labelled and not is_labelled(column):
                converted.append(column)
            else:
                converted.append(as_factor(column, levels=levels, ordered=ordered))
        x.columns = converted
        return x
    if not isinstance(x, Vector):
        return x
    choice = _match_arg(levels)
    codes = [value for value, _name in x.labels]
    names = [name for _value, name in x.labels]
    data = list(x.values)
    if choice == "both":
        names = [f"[{_level_text(value)}] {name}" for value, name in zip(codes, names)]
    if choice in ("default", "both"):
        values, level_names = _default_levels(data, codes, names)
    elif choice == "labels":
        level_names = []
        for name in names:
            if name not in level_names:
                level_names.append(name)
        replaced = _replace_with(data, codes, names)
        values = []
        for original, item in zip(data, replaced):
            if _matched(original, codes):
                values.append(item if isinstance(item, str) else _level_text(item))
            else:
                values.append(None)
    else:
        if codes and all(_in(value, codes) for value in data):
            level_values = list(codes)
        else:
            level_values = sorted({value for value in data if not _missing(value)}, key=_sort_key)
        level_names = []
        for value in level_values:
            text = _level_text(value)
            if text is not None and text not in level_names:
                level_names.append(text)
        values = [None if _missing(value) else _level_text(value) for value in data]
    out = Vector(values, "string")
    out.levels = level_names
    out.ordered = ordered
    out.label = x.label
    out.class_ = ["ordered", "factor"] if ordered else ["factor"]
    return out


def _default_levels(data, codes, names):
    vals = []
    for value in data:
        if not any(_same(value, kept) for kept in vals):
            vals.append(value)
    levs = _replace_with(vals, codes, names)
    items = list(zip(levs, vals)) + list(zip(names, codes))
    items.sort(key=lambda pair: _sort_key(pair[1]))
    level_names = []
    for name, _value in items:
        text = name if isinstance(name, str) else _level_text(name)
        if text is not None and text not in level_names:
            level_names.append(text)
    replaced = _replace_with(data, codes, names)
    values = []
    for item in replaced:
        if _missing(item):
            values.append(None)
        elif isinstance(item, str):
            values.append(item)
        else:
            values.append(_level_text(item))
    return values, level_names


def _level_text(value):
    if value is None or is_na_double(value):
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    if isinstance(value, float):
        return format(value, ".15g")
    return str(value)


def _missing(value) -> bool:
    return value is None or is_na_double(value)


def _same(left, right) -> bool:
    if _missing(left) or _missing(right):
        if is_tagged_na([left])[0] or is_tagged_na([right])[0]:
            return na_tag([left])[0] == na_tag([right])[0] and is_tagged_na([left])[0] and is_tagged_na([right])[0]
        return _missing(left) and _missing(right)
    return left == right


def _matched(value, codes) -> bool:
    if is_tagged_na([value])[0]:
        return any(is_tagged_na([code])[0] and na_tag([code])[0] == na_tag([value])[0] for code in codes)
    if _missing(value):
        return False
    return any(not _missing(code) and value == code for code in codes)


def _identity(values):
    return list(values)


def _in(value, codes) -> bool:
    if is_na_double(value) or value is None:
        return any(is_na_double(code) or code is None for code in codes)
    return any(value == code for code in codes)


def _replace_with(values, sources, targets):
    out = list(values)
    tagged = is_tagged_na(values) if values and not isinstance(values[0], str) else [False] * len(values)
    for index, value in enumerate(values):
        if tagged[index]:
            continue
        for source, target in zip(sources, targets):
            if is_na_double(source) or source is None:
                continue
            if value == source:
                out[index] = target
                break
    if not any(tagged):
        return out
    value_tags = na_tag(values)
    source_tags = na_tag(sources) if sources else []
    for index, flag in enumerate(tagged):
        if not flag:
            continue
        for source_tag, target in zip(source_tags, targets):
            if source_tag is not None and source_tag == value_tags[index]:
                out[index] = target
                break
    return out
