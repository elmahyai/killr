"""isplit from iterators 1.0.14.

Returns an iterator over the groups of ``x`` defined by ``f``. A factor keeps
its levels, including levels that do not occur. Anything else is turned into
a factor, and the key is taken from ``sort(unique(f))`` with missing values
removed. ``drop=TRUE`` skips an empty group. A data frame is split by row.

``icount`` walks the level combinations. ``nextElem`` and ``iter`` from
``iterators.core`` run the iterator. An empty combination list stops with
``illegal zero length vector``.
"""

from __future__ import annotations

import locale
import math
import warnings

import numpy as np

from iterators.core import DataFrame, Iter, IteratorError, icount, nextElem
from iterators.core import iter as r_iter


class NAType:
    """R's missing value. ``None`` remains ``NULL``, and ``NaN`` stays a number."""

    def __repr__(self):
        return "NA"


NA = NAType()


class Factor:
    """An R factor. ``codes`` are 1-based, and ``NA`` is a missing code."""

    def __init__(self, codes, levels, ordered=False):
        self.codes = list(codes)
        self.levels = [str(level) for level in levels]
        self.ordered = bool(ordered)

    def __repr__(self):
        return f"Factor({self.codes!r}, {self.levels!r})"


class Atomic:
    """An R atomic vector. ``names`` is ``None`` when the vector is unnamed."""

    def __init__(self, values, kind, names=None):
        self.values = list(values)
        self.kind = kind
        self.names = None if names is None else list(names)

    def __repr__(self):
        return f"Atomic({self.kind}, {self.values!r})"


class RList:
    """An R list, as opposed to an atomic vector stored as a Python list."""

    def __init__(self, elements, names=None):
        self.elements = list(elements)
        self.names = None if names is None else list(names)

    def __repr__(self):
        return f"RList({self.elements!r}, {self.names!r})"


class Split:
    """One group. ``key_names`` is ``None`` when the grouping list has no names."""

    def __init__(self, value, key, key_names, key_kinds):
        self.value = value
        self.key = list(key)
        self.key_names = None if key_names is None else list(key_names)
        self.key_kinds = list(key_kinds)

    def __repr__(self):
        return f"Split(value={self.value!r}, key={self.key!r})"


def _is_na(value):
    return value is NA


