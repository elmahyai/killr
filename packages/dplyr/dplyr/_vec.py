"""Private vector helpers for dplyr `near` and `between`.

These follow the installed dplyr 1.2.1 calls into vctrs: common type, cast,
recycle to the size of `x`, and `vec_compare`. They are not package exports.
"""

from __future__ import annotations

import datetime
import math
from dataclasses import dataclass, field

import numpy as np


class Logical(list):
    """A logical vector. `None` is R's NA."""

    def __init__(self, values, names=None, shape=None):
        super().__init__(True if v is True else False if v is False else None for v in values)
        self.names = names
        self.shape = shape

    def __repr__(self):
        if len(self) == 0:
            return "logical(0)"
        cells = []
        for value in self:
            if value is True:
                cells.append("TRUE")
            elif value is False:
                cells.append("FALSE")
            else:
                cells.append("NA")
        return "[" + ", ".join(cells) + "]"


@dataclass
class Vec:
    kind: str
    data: list = field(default_factory=list)
    levels: list | None = None
    ordered: bool = False
    names: list | None = None
    is_matrix: bool = False
    nrow: int = 0
    ncol: int = 0
    columns: list | None = None

    def size(self):
        if self.kind == "null":
            return 0
        if self.kind == "dataframe":
            return self.nrow
        if self.is_matrix:
            return self.nrow
        return len(self.data)


class Factor:
    """An R factor. `ordered=True` is `ordered()`."""

    def __init__(self, x, levels=None, ordered=False):
        self.values = list(x)
        self.ordered = ordered
        if levels is None:
            levels = []
            for value in self.values:
                if value is not None and value not in levels:
                    levels.append(value)
        self.levels = list(levels)

    def to_vec(self):
        index = {level: i for i, level in enumerate(self.levels)}
        codes = []
        for value in self.values:
            if value is None or (isinstance(value, float) and math.isnan(value)):
                codes.append(None)
            else:
                codes.append(index.get(value))
        return Vec("factor", codes, levels=self.levels, ordered=self.ordered)


def ordered(x, levels):
    """Build an ordered factor, the `ptype` used by `between()`."""
    return Factor(x, levels=levels, ordered=True)


def factor(x, levels=None, ordered=False):
    return Factor(x, levels=levels, ordered=ordered)


def ints(values):
    """An R integer vector. `None` is `NA_integer_`."""
    data = []
    for value in values:
        if value is None or (isinstance(value, float) and math.isnan(value)):
            data.append(None)
            continue
        item = int(value)
        if item < -2147483647 or item > 2147483647:
            raise ValueError("integer value is outside R's integer range")
        data.append(item)
    return Vec("integer", data)


_RANK = {"logical": 0, "integer": 1, "double": 2, "complex": 3}
_INT_MIN = -2147483647
_INT_MAX = 2147483647


def _clean_float(value):
    if value is None:
        return None
    number = float(value)
    if math.isnan(number):
        return None
    return number


def _is_missing(value):
    return value is None or (isinstance(value, float) and math.isnan(value))


def _scalar_kind(value):
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int):
        return "double"
    if isinstance(value, float):
        return "double"
    if isinstance(value, complex):
        return "complex"
    if isinstance(value, str):
        return "character"
    if isinstance(value, datetime.datetime):
        return "posixct"
    if isinstance(value, datetime.date):
        return "date"
    raise TypeError(f"unsupported between value {value!r}")


