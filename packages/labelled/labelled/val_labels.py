"""Value-label helpers translated from labelled 2.16.1."""

from __future__ import annotations

from copy import deepcopy
from math import isnan

try:
    from haven.labelled import Vector
except ImportError:  # pragma: no cover
    class Vector:
        def __init__(self, values, labels=None, label=None):
            self.values = list(values)
            self.labels = [(value, name) for name, value in (labels or {}).items()]
            self.label = label
            self.class_ = ["haven_labelled"]
            self.na_values = None
            self.na_range = None

        def copy(self):
            return deepcopy(self)

    def labelled(values=None, labels=None, label=None):
        return Vector([] if values is None else values, labels, label)


def _is_na(value):
    return value is None or (isinstance(value, float) and isnan(value))


def _copy(x):
    return x.copy() if hasattr(x, "copy") else deepcopy(x)


def _pairs(x):
    if isinstance(x, Vector):
        return list(x.labels)
    if isinstance(x, dict):
        return [(value, name) for name, value in x.items()]
    if x is None:
        return []
    return list(x)


def _set_pairs(x, pairs, null_action="unclass"):
    out = _copy(x)
    if isinstance(out, Vector):
        out.labels = list(pairs)
        if not pairs and null_action == "unclass":
            out.class_ = []
        return out
    return out


def _map_columns(data, fn):
    if isinstance(data, dict):
        return {name: fn(value) for name, value in data.items()}
    try:
        import polars as pl
        if isinstance(data, pl.DataFrame):
            return data.with_columns(
                [pl.col(name).map_batches(lambda s: s, return_dtype=data[name].dtype)
                 for name in data.columns]
            )
    except ImportError:
        pass
    return fn(data)


def val_labels(x, prefixed=False):
    """Return value labels as a name-to-value dictionary."""
    if isinstance(x, Vector):
        pairs = _pairs(x)
        if not prefixed:
            return {name: value for value, name in pairs}
        return {name: f"[{value}] {name}" for value, name in pairs}
    if isinstance(x, dict):
        return {name: val_labels(value, prefixed=prefixed) for name, value in x.items()}
    return None


def val_label(x, v, prefixed=False):
    if isinstance(x, Vector):
        for value, name in _pairs(x):
            if value == v:
                return f"[{value}] {name}" if prefixed else name
        return None
    if isinstance(x, dict):
        return {name: val_label(value, v, prefixed=prefixed) for name, value in x.items()}
    return None


def set_value_labels(
    data, *args, labels=None, strict=True, overwrite=True,
    null_action="unclass", **kwargs
):
    """Replace value labels on a vector or named collection of vectors."""
    if isinstance(data, Vector):
        if not overwrite and _pairs(data):
            return data
        supplied = labels if labels is not None else _named_args(args, kwargs)
        if isinstance(supplied, dict):
            supplied = [(value, name) for name, value in supplied.items()]
        return _set_pairs(data, supplied or [], null_action)
    if isinstance(data, dict):
        out = dict(data)
        supplied = labels if labels is not None else _named_args(args, kwargs)
        if labels is not None:
            supplied = {k: v for k, v in supplied.items()
                        if k in out} if not strict else supplied
        if strict and any(k not in out for k in supplied or {}):
            raise KeyError(next(k for k in supplied if k not in out))
        for name, value in (supplied or {}).items():
            if overwrite or not _pairs(out[name]):
                out[name] = set_value_labels(out[name], labels=value,
                                              null_action=null_action)
        return out
    return data


def _named_args(args, kwargs):
    if args:
        if len(args) != 1 or not isinstance(args[0], dict):
            raise TypeError("value labels must be named")
        return args[0]
    return kwargs


def add_value_labels(data, *args, strict=True, null_action="unclass", **kwargs):
    supplied = _named_args(args, kwargs)
    if isinstance(data, Vector):
        pairs = _pairs(data)
        by_value = {value: name for value, name in pairs}
        for name, value in supplied.items():
            by_value[value] = name
        return _set_pairs(data, [(value, name) for value, name in by_value.items()],
                          null_action)
    if isinstance(data, dict):
        if strict and any(k not in data for k in supplied):
            raise KeyError(next(k for k in supplied if k not in data))
        out = dict(data)
        for name, labels in supplied.items():
            if name not in out:
                continue
            out[name] = add_value_labels(out[name], labels, strict=strict,
                                         null_action=null_action)
        return out
    return data


def remove_value_labels(data, *args, strict=True, null_action="unclass", **kwargs):
    supplied = args[0] if args and len(args) == 1 and isinstance(args[0], (list, tuple)) else args
    supplied = list(supplied) if args else list(kwargs.values())
    if isinstance(data, Vector):
        return _set_pairs(data, [(value, name) for value, name in _pairs(data)
                                 if value not in supplied], null_action)
    if isinstance(data, dict):
        if strict and any(k not in data for k in kwargs):
            raise KeyError(next(k for k in kwargs if k not in data))
        out = dict(data)
        for name, values in kwargs.items():
            out[name] = remove_value_labels(out[name], values, strict=strict,
                                            null_action=null_action)
        return out
    return data


def update_value_labels_with(data, fn, cols=None, *args, **kwargs):
    if isinstance(data, dict):
        out = dict(data)
        selected = data.keys() if cols is None else cols
        for name in selected:
            labels = val_labels(out[name])
            if labels is not None:
                out[name] = set_value_labels(out[name],
                                              labels={fn(k, *args, **kwargs): v
                                                      for k, v in labels.items()})
        return out
    return data


def update_variable_labels_with(data, fn, cols=None, *args, **kwargs):
    if not isinstance(data, dict):
        return data
    out = dict(data)
    selected = data.keys() if cols is None else cols
    for name in selected:
        column = _copy(out[name])
        if isinstance(column, Vector):
            column.label = fn(column.label, *args, **kwargs)
        out[name] = column
    return out


def names_prefixed_by_values(x, sep="[]"):
    if x is None:
        return None
    if isinstance(x, list):
        return [names_prefixed_by_values(item, sep) for item in x]
    if isinstance(x, dict):
        return {name: (f"[{value}] {name}" if sep == "[]"
                       else f"{value}{sep}{name}")
                for name, value in x.items()}
    return x


def sort_val_labels(x, according_to="values", decreasing=False):
    if isinstance(x, Vector):
        pairs = _pairs(x)
        if according_to in ("labels", "l"):
            key = lambda pair: pair[1]
        else:
            key = lambda pair: pair[0]
        return _set_pairs(x, sorted(pairs, key=key, reverse=decreasing))
    if isinstance(x, dict):
        return {name: sort_val_labels(value, according_to, decreasing)
                for name, value in x.items()}
    return x


def nolabel_to_na(x):
    if isinstance(x, Vector):
        labelled_values = {value for value, _ in _pairs(x)}
        out = x.copy()
        out.values = [None if not _is_na(value) and value not in labelled_values else value
                      for value in out.values]
        return out
    if isinstance(x, dict):
        return {name: nolabel_to_na(value) for name, value in x.items()}
    return x


def val_labels_to_na(x):
    if isinstance(x, Vector):
        values = {value for value, _ in _pairs(x)}
        out = x.copy()
        out.values = [None if value in values else value for value in out.values]
        out.labels = []
        out.class_ = [] if not out.na_values and out.na_range is None else out.class_
        return out
    if isinstance(x, dict):
        return {name: val_labels_to_na(value) for name, value in x.items()}
    return x
