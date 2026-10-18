"""Translations for labelled's tagged-NA and coercion helpers."""

from __future__ import annotations

import math
import re
from collections import OrderedDict

from haven.factor import as_factor
from haven.labelled import Vector, labelled, labelled_spss
from haven.tagged import (
    format_tagged_na,
    is_na_double,
    is_tagged_na,
    na_real,
    na_tag,
)


def _values(x):
    return list(x.values) if isinstance(x, Vector) else list(x)


def _copy(x):
    return x.copy() if isinstance(x, Vector) else list(x)


def _same(a, b):
    if is_na_double(a) or a is None:
        return (is_na_double(b) or b is None) and (
            not is_tagged_na([a])[0] or not is_tagged_na([b])[0]
        )
    return a == b


def duplicated_tagged_na(x, fromLast=False):
    values = _values(x)
    result = [False] * len(values)
    seen = set()
    indices = range(len(values) - 1, -1, -1) if fromLast else range(len(values))
    for i in indices:
        v = values[i]
        if is_tagged_na([v])[0]:
            key = ("tag", na_tag([v])[0])
        elif is_na_double(v) or v is None:
            key = ("na",)
        else:
            key = ("value", v)
        result[i] = key in seen
        seen.add(key)
    return result


def unique_tagged_na(x, fromLast=False):
    values = _values(x)
    keep = [not flag for flag in duplicated_tagged_na(values, fromLast)]
    out = [v for v, flag in zip(values, keep) if flag]
    if isinstance(x, Vector):
        return x[ [i for i, flag in enumerate(keep) if flag] ]
    return out


def _order_key(v, decreasing=False):
    if is_tagged_na([v])[0]:
        return (2, na_tag([v])[0] or "")
    if is_na_double(v) or v is None:
        return (3, "")
    return (0, v)


def order_tagged_na(x, na_last=True, decreasing=False, method="auto",
                    na_decreasing=None, untagged_na_last=True):
    values = _values(x)
    if na_decreasing is None:
        na_decreasing = decreasing
    present = [i for i, v in enumerate(values) if not (is_na_double(v) or v is None)]
    missing = [i for i, v in enumerate(values) if is_na_double(v) or v is None]
    present.sort(key=lambda i: values[i], reverse=decreasing)
    def missing_key(i):
        v = values[i]
        tagged = is_tagged_na([v])[0]
        # R orders tags lexically, and places ordinary NA according to options.
        if tagged:
            return (1 if untagged_na_last else 0, na_tag([v])[0] or "")
        return (0 if untagged_na_last else 1, "")
    missing.sort(key=missing_key, reverse=na_decreasing)
    return (missing + present) if not na_last else (present + missing)


def sort_tagged_na(x, decreasing=False, na_last=True, na_decreasing=None,
                   untagged_na_last=True):
    idx = order_tagged_na(x, na_last, decreasing, na_decreasing=na_decreasing,
                          untagged_na_last=untagged_na_last)
    if isinstance(x, Vector):
        return x[idx]
    return [_values(x)[i] for i in idx]


def tagged_na_to_regular_na(x):
    if isinstance(x, dict):
        return {k: tagged_na_to_regular_na(v) for k, v in x.items()}
    if isinstance(x, Vector):
        out = x.copy()
        out.values = [na_real() if is_tagged_na([v])[0] else v for v in out.values]
        out.labels = [(v, n) for v, n in out.labels if not is_tagged_na([v])[0]]
        return out
    return [na_real() if is_tagged_na([v])[0] else v for v in x]


def tagged_na_to_user_na(x, user_na_start=None):
    if isinstance(x, dict):
        return {k: tagged_na_to_user_na(v, user_na_start) for k, v in x.items()}
    if not isinstance(x, Vector):
        return x
    out = x.copy()
    tags = []
    for v in out.values:
        if is_tagged_na([v])[0] and na_tag([v])[0] not in tags:
            tags.append(na_tag([v])[0])
    if not tags:
        return out
    if user_na_start is None:
        observed = [v for v in out.values if not is_na_double(v) and v is not None]
        user_na_start = math.trunc(max(observed)) + 1 if observed else 1
    for j, tag in enumerate(tags):
        new = user_na_start + j
        if any(_same(v, new) for v in out.values):
            raise ValueError(f"Value {new} is already used in x.")
        out.values = [new if is_tagged_na([v], tag)[0] else v for v in out.values]
        replaced = False
        labels = []
        for value, name in out.labels:
            if is_tagged_na([value], tag)[0]:
                labels.append((new, name)); replaced = True
            else:
                labels.append((value, name))
        if not replaced:
            labels.append((new, f"NA({tag})"))
        out.labels = labels
    out.na_range = [user_na_start, user_na_start + len(tags) - 1]
    return out