def _epoch_days(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        value = value.date()
    return float((value - datetime.date(1970, 1, 1)).days)


def _epoch_seconds(value):
    if value is None:
        return None
    if isinstance(value, datetime.datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return float(value.timestamp())
    if isinstance(value, datetime.date):
        instant = datetime.datetime(value.year, value.month, value.day, tzinfo=datetime.timezone.utc)
        return float(instant.timestamp())
    return None


def _coerce(value, kind):
    if kind == "logical":
        if _is_missing(value):
            return None
        return bool(value)
    if kind == "double":
        if isinstance(value, bool):
            return 1.0 if value else 0.0
        return _clean_float(value)
    if kind == "complex":
        if _is_missing(value):
            return None
        if isinstance(value, bool):
            return complex(1.0 if value else 0.0)
        return complex(value)
    if kind == "character":
        if _is_missing(value):
            return None
        if isinstance(value, bool):
            return "TRUE" if value else "FALSE"
        return str(value)
    if kind == "date":
        return _epoch_days(value)
    if kind == "posixct":
        return _epoch_seconds(value)
    raise TypeError(kind)


def _from_numpy(array):
    if array.ndim == 2:
        flat = array.ravel(order="F")
        vec = _from_numpy(flat)
        vec.is_matrix = True
        vec.nrow = int(array.shape[0])
        vec.ncol = int(array.shape[1])
        return vec
    if array.ndim != 1:
        raise TypeError("between supports vectors and two-dimensional arrays")
    if array.dtype == object:
        return _from_sequence(array.tolist())
    if np.issubdtype(array.dtype, np.bool_):
        return Vec("logical", [bool(value) for value in array.tolist()])
    if np.issubdtype(array.dtype, np.integer):
        values = [int(value) for value in array.tolist()]
        if any(value < _INT_MIN or value > _INT_MAX for value in values):
            return Vec("double", [float(value) for value in values])
        return Vec("integer", values)
    if np.issubdtype(array.dtype, np.floating):
        return Vec("double", [_clean_float(value) for value in array.tolist()])
    if np.issubdtype(array.dtype, np.complexfloating):
        data = []
        for value in array.tolist():
            if math.isnan(value.real) or math.isnan(value.imag):
                data.append(None)
            else:
                data.append(complex(value))
        return Vec("complex", data)
    if np.issubdtype(array.dtype, np.str_):
        return Vec("character", [None if value is None else str(value) for value in array.tolist()])
    raise TypeError(f"unsupported array dtype {array.dtype}")


def _from_sequence(items):
    if len(items) == 0:
        return Vec("double", [])
    kinds = set()
    for item in items:
        if _is_missing(item):
            continue
        kinds.add(_scalar_kind(item))
    if not kinds:
        return Vec("logical", [None] * len(items))
    if kinds <= {"date", "posixct"}:
        kind = "posixct" if "posixct" in kinds else "date"
        return Vec(kind, [_coerce(item, kind) for item in items])
    if "character" in kinds and kinds <= {"character", "logical", "double", "integer", "complex"}:
        return Vec("character", [_coerce(item, "character") for item in items])
    if kinds <= set(_RANK):
        kind = max(kinds, key=_RANK.__getitem__)
        return Vec(kind, [_coerce(item, kind) for item in items])
    raise TypeError("cannot mix these between values")


def _is_column(value):
    if isinstance(value, (str, bytes, Factor, Vec)):
        return False
    if isinstance(value, (list, tuple, range, np.ndarray)):
        return True
    return False


def _named_vector(mapping):
    names = list(mapping)
    vec = _from_sequence(list(mapping.values()))
    vec.names = names
    return vec


def _data_frame(mapping):
    columns = [(name, as_vec(value)) for name, value in mapping.items()]
    if not columns:
        return Vec("dataframe", columns=[], nrow=0)
    nrow = max(column.size() for _, column in columns)
    aligned = []
    for name, column in columns:
        aligned.append((name, recycle_to(column, nrow, name)))
    return Vec("dataframe", columns=aligned, nrow=nrow)


def as_vec(value):
    if isinstance(value, Vec):
        return value
    if isinstance(value, Factor):
        return value.to_vec()
    if value is None:
        return Vec("null")
    if isinstance(value, dict):
        if value and all(_is_column(item) for item in value.values()):
            return _data_frame(value)
        return _named_vector(value)
    if isinstance(value, np.ndarray):
        return _from_numpy(value)
    if isinstance(value, (list, tuple, range)):
        return _from_sequence(list(value))
    if isinstance(value, np.generic):
        return _from_numpy(np.atleast_1d(value))
    if isinstance(value, (bool, int, float, complex, str, datetime.date)):
        return _from_sequence([value])
    raise TypeError(f"unsupported between value {value!r}")


def type_name(vec):
    if vec.kind == "factor":
        return "ordered" if vec.ordered else "factor"
    if vec.is_matrix:
        return f"{vec.kind}[,{vec.ncol}]"
    return vec.kind


def _proto_from(vec):
    return Vec(
        vec.kind,
        levels=list(vec.levels) if vec.levels is not None else None,
        ordered=vec.ordered,
        is_matrix=vec.is_matrix,
        nrow=vec.nrow,
        ncol=vec.ncol,
        columns=None if vec.columns is None else [(name, _proto_from(column)) for name, column in vec.columns],
    )


def _na_like(proto, size):
    if proto.kind == "dataframe":
        return Vec(
            "dataframe",
            columns=[(name, _na_like(column, size)) for name, column in proto.columns],
            nrow=size,
        )
    return Vec(
        proto.kind,
        [None] * size,
        levels=list(proto.levels) if proto.levels is not None else None,
        ordered=proto.ordered,
        is_matrix=proto.is_matrix,
        nrow=size if proto.is_matrix else 0,
        ncol=proto.ncol,
    )


def _lossy(name, source, proto, locations, reason):
    shown = ", ".join(str(index) for index in locations)
    return ValueError(
        f"Can't convert from `{name}` <{type_name(source)}> to <{type_name(proto)}> "
        f"due to {reason}.\n• Locations: {shown}"
    )


def _convert_element(value, source_kind, proto):
    target = proto.kind
    if source_kind == target and target != "factor":
        return value, False
    if target == "character" and source_kind == "factor":
        if value is None:
            return None, False
        return proto.levels[value] if source_kind == "factor" else value, False
    if source_kind == "factor" and target == "character":
        if value is None:
            return None, False
        return proto.levels[value], False
    if source_kind == "factor" and target == "factor":
        if value is None:
            return None, False
        label = None if value is None else None
        return value, False
    if value is None and target in _RANK:
        return None, False
    if source_kind == "logical" and target == "integer":
        if value is None:
            return None, False
        return (1 if value else 0), False
    if source_kind == "logical" and target == "double":
        if value is None:
            return None, False
        return (1.0 if value else 0.0), False
    if source_kind == "logical" and target == "complex":
        if value is None:
            return None, False
        return complex(1.0 if value else 0.0), False
    if source_kind == "integer" and target == "double":
        if value is None:
            return None, False
        return float(value), False
    if source_kind == "integer" and target == "complex":
        if value is None:
            return None, False
        return complex(float(value)), False
    if source_kind == "integer" and target == "logical":
        if value is None:
            return None, False
        if value in (0, 1):
            return bool(value), False
        return None, True
    if source_kind == "double" and target == "integer":
        if value is None:
            return None, False
        if math.isinf(value) or not float(value).is_integer():
            return None, True
        item = int(value)
        if item < _INT_MIN or item > _INT_MAX:
            return None, True
        return item, False
    if source_kind == "double" and target == "logical":
        if value is None:
            return None, False
        if value == 0.0:
            return False, False
        if value == 1.0:
            return True, False
        return None, True
    if source_kind == "double" and target == "complex":
        if value is None:
            return None, False
        return complex(value), False
    if source_kind == "integer" and target == "double":
        return (None if value is None else float(value)), False
    if source_kind == "date" and target == "posixct":
        if value is None:
            return None, False
        return float(value) * 86400.0, False
    if source_kind == "character" and target == "factor":
        if value is None:
            return None, False
        try:
            return proto.levels.index(value), False
        except ValueError:
            return None, True
    if source_kind == "factor" and target == "factor":
        if value is None:
            return None, False
        label = proto.levels[value] if False else None
        return value, False
    return None, True


def _factor_label(vec, code):
    if code is None:
        return None
    return vec.levels[code]


def cast(vec, proto, name):
    if vec.kind == "null":
        return vec
    if proto.kind == "dataframe" or vec.kind == "dataframe":
        return _cast_frame(vec, proto, name)
    if vec.is_matrix or proto.is_matrix:
        return _cast_matrix(vec, proto, name)
    if vec.kind == "factor" and proto.kind == "character":
        labels = vec.levels
        return Vec("character", [None if code is None else labels[code] for code in vec.data])
    if vec.kind == "factor" and proto.kind == "factor":
        if vec.levels == proto.levels and vec.ordered == proto.ordered:
            return Vec("factor", list(vec.data), levels=list(proto.levels), ordered=proto.ordered)
        lossy = []
        data = []
        for index, code in enumerate(vec.data, start=1):
            if code is None:
                data.append(None)
                continue
            label = vec.levels[code]
            if label not in proto.levels:
                lossy.append(index)
                data.append(None)
            else:
                data.append(proto.levels.index(label))
        if lossy:
            reason = "loss of generality"
            raise _lossy(name, vec, proto, lossy, reason)
        return Vec("factor", data, levels=list(proto.levels), ordered=proto.ordered)
    if vec.kind == proto.kind:
        return Vec(proto.kind, list(vec.data), levels=proto.levels, ordered=proto.ordered, names=vec.names)
    data = []
    lossy = []
    reason = "loss of generality" if proto.kind == "factor" else "loss of precision"
    for index, value in enumerate(vec.data, start=1):
        if vec.kind == "factor" and proto.kind == "character":
            converted, lost = (None if value is None else vec.levels[value]), False
        else:
            converted, lost = _convert_element(value, vec.kind, proto)
        if lost:
            lossy.append(index)
        data.append(converted)
    if lossy:
        raise _lossy(name, vec, proto, lossy, reason)
    return Vec(
        proto.kind,
        data,
        levels=list(proto.levels) if proto.levels is not None else None,
        ordered=proto.ordered,
        names=vec.names,
    )


def _cast_frame(vec, proto, name):
    if vec.kind != "dataframe" or proto.kind != "dataframe":
        raise ValueError(
            f"Can't convert from `{name}` <{type_name(vec)}> to <{type_name(proto)}>."
        )
    source = dict(vec.columns)
    columns = []
    for column_name, column_proto in proto.columns:
        if column_name in source:
            columns.append((column_name, cast(source[column_name], column_proto, name)))
        else:
            columns.append((column_name, _na_like(column_proto, vec.nrow)))
    return Vec("dataframe", columns=columns, nrow=vec.nrow)


def _cast_matrix(vec, proto, name):
    target_kind = proto.kind if proto.kind != "null" else vec.kind
    atomic = _proto_from(proto)
    atomic.is_matrix = False
    atomic.kind = target_kind
    if vec.is_matrix:
        flat = Vec(vec.kind, list(vec.data))
        casted = cast(flat, atomic, name)
        return Vec(casted.kind, casted.data, is_matrix=True, nrow=vec.nrow, ncol=vec.ncol)
    flat = cast(vec, atomic, name)
    ncol = proto.ncol
    if flat.size() == 1:
        data = flat.data * ncol
        return Vec(flat.kind, data, is_matrix=True, nrow=1, ncol=ncol)
    if flat.size() == ncol:
        return Vec(flat.kind, list(flat.data), is_matrix=True, nrow=1, ncol=ncol)
    raise ValueError(
        f"Can't convert from `{name}` <{type_name(vec)}> to <{type_name(proto)}>."
    )


def _combine(left, right, left_name, right_name):
    if left.kind == "null":
        return right
    if right.kind == "null":
        return left
    if left.kind == "dataframe" or right.kind == "dataframe":
        if left.kind != "dataframe" or right.kind != "dataframe":
            raise ValueError(
                f"Can't combine `{left_name}` <{type_name(left)}> and `{right_name}` <{type_name(right)}>."
            )
        return _combine_frame(left, right, left_name, right_name)
    if left.is_matrix or right.is_matrix:
        return _combine_matrix(left, right, left_name, right_name)
    if left.kind in _RANK and right.kind in _RANK:
        kind = left.kind if _RANK[left.kind] >= _RANK[right.kind] else right.kind
        return Vec(kind)
    if left.kind == "date" and right.kind == "date":
        return Vec("date")
    if {left.kind, right.kind} <= {"date", "posixct"}:
        return Vec("posixct")
    if left.kind == "character" and right.kind == "character":
        return Vec("character")
    if left.kind == "factor" and right.kind == "character":
        return Vec("character")
    if left.kind == "character" and right.kind == "factor":
        return Vec("character")
    if left.kind == "factor" and right.kind == "factor":
        if left.levels == right.levels and left.ordered == right.ordered:
            return Vec("factor", levels=list(left.levels), ordered=left.ordered)
        raise ValueError(
            f"Can't combine `{left_name}` <{type_name(left)}> and `{right_name}` <{type_name(right)}>."
        )
    raise ValueError(
        f"Can't combine `{left_name}` <{type_name(left)}> and `{right_name}` <{type_name(right)}>."
    )


def _combine_frame(left, right, left_name, right_name):
    names = [name for name, _ in left.columns]
    right_map = dict(right.columns)
    left_map = dict(left.columns)
    for name in right_map:
        if name not in left_map:
            names.append(name)
    columns = []
    for name in names:
        if name in left_map and name in right_map:
            columns.append((name, _combine(left_map[name], right_map[name], left_name, right_name)))
        elif name in left_map:
            columns.append((name, _proto_from(left_map[name])))
        else:
            columns.append((name, _proto_from(right_map[name])))
    return Vec("dataframe", columns=columns, nrow=0)


def _combine_matrix(left, right, left_name, right_name):
    if left.is_matrix and right.is_matrix and left.ncol != right.ncol:
        raise ValueError(
            f"Can't combine `{left_name}` <{type_name(left)}> and `{right_name}` <{type_name(right)}>."
        )
    matrix = left if left.is_matrix else right
    other = right if left.is_matrix else left
    if other.is_matrix:
        kind = _combine(Vec(left.kind), Vec(right.kind), left_name, right_name).kind
        return Vec(kind, is_matrix=True, ncol=matrix.ncol, nrow=matrix.nrow)
    if other.kind not in _RANK and other.kind not in {"character", "logical"}:
        raise ValueError(
            f"Can't combine `{left_name}` <{type_name(left)}> and `{right_name}` <{type_name(right)}>."
        )
    kind = _combine(Vec(matrix.kind), Vec(other.kind), left_name, right_name).kind
    return Vec(kind, is_matrix=True, ncol=matrix.ncol, nrow=matrix.nrow)


def _as_prototype(ptype):
    if ptype is int or ptype is np.integer:
        return Vec("integer")
    if ptype is float:
        return Vec("double")
    if ptype is bool:
        return Vec("logical")
    if ptype is str:
        return Vec("character")
    if ptype is datetime.date:
        return Vec("date")
    if ptype is datetime.datetime:
        return Vec("posixct")
    vec = as_vec(ptype)
    if vec.kind == "null":
        raise ValueError("`ptype` must be a vector, not `NULL`.")
    return vec


def cast_common(pairs, ptype=None):
    if ptype is not None:
        proto = _as_prototype(ptype)
        return [cast(vec, proto, name) for name, vec in pairs]
    proto = pairs[0][1]
    acc_name = pairs[0][0]
    for name, vec in pairs[1:]:
        proto = _combine(proto, vec, acc_name, name)
    return [cast(vec, proto, name) for name, vec in pairs]


def recycle_to(vec, size, name):
    if vec.kind == "null":
        return vec
    current = vec.size()
    if current == size:
        return vec
    if current == 1:
        return _repeat(vec, size)
    raise ValueError(f"Can't recycle `{name}` (size {current}) to size {size}.")


def _repeat(vec, size):
    if vec.kind == "dataframe":
        return Vec(
            "dataframe",
            columns=[(name, _repeat(column, size)) for name, column in vec.columns],
            nrow=size,
        )
    if vec.is_matrix:
        if vec.nrow != 1:
            raise ValueError(f"Can't recycle input (size {vec.nrow}) to size {size}.")
        data = []
        for column in range(vec.ncol):
            data.extend([vec.data[column]] * size)
        return Vec(vec.kind, data, is_matrix=True, nrow=size, ncol=vec.ncol)
    if len(vec.data) != 1:
        raise ValueError(f"Can't recycle input (size {len(vec.data)}) to size {size}.")
    return Vec(
        vec.kind,
        vec.data * size,
        levels=list(vec.levels) if vec.levels is not None else None,
        ordered=vec.ordered,
        names=vec.names,
    )


def _cmp_values(left, right):
    if left is None or right is None:
        return None
    if isinstance(left, complex) or isinstance(right, complex):
        raise TypeError("vec_compare is not supported for complex vectors")
    if left < right:
        return -1
    if left > right:
        return 1
    return 0


def compare(left, right):
    if left.kind == "null":
        raise ValueError(
            "`x` must be a vector, not `NULL`.\n"
            "ℹ Read our FAQ about scalar types (`?vctrs::faq_error_scalar_type`) to learn more."
        )
    if right.kind == "null":
        raise ValueError(
            "`y` must be a vector, not `NULL`.\n"
            "ℹ Read our FAQ about scalar types (`?vctrs::faq_error_scalar_type`) to learn more."
        )
    if left.kind == "dataframe":
        return _compare_frame(left, right)
    if left.is_matrix:
        return _compare_matrix(left, right)
    if left.kind == "factor":
        return [_cmp_values(a, b) for a, b in zip(left.data, right.data)]
    return [_cmp_values(a, b) for a, b in zip(left.data, right.data)]


def _compare_matrix(left, right):
    out = []
    for row in range(left.nrow):
        decision = 0
        for column in range(left.ncol):
            index = row + column * left.nrow
            step = _cmp_values(left.data[index], right.data[index])
            if step is None:
                decision = None
                break
            if step != 0:
                decision = step
                break
        out.append(decision)
    return out


def _compare_frame(left, right):
    decisions = [0] * left.nrow
    right_map = dict(right.columns)
    for name, column in left.columns:
        steps = compare(column, right_map[name])
        for index, step in enumerate(steps):
            if decisions[index] is None or decisions[index] != 0:
                continue
            decisions[index] = step
    return decisions


def _flag(value):
    if value is None:
        return None
    return bool(value)


def _and(left, right):
    if left is False or right is False:
        return False
    if left is None or right is None:
        return None
    return True


def between_result(left_cmp, right_cmp):
    values = []
    for left, right in zip(left_cmp, right_cmp):
        left_ok = None if left is None else left >= 0
        right_ok = None if right is None else right <= 0
        values.append(_and(left_ok, right_ok))
    return Logical(values)
