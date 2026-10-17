"""Match, coalesce, and contiguous tapply.

Integer, real, and character lookups use a dict. A real NA and a NaN are
different keys, and -0 matches 0. A factor that is being looked up uses its
labels. A factor used as the table keeps its integer codes. Any other type,
and any incomparables value other than NULL or a single FALSE, uses the same
rules as match().
"""

from __future__ import annotations

import math
import warnings

_MISSING = object()

_SAFE_WARNING = (
    "This R version has made SETLENGTH illegal, but does not have growable "
    "vector API, use R < 4.5.0 or >= 4.6.0 to enable .SAFE=FALSE mode."
)


class Factor:
    """Labels with R's default level order, unless levels are supplied."""

    def __init__(self, values, levels=None):
        labels = list(values)
        if levels is None:
            seen = []
            for label in labels:
                if label is not None and label not in seen:
                    seen.append(label)
            levels = sorted(seen)
        else:
            levels = list(levels)
        index = {label: i + 1 for i, label in enumerate(levels)}
        codes = []
        for label in labels:
            if label is None:
                codes.append(None)
            elif label not in index:
                raise ValueError(f"level {label!r} is not in the factor")
            else:
                codes.append(index[label])
        self.labels = labels
        self.levels = levels
        self.codes = codes

    def __len__(self):
        return len(self.labels)


class PosixLt:
    """A POSIXlt value already formatted the way as.character prints it."""

    def __init__(self, values):
        self.values = [values] if isinstance(values, str) else list(values)

    def __len__(self):
        return len(self.values)


class List(list):
    """A generic vector. A plain list of numbers is an atomic vector."""


class Integers(list):
    """An integer vector. Use this when every value is missing."""


class Characters(list):
    """A character vector. Use this when every value is missing."""


class MatchHash:
    def __str__(self):
        return "<hash table>"

    def __repr__(self):
        return "<hash table>"


class Hashed(list):
    """A table returned by fmatch_hash, with the match hash attached."""

    def __init__(self, values):
        super().__init__(values)
        self.match_hash = MatchHash()


class Named:
    """An atomic result with a name per value, as c() returns from ctapply."""

    def __init__(self, values, names):
        self.values = list(values)
        self.names = list(names)

    def __len__(self):
        return len(self.values)

    def __str__(self):
        return " ".join(f"{name}:{value}" for name, value in zip(self.names, self.values))


def fmatch(x, table, nomatch=None, incomparables=None):
    """1-based positions of x in table. Missing results use nomatch."""
    return _fmatch(x, table, nomatch, incomparables, hash_only=False)


def fmatch_hash(x, table, nomatch=None, incomparables=None):
    """Build the table hash. x is used only to choose the common type."""
    return _fmatch(x, table, nomatch, incomparables, hash_only=True)


def fin(x, table):
    """TRUE where x occurs in table. A miss is FALSE, because nomatch is 0."""
    hits = fmatch(x, table, nomatch=0, incomparables=None)
    return [hit > 0 for hit in hits]


def not_fin(x, table):
    """TRUE where x does not occur in table."""
    hits = fmatch(x, table, nomatch=0, incomparables=None)
    return [hit == 0 for hit in hits]


def coalesce(x):
    """1-based order that packs equal values into contiguous groups.

    Groups follow the first occurrence, the same order as unique().
    """
    kind, values, _codes = _prepare(x, labels=False)
    if kind not in ("integer", "real", "character"):
        raise TypeError("coalesce supports integer, real, and character vectors")
    groups = {}
    for position, value in enumerate(values, start=1):
        groups.setdefault(_key(kind, value), []).append(position)
    order = []
    for positions in groups.values():
        order.extend(positions)
    return order


def ctapply(x, index, fun, *args, merge=_MISSING, safe=True):
    """Apply fun to each contiguous run of index.

    merge defaults to c(). Pass merge=None to ask for the error R raises
    when MERGE is NULL. safe=False warns on this R and still allocates a
    fresh slice for every group.
    """
    if safe is False:
        warnings.warn(_SAFE_WARNING, UserWarning, stacklevel=2)
    x_kind, x_values = _ct_x(x)
    index_kind, index_values = _ct_index(index)
    if len(x_values) != len(index_values):
        raise ValueError("X and INDEX must have the same length")
    groups = []
    start = 0
    n = len(x_values)
    while start < n:
        end = start + 1
        while end < n and _run_equal(index_kind, index_values[end], index_values[end - 1]):
            end += 1
        piece = x_values[start:end]
        if x_kind != "list":
            piece = list(piece)
        result = fun(piece, *args)
        groups.append((_group_name(index_kind, index_values[start]), _as_part(result)))
        start = end
    if not groups:
        return None
    if merge is _MISSING:
        merge = _c_merge
    if merge is None:
        raise TypeError("attempt to apply non-function")
    return merge(groups) if merge is _c_merge else _apply_merge(merge, groups)