def to_factor(x, levels="labels", ordered=False, nolabel_to_na=False,
              sort_levels="auto", decreasing=False, drop_unused_labels=False,
              user_na_to_na=False, strict=False, unclass=False,
              explicit_tagged_na=False, labelled_only=True, **kwargs):
    if isinstance(x, dict):
        return {k: to_factor(v, levels, ordered, nolabel_to_na, sort_levels,
                            decreasing, drop_unused_labels, user_na_to_na,
                            strict, unclass, explicit_tagged_na, labelled_only)
                if isinstance(v, Vector) or not labelled_only else v
                for k, v in x.items()}
    if not isinstance(x, Vector) or "haven_labelled" not in x.class_:
        return as_factor(x) if not labelled_only and not isinstance(x, Vector) else x
    out = x.copy()
    data = list(out.values)
    labels = list(out.labels)
    if user_na_to_na and out.na_values:
        data = [na_real() if v in out.na_values else v for v in data]
    if explicit_tagged_na:
        labels = [(format_tagged_na([v])[0] if is_tagged_na([v])[0] else v, n)
                  for v, n in labels]
    else:
        labels = [(v, n) for v, n in labels if not is_na_double(v)]
    observed = []
    for v in data:
        if not (is_na_double(v) or v is None) and not any(_same(v, z) for z in observed):
            observed.append(v)
    known = [v for v, _ in labels]
    missing = [v for v in observed if not any(_same(v, z) for z in known)]
    if strict and missing:
        return list(data) if unclass else x
    if nolabel_to_na:
        data = [na_real() if any(_same(v, z) for z in missing) else v for v in data]
        missing = []
    pairs = labels + [(v, str(v) if not isinstance(v, str) else v) for v in missing]
    if sort_levels in ("labels",) or (sort_levels == "auto" and missing):
        pairs.sort(key=lambda p: str(p[1]), reverse=decreasing)
    elif sort_levels == "values" or (sort_levels == "auto" and missing):
        pairs.sort(key=lambda p: p[0], reverse=decreasing)
    names = [n for v, n in pairs]
    if levels.startswith("value"):
        names = [str(v) for v, n in pairs]
    elif levels.startswith("pref"):
        names = [f"[{v}] {n}" for v, n in pairs]
    vals = []
    for v in data:
        match = next((n for (code, n) in pairs if _same(v, code)), None)
        vals.append(match if match is not None else None)
    result = Vector(vals, "string")
    result.levels = names
    result.ordered = ordered
    result.class_ = ["ordered", "factor"] if ordered else ["factor"]
    result.label = x.label
    return result


def to_character(x, levels="labels", nolabel_to_na=False, user_na_to_na=False,
                 explicit_tagged_na=False, labelled_only=True, **kwargs):
    if isinstance(x, dict):
        return {k: to_character(v, levels, nolabel_to_na, user_na_to_na,
                                explicit_tagged_na, labelled_only)
                if isinstance(v, Vector) or not labelled_only else
                [str(z) if z is not None else None for z in v]
                for k, v in x.items()}
    if isinstance(x, Vector) and "haven_labelled" in x.class_:
        return to_factor(x, levels, nolabel_to_na, user_na_to_na=user_na_to_na,
                         explicit_tagged_na=explicit_tagged_na).values
    return [str(v) if v is not None else None for v in _values(x)]


def unlabelled(x, **kwargs):
    if isinstance(x, Vector):
        return to_factor(x, strict=True, unclass=True, **kwargs)
    if isinstance(x, dict):
        return to_factor(x, strict=True, unclass=True, labelled_only=True, **kwargs)
    return x


def update_labelled(x):
    if isinstance(x, dict):
        return {k: update_labelled(v) for k, v in x.items()}
    if isinstance(x, Vector):
        if "haven_labelled_spss" in x.class_:
            return labelled_spss(x.values, labels=dict((n, v) for v, n in x.labels),
                                 label=x.label, na_values=x.na_values,
                                 na_range=x.na_range)
        return labelled(x.values, labels=dict((n, v) for v, n in x.labels), label=x.label)
    return x


def foreign_to_labelled(x):
    if not isinstance(x, dict):
        return x
    variable_labels = x.get("__variable.labels__", x.get("variable.labels", {}))
    value_labels = x.get("__label.table__", x.get("label.table", {}))
    out = {}
    for name, values in x.items():
        if name.startswith("__"):
            continue
        if isinstance(values, Vector):
            out[name] = values
        else:
            out[name] = labelled(values, labels=value_labels.get(name))
        if name in variable_labels:
            out[name].label = variable_labels[name]
    return out


def memisc_to_labelled(x):
    if not (hasattr(x, "class_") and "data.set" in x.class_):
        return x
    raise ImportError("memisc is required to convert a data.set.")


def to_labelled(x, labels=None, _quiet=False, **kwargs):
    if isinstance(x, Vector):
        return x
    if isinstance(x, dict):
        return foreign_to_labelled(x)
    if hasattr(x, "class_") and "data.set" in x.class_:
        return memisc_to_labelled(x)
    if hasattr(x, "levels") and hasattr(x, "values"):
        if labels is None:
            labels = {level: i + 1 for i, level in enumerate(x.levels)}
        vals = [labels.get(v, na_real()) for v in x.values]
        return labelled(vals, labels=labels)
    return x

