"""Labelled vectors. The vctrs methods haven defines live on this class."""

from __future__ import annotations

import operator

from haven.tagged import format_tagged_na, is_na_double, is_tagged_na, na_real

_OPS = {
    "+": operator.add,
    "-": operator.sub,
    "*": operator.mul,
    "/": operator.truediv,
    "^": operator.pow,
    "%%": operator.mod,
    "%/%": lambda left, right: operator.floordiv(left, right),
}


class Vector:
    """A column of values plus the attributes haven stores."""

    def __init__(self, values, storage="double"):
        self.values = list(values)
        self.storage = storage
        self.label = None
        self.labels = []
        self.class_ = []
        self.format_stata = None
        self.format_spss = None
        self.format_sas = None
        self.display_width = None
        self.width = None
        self.na_values = None
        self.na_range = None
        self.units = None
        self.tzone = None
        self.levels = None
        self.ordered = False
        self.names = None

    def __len__(self):
        return len(self.values)

    @property
    def rows(self):
        return len(self.values)

    def __iter__(self):
        return iter(self.values)

    def __getitem__(self, item):
        if isinstance(item, int):
            return self.values[item]
        chosen = Vector([self.values[index] for index in item], self.storage)
        _copy_meta(self, chosen)
        return chosen

    def __setitem__(self, item, value):
        if isinstance(item, list) and item and isinstance(item[0], bool):
            for index, flag in enumerate(item):
                if flag:
                    self.values[index] = value
            return
        self.values[item] = value

    def copy(self):
        other = Vector(self.values, self.storage)
        _copy_meta(self, other)
        return other


def _copy_meta(source: Vector, target: Vector) -> None:
    target.label = source.label
    target.labels = list(source.labels)
    target.class_ = list(source.class_)
    target.format_stata = source.format_stata
    target.format_spss = source.format_spss
    target.format_sas = source.format_sas
    target.display_width = source.display_width
    target.width = source.width
    target.na_values = None if source.na_values is None else list(source.na_values)
    target.na_range = None if source.na_range is None else list(source.na_range)
    target.units = source.units
    target.tzone = source.tzone
    target.levels = None if source.levels is None else list(source.levels)
    target.ordered = source.ordered
    target.names = None if source.names is None else list(source.names)


def is_labelled(x) -> bool:
    """True when x is a labelled or SPSS-labelled vector."""
    return isinstance(x, Vector) and any(
        name in ("haven_labelled", "labelled") for name in x.class_
    )


def _same_storage(left, right) -> bool:
    if left is None or right is None:
        return True
    left_char = all(isinstance(item, str) for item in left if item is not None)
    right_char = all(isinstance(item, str) for item in right if item is not None)
    if not left or not right:
        return True
    return left_char == right_char


def _unique_labels(labels) -> None:
    seen = []
    for value, _name in labels:
        if is_na_double(value) or value is None:
            continue
        if any(item == value for item in seen):
            raise ValueError("`labels` must be unique.")
        seen.append(value)


def labelled(x=None, labels=None, label=None) -> Vector:
    """Create a labelled vector."""
    if x is None:
        x = []
    if isinstance(x, Vector):
        values = list(x.values)
        storage = x.storage
    elif isinstance(x, str):
        values = [x]
        storage = "string"
    elif isinstance(x, (int, float)) and not isinstance(x, bool):
        values = [float(x)]
        storage = "double"
    else:
        values = list(x)
        if values and isinstance(values[0], str):
            storage = "string"
        else:
            storage = "double"
            values = [None if item is None else float(item) for item in values]
    if storage not in ("double", "string"):
        raise ValueError("`x` must be a numeric or a character vector.")
    pairs = _label_pairs(labels, storage)
    if label is not None and (not isinstance(label, str)):
        raise ValueError("`label` must be a character vector of length one.")
    out = Vector(values, storage)
    out.labels = pairs
    out.label = label
    out.class_ = ["haven_labelled", "vctrs_vctr", "character" if storage == "string" else "double"]
    return out