def _fmatch(x, table, nomatch, incomparables, hash_only):
    if not _incomparables_off(incomparables):
        warnings.warn(
            "incomparables used in fmatch(), falling back to match()",
            UserWarning,
            stacklevel=3,
        )
        return _base_match(x, table, nomatch, incomparables)
    x_kind, x_values, _x_codes = _prepare(x, labels=True)
    if len(x_values) == 0:
        return []
    if table is None or _plain_length(table) == 0:
        if hash_only:
            return table
        missing = _as_integer(nomatch)
        return [missing] * len(x_values)
    y_kind, y_values, y_codes = _prepare(table, labels=False)
    kind = _common(x_kind, y_kind)
    if kind not in ("integer", "real", "character"):
        warnings.warn(
            "incompatible type, fastmatch() is falling back to match()",
            UserWarning,
            stacklevel=3,
        )
        return _base_match(x, table, nomatch, incomparables)
    x_values = _coerce(x_values, x_kind, kind, None)
    y_values = _coerce(y_values, y_kind, kind, y_codes)
    if hash_only:
        return Hashed(y_values)
    missing = _as_integer(nomatch)
    first = {}
    for position, value in enumerate(y_values, start=1):
        first.setdefault(_key(kind, value), position)
    return [first.get(_key(kind, value), missing) for value in x_values]


def _base_match(x, table, nomatch, incomparables):
    x_kind, x_values, _codes = _prepare(x, labels=True)
    if table is None or _plain_length(table) == 0:
        missing = _as_integer(nomatch)
        return [missing] * len(x_values)
    y_kind, y_values, y_codes = _prepare(table, labels=True)
    if x_kind == "factor":
        x_kind, x_values = "character", x_values
    if y_kind == "factor":
        y_kind, y_values, y_codes = "character", y_values, None
    kind = _common(x_kind, y_kind)
    if kind == "list":
        kind = "character"
    x_values = _coerce(x_values, x_kind, kind, None)
    y_values = _coerce(y_values, y_kind, kind, None if y_kind == "character" else y_codes)
    blocked = set()
    if not _incomparables_off(incomparables):
        raw = incomparables if isinstance(incomparables, (list, tuple, Factor)) else [incomparables]
        i_kind, i_values, i_codes = _prepare(raw, labels=True)
        if i_kind == "factor":
            i_kind = "character"
        i_values = _coerce(i_values, i_kind, kind, None)
        blocked = {_key(kind, value) for value in i_values}
    missing = _as_integer(nomatch)
    out = []
    for value in x_values:
        key = _key(kind, value)
        if key in blocked:
            out.append(missing)
            continue
        found = missing
        for position, other in enumerate(y_values, start=1):
            if _key(kind, other) == key:
                found = position
                break
        out.append(found)
    return out


def _prepare(value, labels):
    """Return kind, values, and factor codes.

    labels=True converts a factor or POSIXlt into character labels. The table
    keeps factor codes so a later character coercion prints those codes.
    """
    if isinstance(value, Factor):
        if labels:
            return "character", list(value.labels), None
        return "factor", list(value.codes), list(value.codes)
    if isinstance(value, PosixLt):
        if labels:
            return "character", list(value.values), None
        return "posixlt", list(value.values), None
    if isinstance(value, Integers):
        return "integer", [None if item is None else int(item) for item in value], None
    if isinstance(value, Characters):
        return "character", list(value), None
    if isinstance(value, Hashed):
        return _prepare(list(value), labels)
    if value is None:
        return "integer", [], None
    if isinstance(value, str):
        return "character", [value], None
    if isinstance(value, (bytes, bytearray)):
        raise TypeError("incompatible type, fastmatch() is falling back to match()")
    if not isinstance(value, (list, tuple)):
        value = [value]
    else:
        value = list(value)
    kinds = [_scalar_kind(item) for item in value]
    present = [kind for kind in kinds if kind is not None]
    if not present:
        return "integer", value, None
    kind = present[0]
    rank = _RANK[kind]
    for item in present[1:]:
        if _RANK[item] > rank:
            kind = item
            rank = _RANK[item]
    return kind, _normalize(value, kind), None


def _normalize(values, kind):
    if kind == "integer":
        return [None if value is None else int(value) for value in values]
    if kind == "real":
        out = []
        for value in values:
            if value is None:
                out.append(None)
            elif isinstance(value, float) and math.isnan(value):
                out.append(float("nan"))
            else:
                out.append(float(value))
        return out
    return list(values)