def _scalar_kind(value):
    if _is_na(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return "logical"
    if isinstance(value, (int, np.integer)):
        return "integer"
    if isinstance(value, (float, np.floating)):
        return "double"
    if isinstance(value, str):
        return "character"
    return None


def _infer_kind(values):
    kind = None
    for value in values:
        if _is_na(value):
            continue
        if isinstance(value, float) and math.isnan(value):
            item = "double"
        else:
            item = _scalar_kind(value)
        if item is None:
            raise IteratorError("unsupported type")
        if kind is None:
            kind = item
        elif kind != item:
            if {kind, item} == {"integer", "double"}:
                kind = "double"
            else:
                raise IteratorError("unsupported type")
    return "logical" if kind is None else kind


def _python(value):
    if isinstance(value, np.generic):
        return value.item()
    return value


def _decompose(obj):
    """Return ``(values, kind, names)`` for one atomic vector, factor, or ``NULL``."""
    if obj is None:
        return [], "null", None
    if isinstance(obj, Atomic):
        return list(obj.values), obj.kind, obj.names
    if isinstance(obj, Factor):
        return list(obj.codes), "factor", None
    if isinstance(obj, np.ndarray):
        flat = np.ravel(obj, order="F")
        if flat.dtype.kind == "b":
            return [bool(item) for item in flat], "logical", None
        if flat.dtype.kind in "iu":
            return [int(item) for item in flat], "integer", None
        if flat.dtype.kind == "f":
            return [float(item) for item in flat], "double", None
        if flat.dtype.kind in "SU":
            return [str(item) for item in flat], "character", None
        raise IteratorError("unsupported type")
    if isinstance(obj, (bool, np.bool_, int, np.integer, float, np.floating, str)):
        value = _python(obj)
        return [value], _scalar_kind(value), None
    if isinstance(obj, (list, tuple)):
        values = [_python(item) for item in obj]
        return values, _infer_kind(values), None
    raise IteratorError("unsupported type")


def _as_character_double(value):
    """R ``as.character`` for one double. A missing value stays missing."""
    if _is_na(value):
        return NA
    value = float(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0.0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


def _sort_character(values):
    """R ``sort`` of character data under the ``en_US.UTF-8`` collation."""
    if len(values) < 2:
        return list(values)
    saved = locale.setlocale(locale.LC_COLLATE)
    try:
        locale.setlocale(locale.LC_COLLATE, "en_US.UTF-8")
        return sorted(values, key=locale.strxfrm)
    finally:
        locale.setlocale(locale.LC_COLLATE, saved)


def _same(kind, left, right):
    if _is_na(left) or _is_na(right):
        return _is_na(left) and _is_na(right)
    if kind == "double":
        if isinstance(left, float) and math.isnan(left):
            return isinstance(right, float) and math.isnan(right)
        if isinstance(right, float) and math.isnan(right):
            return False
        return float(left) == float(right)
    return left == right


def _unique(values, kind):
    kept = []
    for value in values:
        if any(_same(kind, value, seen) for seen in kept):
            continue
        kept.append(value)
    return kept


def _sort_na(value, kind):
    if _is_na(value):
        return True
    if kind == "double" and isinstance(value, float) and math.isnan(value):
        return True
    return False


def _order_double(values):
    """R ``order``: numbers, then ``NaN``, then ``NA``."""

    def key(value):
        if isinstance(value, float) and math.isnan(value):
            return (1, 0.0)
        if _is_na(value):
            return (2, 0.0)
        return (0, float(value))

    return sorted(range(len(values)), key=lambda index: key(values[index]))


def _factor_from_values(values, kind):
    if kind == "null":
        return Factor([], [])
    if kind == "integer":
        levels = sorted(value for value in _unique(values, kind) if not _sort_na(value, kind))
        codes = []
        for value in values:
            if _sort_na(value, kind):
                codes.append(NA)
            else:
                codes.append(levels.index(value) + 1)
        return Factor(codes, [str(level) for level in levels])
    if kind == "logical":
        present = [value for value in (False, True) if any(item is value for item in values)]
        codes = []
        for value in values:
            if _is_na(value):
                codes.append(NA)
            else:
                codes.append(present.index(bool(value)) + 1)
        return Factor(codes, ["TRUE" if level else "FALSE" for level in present])
    if kind == "character":
        levels = _sort_character(
            [value for value in _unique(values, kind) if not _sort_na(value, kind)]
        )
        codes = []
        for value in values:
            if _is_na(value):
                codes.append(NA)
            else:
                codes.append(levels.index(value) + 1)
        return Factor(codes, levels)
    if kind == "double":
        unique = _unique(values, kind)
        ordered = [unique[index] for index in _order_double(unique)]
        levels = []
        for value in ordered:
            text = _as_character_double(value)
            if text is NA or text in levels:
                continue
            levels.append(text)
        codes = []
        for value in values:
            text = _as_character_double(value)
            if text is NA or text not in levels:
                codes.append(NA)
            else:
                codes.append(levels.index(text) + 1)
        return Factor(codes, levels)
    raise IteratorError("unsupported type")


def _plain_levels(values, kind):
    """``sort(unique.default(x))``. ``sort`` drops missing values."""
    if kind == "null":
        return [], "logical"
    kept = [value for value in _unique(values, kind) if not _sort_na(value, kind)]
    if kind == "character":
        return _sort_character(kept), "character"
    if kind == "logical":
        return [value for value in (False, True) if value in kept], "logical"
    if kind == "integer":
        return sorted(kept), "integer"
    if kind == "double":
        return sorted(float(value) for value in kept), "double"
    raise IteratorError("unsupported type")


def factor(x, levels=None, ordered=False):
    """Build a factor the way R's ``factor`` does when ``levels`` is supplied.

    Omitted ``levels`` follow ``as.factor``.
    """
    if isinstance(x, Factor) and levels is None:
        return x
    values, kind, _names = _decompose(x)
    if levels is None:
        built = _factor_from_values(values, kind)
        built.ordered = bool(ordered)
        return built
    labels = [str(level) for level in levels]
    codes = []
    for value in values:
        if kind == "double":
            text = _as_character_double(value)
        elif kind == "logical":
            text = NA if _is_na(value) else ("TRUE" if value else "FALSE")
        elif kind == "integer":
            text = NA if _is_na(value) else str(int(value))
        elif kind == "character":
            text = NA if _is_na(value) else value
        elif kind in ("null", "logical") and not values:
            text = NA
        else:
            text = NA if _is_na(value) else str(value)
        if text is NA or text not in labels:
            codes.append(NA)
        else:
            codes.append(labels.index(text) + 1)
    return Factor(codes, labels, ordered=ordered)


def _is_atomic_sequence(obj):
    if isinstance(obj, (str, bytes, Atomic, Factor, DataFrame, RList, np.ndarray, dict)):
        return False
    if not isinstance(obj, (list, tuple)):
        return False
    for item in obj:
        if isinstance(item, (list, tuple, dict, Factor, Atomic, DataFrame, RList, np.ndarray)):
            return False
    return True


def _grouping(f):
    """Return the list ``f`` becomes, and its names.

    A bare vector is one grouping variable. A data frame, a dict, an
    ``RList``, or a list of vectors is several.
    """
    if isinstance(f, DataFrame):
        return [f.columns[name] for name in f.names], list(f.names)
    if isinstance(f, dict):
        return list(f.values()), [str(name) for name in f.keys()]
    if isinstance(f, RList):
        return list(f.elements), f.names
    if isinstance(f, (list, tuple)) and not _is_atomic_sequence(f):
        return list(f), None
    return [f], None


def _prepare(f):
    pieces, names = _grouping(f)
    code_lists = []
    level_lists = []
    level_kinds = []
    counts = []
    for piece in pieces:
        if isinstance(piece, Factor):
            code_lists.append(list(piece.codes))
            level_lists.append(list(piece.levels))
            level_kinds.append("character")
            counts.append(len(piece.levels))
            continue
        values, kind, _names = _decompose(piece)
        built = _factor_from_values(values, kind)
        plain, plain_kind = _plain_levels(values, kind)
        code_lists.append(built.codes)
        level_lists.append(plain)
        level_kinds.append(plain_kind)
        counts.append(len(built.levels))
    return code_lists, level_lists, level_kinds, counts, names


def _icountn(vn):
    """The level odometer ``isplit`` uses. The first count changes fastest."""
    counts = [int(value) for value in vn]
    width = len(counts)
    if width == 0:
        raise IteratorError("illegal zero length vector")
    outer = icount(counts[-1])
    if width == 1:

        def next_one():
            return [nextElem(outer)]

        return r_iter(Iter(["abstractiter", "iter"], nextElem=next_one))

    inner = _icountn(counts[:-1])
    has_value = False
    cached = None

    def next_many():
        nonlocal inner, has_value, cached
        while True:
            if not has_value:
                cached = nextElem(outer)
                has_value = True
            try:
                head = nextElem(inner)
            except IteratorError as exc:
                if exc.message == "StopIteration":
                    inner = _icountn(counts[:-1])
                    has_value = False
                    continue
                raise IteratorError(exc.message) from None
            if not isinstance(head, list):
                head = [head]
            return head + [cached]

    return r_iter(Iter(["abstractiter", "iter"], nextElem=next_many))


def _recycle(op, left, right):
    if len(left) == 0 or len(right) == 0:
        return []
    width = max(len(left), len(right))
    if width % len(left) or width % len(right):
        warnings.warn(
            "longer object length is not a multiple of shorter object length",
            UserWarning,
            stacklevel=3,
        )
    return [op(left[index % len(left)], right[index % len(right)]) for index in range(width)]


def _eq(left, right):
    if _is_na(left) or _is_na(right):
        return None
    if isinstance(left, float) and math.isnan(left):
        return None
    if isinstance(right, float) and math.isnan(right):
        return None
    return left == right


def _and(left, right):
    if left is False or right is False:
        return False
    if left is None or right is None:
        return None
    return True


def _iwhich(code_lists, index):
    if len(index) == 0:
        raise IteratorError("illegal zero length vector")
    mask = [True] * len(code_lists[0])
    for position, code in enumerate(index):
        compared = _recycle(_eq, code_lists[position], [code])
        mask = _recycle(_and, mask, compared)
    return [offset + 1 for offset, bit in enumerate(mask) if bit is True]


def _drop_elements(drop):
    if drop is None or drop is NA:
        return [drop]
    if isinstance(drop, np.ndarray):
        return [_python(item) for item in np.ravel(drop, order="F")]
    if isinstance(drop, (list, tuple)):
        return [_python(item) for item in drop]
    if isinstance(drop, (bool, np.bool_, int, np.integer, float, np.floating, str)):
        return [_python(drop)]
    raise IteratorError("invalid argument type")


def _truth(value):
    if _is_na(value):
        return None
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, (int, np.integer, float, np.floating)):
        number = float(value)
        if math.isnan(number):
            return None
        return number != 0.0
    raise IteratorError("invalid argument type")


def _not(drop):
    if drop is None or isinstance(drop, str):
        raise IteratorError("invalid argument type")
    elements = _drop_elements(drop)
    if any(isinstance(item, str) or item is None for item in elements):
        raise IteratorError("invalid argument type")
    bits = []
    for item in elements:
        flag = _truth(item)
        bits.append(None if flag is None else (not flag))
    return bits


def _or(left, right):
    """``left || right`` for the ``drop`` test. ``None`` means a missing condition."""
    if len(left) > 1:
        raise IteratorError(f"'length = {len(left)}' in coercion to 'logical(1)'")
    if len(left) == 0:
        return True if right else None
    bit = left[0]
    if bit is True:
        return True
    if bit is False:
        return True if right else False
    return True if right else None


def _keep(drop, nonempty):
    flag = _or(_not(drop), nonempty)
    if flag is None:
        raise IteratorError("missing value where TRUE/FALSE needed")
    return flag


def _subset_atomic(values, kind, names, indices):
    if kind == "null":
        return None
    chosen = []
    chosen_names = [] if names is not None else None
    width = len(values)
    for index in indices:
        if isinstance(index, bool) or not isinstance(index, (int, np.integer)) or index < 1 or index > width:
            chosen.append(NA)
            if chosen_names is not None:
                chosen_names.append(NA)
            continue
        chosen.append(values[index - 1])
        if chosen_names is not None:
            chosen_names.append(names[index - 1])
    return Atomic(chosen, kind, chosen_names)


def _subset_factor(factor_obj, indices):
    codes = []
    width = len(factor_obj.codes)
    for index in indices:
        if isinstance(index, bool) or not isinstance(index, (int, np.integer)) or index < 1 or index > width:
            codes.append(NA)
        else:
            codes.append(factor_obj.codes[index - 1])
    return Factor(codes, factor_obj.levels, factor_obj.ordered)


def _subset_list(obj, indices):
    elements = []
    names = [] if obj.names is not None else None
    width = len(obj.elements)
    for index in indices:
        if isinstance(index, bool) or not isinstance(index, (int, np.integer)) or index < 1 or index > width:
            elements.append(None)
            if names is not None:
                names.append(NA)
        else:
            elements.append(obj.elements[index - 1])
            if names is not None:
                names.append(obj.names[index - 1])
    return RList(elements, names)


def _column_kind(values):
    for value in values:
        if _is_na(value):
            continue
        if isinstance(value, float) and math.isnan(value):
            return "double"
        kind = _scalar_kind(value)
        if kind is not None:
            return kind
    return "logical"


def _make_unique(names):
    """R ``make.unique`` with a dot before the added number."""
    seen = set(names)
    used = {}
    out = []
    for name in names:
        if name not in used:
            used[name] = 1
            out.append(name)
            continue
        number = used[name]
        candidate = f"{name}.{number}"
        while candidate in seen or candidate in used:
            number += 1
            candidate = f"{name}.{number}"
        used[name] = number + 1
        used[candidate] = 1
        seen.add(candidate)
        out.append(candidate)
    return out


def _subset_frame(frame, indices):
    kinds = [_column_kind(frame.columns[name]) for name in frame.names]
    columns = {name: [] for name in frame.names}
    rows = []
    for index in indices:
        missing = (
            _is_na(index)
            or isinstance(index, bool)
            or not isinstance(index, (int, np.integer))
            or index < 1
            or index > frame.nrow
        )
        if missing:
            rows.append("NA")
            for name in frame.names:
                columns[name].append(NA)
            continue
        rows.append(frame.row_names[index - 1])
        for name in frame.names:
            columns[name].append(frame.columns[name][index - 1])
    result = DataFrame(columns, row_names=_make_unique(rows))
    result.kinds = kinds
    return result


def _subset(obj, indices):
    if obj is None:
        return None
    if isinstance(obj, DataFrame):
        return _subset_frame(obj, indices)
    if isinstance(obj, Factor):
        return _subset_factor(obj, indices)
    if isinstance(obj, RList):
        return _subset_list(obj, indices)
    if isinstance(obj, Atomic):
        return _subset_atomic(obj.values, obj.kind, obj.names, indices)
    values, kind, names = _decompose(obj)
    return _subset_atomic(values, kind, names, indices)


def _key_at(levels, code):
    if isinstance(code, bool) or not isinstance(code, (int, np.integer)):
        return NA
    if code < 1 or code > len(levels):
        return NA
    return levels[code - 1]


def _bind(args, kwargs):
    formals = ("x", "f", "drop")
    exact = {}
    pending = []
    for name, value in kwargs.items():
        if name in formals:
            exact[name] = value
        else:
            pending.append((name, value))
    partial = {}
    for name, value in pending:
        hits = [formal for formal in formals if formal not in exact and formal.startswith(name) and name]
        if len(hits) > 1:
            raise IteratorError(f"argument {name!r} matches multiple formal arguments")
        if len(hits) == 1:
            formal = hits[0]
            if formal in partial:
                raise IteratorError(
                    f'formal argument "{formal}" matched by multiple actual arguments'
                )
            partial[formal] = value
    bound = dict(exact)
    bound.update(partial)
    position = 0
    for formal in formals:
        if formal in bound:
            continue
        if position < len(args):
            bound[formal] = args[position]
            position += 1
    if "drop" not in bound:
        bound["drop"] = False
    return bound


def _isplit_default(x, f, drop, x_missing):
    code_lists, level_lists, level_kinds, counts, key_names = _prepare(f)
    counter = _icountn(counts)

    def next_el():
        while True:
            index = nextElem(counter)
            if not isinstance(index, list):
                index = [index]
            chosen = _iwhich(code_lists, index)
            if _keep(drop, len(chosen) > 0):
                break
        if x_missing:
            raise IteratorError('argument "x" is missing, with no default')
        value = _subset(x, chosen)
        key = [_key_at(level_lists[pos], index[pos]) for pos in range(len(index))]
        return Split(value, key, key_names, level_kinds)

    return r_iter(Iter(["abstractiter", "iter"], nextElem=next_el))


def _isplit_frame(frame, f, drop):
    rows = Atomic(list(range(1, frame.nrow + 1)), "integer")
    inner = _isplit_default(rows, f, drop, x_missing=False)

    def next_el():
        group = nextElem(inner)
        value = _subset_frame(frame, group.value.values)
        return Split(value, group.key, group.key_names, group.key_kinds)

    return r_iter(Iter(["abstractiter", "iter"], nextElem=next_el))


def isplit(*args, **kwargs):
    """Split ``x`` into the groups defined by ``f``.

    ``f`` is a factor, a vector, or a list of those. ``drop`` omits a group
    that has no rows when it is true. A data frame yields one frame per
    group. The iterator stops with ``StopIteration``.
    """
    bound = _bind(args, kwargs)
    if "f" not in bound:
        raise IteratorError('argument "f" is missing, with no default')
    x_missing = "x" not in bound
    x = None if x_missing else bound["x"]
    if (not x_missing) and isinstance(x, DataFrame):
        return _isplit_frame(x, bound["f"], bound["drop"])
    return _isplit_default(x, bound["f"], bound["drop"], x_missing)