def labelled_spss(x=None, labels=None, na_values=None, na_range=None, label=None, na_value=None) -> Vector:
    """A labelled vector that also records SPSS user-missing values."""
    if na_value is not None and na_values is None:
        na_values = [na_value]
    base = labelled(x, labels=labels, label=label)
    if na_values is not None:
        na_values = list(na_values)
        if any(is_na_double(item) or item is None for item in na_values):
            raise ValueError("`na_values` can not contain missing values.")
        if base.storage == "double":
            na_values = [float(item) for item in na_values]
    if na_range is not None:
        na_range = list(na_range)
        if len(na_range) != 2:
            raise ValueError("`na_range` must be a vector of length two the same type as `x`.")
        if any(is_na_double(item) or item is None for item in na_range):
            raise ValueError("`na_range` can not contain missing values.")
        if na_range[0] >= na_range[1]:
            raise ValueError("`na_range` must be in ascending order.")
        if base.storage == "double":
            na_range = [float(item) for item in na_range]
    base.na_values = na_values
    base.na_range = na_range
    base.class_ = ["haven_labelled_spss", "haven_labelled", "vctrs_vctr", base.class_[-1]]
    return base


def _label_pairs(labels, storage: str):
    if labels is None:
        return []
    if isinstance(labels, dict):
        pairs = [(value, name) for name, value in labels.items()]
    else:
        pairs = []
        for item in labels:
            if isinstance(item, tuple) and len(item) == 2:
                pairs.append((item[0], item[1]))
            else:
                raise ValueError("`labels` must have names.")
    converted = []
    for value, name in pairs:
        if name is None:
            raise ValueError("`labels` must have names.")
        if storage == "double" and not isinstance(value, str):
            value = float(value)
        elif storage == "string" and not isinstance(value, str):
            raise ValueError("`labels` must be the same type as `x`.")
        converted.append((value, str(name)))
    if converted and storage == "string" and not all(isinstance(value, str) for value, _name in converted):
        raise ValueError("`labels` must be the same type as `x`.")
    _unique_labels(converted)
    return converted


def is_missing(x: Vector) -> list[bool]:
    """Missing values, including SPSS user missings on a labelled_spss vector."""
    out = []
    for value in x.values:
        if x.storage == "string":
            out.append(value is None)
        else:
            out.append(is_na_double(value))
    if "haven_labelled_spss" not in x.class_:
        return out
    if x.na_values:
        for index, value in enumerate(x.values):
            if any(value == item for item in x.na_values):
                out[index] = True
    if x.na_range is not None:
        lo, hi = x.na_range
        for index, value in enumerate(x.values):
            if value is not None and not is_na_double(value) and lo <= value <= hi:
                out[index] = True
    return out


def print_labels(x, name=None) -> None:
    """Print the value labels of a labelled vector."""
    if not is_labelled(x):
        raise ValueError("`x` must be a labelled vector.")
    if not x.labels:
        return
    print(f"\nLabels:{'' if name is None else name}")
    values = []
    for value, _label in x.labels:
        if isinstance(value, float) and is_tagged_na([value])[0]:
            values.append(format_tagged_na([value])[0].strip())
        elif isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
            values.append(str(int(value)))
        else:
            values.append(str(value))
    labels = [label for _value, label in x.labels]
    value_width = max(len("value"), *(len(item) for item in values))
    label_width = max(len("label"), *(len(item) for item in labels))
    print(" " + "value".rjust(value_width) + " " + "label".rjust(label_width))
    for rendered, label in zip(values, labels):
        print(" " + rendered.rjust(value_width) + " " + label.rjust(label_width))


def _keep_missing(value):
    if isinstance(value, float) and is_na_double(value):
        return value
    if value is None or is_na_double(value):
        return na_real()
    return None


def vec_arith_haven_labelled(op, x, y=None):
    """Apply a numeric operator and return the plain values."""
    if op not in _OPS:
        raise ValueError(f"operator {op} is not supported for labelled vectors")
    left = x.values if isinstance(x, Vector) else ([x] if not isinstance(x, (list, tuple)) else list(x))
    if y is None:
        return [_keep_missing(item) or _OPS[op](0, item) if op == "-" else item for item in left]
    right = y.values if isinstance(y, Vector) else ([y] if not isinstance(y, (list, tuple)) else list(y))
    if len(left) == 1 and len(right) != 1:
        left = left * len(right)
    if len(right) == 1 and len(left) != 1:
        right = right * len(left)
    out = []
    for a, b in zip(left, right):
        kept = _keep_missing(a)
        if kept is None:
            kept = _keep_missing(b)
        out.append(kept if kept is not None else _OPS[op](a, b))
    return out