def _scalar_kind(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return "logical"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "real"
    if isinstance(value, str):
        return "character"
    if isinstance(value, complex):
        return "complex"
    raise TypeError("incompatible type, fastmatch() is falling back to match()")


_RANK = {
    "logical": 10,
    "integer": 13,
    "real": 14,
    "complex": 15,
    "character": 16,
    "factor": 13,
    "posixlt": 19,
    "list": 19,
}


def _common(left, right):
    if _RANK[left] >= 16 or _RANK[right] >= 16:
        return "character"
    return left if _RANK[left] >= _RANK[right] else right


def _coerce(values, source, target, codes):
    if source == "factor":
        values = list(codes)
        source = "integer"
    if source == target:
        return list(values)
    out = []
    for value in values:
        out.append(_coerce_one(value, source, target))
    return out


def _coerce_one(value, source, target):
    if value is None or target == "character":
        return None if value is None else _as_character(value, source)
    if target == "integer":
        if source == "logical":
            return int(value)
        if source == "real":
            if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
                return None
            return int(value)
        return int(value)
    if target == "real":
        if source == "logical":
            return float(int(value))
        return float(value)
    if target == "logical":
        if value is None:
            return None
        return bool(value)
    if target == "complex":
        return complex(value)
    return value


def _as_character(value, source):
    if value is None:
        return None
    if source == "logical":
        return "TRUE" if value else "FALSE"
    if source == "integer":
        return str(int(value))
    if source == "real":
        if isinstance(value, float) and math.isnan(value):
            return "NaN"
        if value == math.inf:
            return "Inf"
        if value == -math.inf:
            return "-Inf"
        return _decimal(float(value))
    if source == "complex":
        real = _decimal(float(value.real))
        imag = _decimal(float(value.imag))
        if imag.startswith("-"):
            return real + imag + "i"
        return real + "+" + imag + "i"
    return str(value)


def _decimal(number):
    """R as.character for a double: fifteen digits, and the shorter spelling."""
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    if number == 0:
        return "0"
    negative = number < 0
    scientific = format(abs(number), ".14e")
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


def _key(kind, value):
    if kind == "real":
        if value is None:
            return ("na",)
        if isinstance(value, float) and math.isnan(value):
            return ("nan",)
        if value == 0:
            return ("num", 0.0)
        return ("num", float(value))
    if kind == "complex":
        if value is None:
            return ("na",)
        if math.isnan(value.real) or math.isnan(value.imag):
            return ("nan",)
        return ("complex", value.real, value.imag)
    if value is None:
        return ("na",)
    return (kind, value)


def _as_integer(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return int(value)
    if isinstance(value, str):
        return int(value)
    raise TypeError("nomatch must be coercible to integer")


def _incomparables_off(value):
    if value is None or value is False:
        return True
    if isinstance(value, (list, tuple)) and len(value) == 1 and value[0] is False:
        return True
    return False


def _plain_length(value):
    if isinstance(value, Factor):
        return len(value)
    if isinstance(value, PosixLt):
        return len(value)
    if isinstance(value, str):
        return 1
    if value is None:
        return 0
    try:
        return len(value)
    except TypeError:
        return 1


def _ct_x(value):
    if isinstance(value, List):
        return "list", list(value)
    if isinstance(value, Factor):
        return "integer", list(value.codes)
    kind, values, _codes = _prepare(value, labels=False)
    if kind == "factor":
        return "integer", values
    if kind not in ("integer", "real", "character", "list"):
        raise ValueError("X must be either integer, real, character or generic vector (list)")
    return kind, values


def _ct_index(value):
    if isinstance(value, Factor):
        return "integer", list(value.codes)
    kind, values, _codes = _prepare(value, labels=False)
    if kind == "factor":
        return "integer", values
    if kind not in ("integer", "real", "character"):
        raise ValueError("INDEX must be either integer, real or character vector")
    return kind, values


def _run_equal(kind, left, right):
    if kind == "real":
        if left is None or right is None:
            return False
        if isinstance(left, float) and math.isnan(left):
            return False
        if isinstance(right, float) and math.isnan(right):
            return False
        return left == right
    return left == right


def _group_name(kind, value):
    if kind == "character":
        return "NA" if value is None else value
    if kind == "integer":
        return "-2147483648" if value is None else str(int(value))
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "nan"
    if value == math.inf:
        return "Inf"
    if value == -math.inf:
        return "-Inf"
    return format(float(value), ".6g")


def _as_part(result):
    if isinstance(result, Named):
        return list(result.values)
    if isinstance(result, (str, bytes)):
        return [result]
    if isinstance(result, (list, tuple)):
        return list(result)
    return [result]


def _c_merge(groups):
    values = []
    names = []
    for name, part in groups:
        if len(part) == 1:
            values.append(part[0])
            names.append(name)
        else:
            for offset, value in enumerate(part, start=1):
                values.append(value)
                names.append(f"{name}{offset}")
    return Named(values, names)


def _apply_merge(merge, groups):
    parts = [part if len(part) != 1 else part[0] for _name, part in groups]
    return merge(*parts)
