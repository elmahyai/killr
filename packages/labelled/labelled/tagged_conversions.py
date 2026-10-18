"""Tagged-NA ordering and labelled coercion translations."""

from __future__ import annotations

import math

from .labelled import LabelledVector, TaggedNA


def _vals(x):
    return list(x.values) if isinstance(x, LabelledVector) else list(x)


def _tagged(v):
    return isinstance(v, TaggedNA)


def _same(a, b):
    if _tagged(a) or _tagged(b):
        return _tagged(a) and _tagged(b) and a.tag == b.tag
    if isinstance(a, float) and math.isnan(a):
        return isinstance(b, float) and math.isnan(b)
    return a == b


def duplicated_tagged_na(x, fromLast=False):
    out = [False] * len(_vals(x))
    seen = []
    indexes = range(len(out) - 1, -1, -1) if fromLast else range(len(out))
    values = _vals(x)
    for i in indexes:
        out[i] = any(_same(values[i], v) for v in seen)
        seen.append(values[i])
    return out


def unique_tagged_na(x, fromLast=False):
    values = _vals(x)
    keep = [not v for v in duplicated_tagged_na(values, fromLast)]
    result = [v for v, k in zip(values, keep) if k]
    return LabelledVector(result) if isinstance(x, LabelledVector) else result


def order_tagged_na(x, na_last=True, decreasing=False, method="auto",
                    na_decreasing=None, untagged_na_last=True):
    values = _vals(x)
    if na_decreasing is None:
        na_decreasing = decreasing
    regular = [i for i, v in enumerate(values) if not (_tagged(v) or v is None or (isinstance(v, float) and math.isnan(v)))]
    missing = [i for i in range(len(values)) if i not in regular]
    regular.sort(key=lambda i: values[i], reverse=decreasing)
    def key(i):
        v = values[i]
        if _tagged(v):
            return (0 if not untagged_na_last else 1, v.tag)
        return (1 if not untagged_na_last else 0, "")
    missing.sort(key=key, reverse=na_decreasing)
    return missing + regular if not na_last else regular + missing


def sort_tagged_na(x, decreasing=False, na_last=True, na_decreasing=None,
                   untagged_na_last=True):
    values = _vals(x)
    result = [values[i] for i in order_tagged_na(
        values, na_last, decreasing, na_decreasing=na_decreasing,
        untagged_na_last=untagged_na_last)]
    return LabelledVector(result) if isinstance(x, LabelledVector) else result


def tagged_na_to_regular_na(x):
    if not isinstance(x, LabelledVector):
        return [None if _tagged(v) else v for v in x]
    out = x.copy()
    out.values = [None if _tagged(v) else v for v in out.values]
    out.labels = {k: v for k, v in out.labels.items() if not _tagged(v)}
    return out


def tagged_na_to_user_na(x, user_na_start=None):
    if not isinstance(x, LabelledVector):
        return x
    out = x.copy()
    tags = []
    for v in out.values:
        if _tagged(v) and v.tag not in tags:
            tags.append(v.tag)
    if not tags:
        return out
    if user_na_start is None:
        observed = [v for v in out.values if isinstance(v, (int, float)) and not (isinstance(v, float) and math.isnan(v))]
        user_na_start = math.trunc(max(observed)) + 1 if observed else 1
    for offset, tag in enumerate(tags):
        value = user_na_start + offset
        if any(_same(v, value) for v in out.values):
            raise ValueError(f"Value {value} is already used in x.")
        out.values = [value if _tagged(v) and v.tag == tag else v for v in out.values]
        out.labels = {name: (value if _tagged(old) and old.tag == tag else old)
                      for name, old in out.labels.items()}
    out.na_range = [user_na_start, user_na_start + len(tags) - 1]
    return out


def update_labelled(x):
    if isinstance(x, dict):
        return {key: update_labelled(value) for key, value in x.items()}
    return x.copy() if isinstance(x, LabelledVector) else x


def to_character(x, levels="labels", **kwargs):
    if isinstance(x, LabelledVector):
        labels = x.labels
        return [next((name for name, code in labels.items() if _same(code, value)),
                     str(value) if value is not None else None) for value in x.values]
    return [str(v) if v is not None else None for v in x]


def to_factor(x, **kwargs):
    if not isinstance(x, LabelledVector):
        return x
    result = LabelledVector(to_character(x, **kwargs))
    result.attributes["levels"] = list(dict.fromkeys(result.values))
    result.attributes["class"] = "factor"
    return result


def unlabelled(x, **kwargs):
    return to_factor(x, **kwargs) if isinstance(x, LabelledVector) else x


def foreign_to_labelled(x):
    return x


def memisc_to_labelled(x):
    raise ImportError("memisc is required to convert a data.set.")


def to_labelled(x, **kwargs):
    if isinstance(x, LabelledVector):
        return x
    if hasattr(x, "values") and hasattr(x, "attributes"):
        return LabelledVector(list(x.values))
    return foreign_to_labelled(x)
