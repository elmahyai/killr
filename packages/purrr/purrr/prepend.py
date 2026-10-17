"""Insert values at the start of a vector, or before a subscript.

``prepend`` was deprecated in purrr 1.0.0. It still concatenates with ``c()``:
``NULL`` arguments are dropped, a list result keeps each element's type, and
an atomic result is coerced to one type. Names are kept. A name is filled
with ``""`` when another argument already has names.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Mapping


class PrependError(Exception):
    """Raised when prepend cannot concatenate or accept ``before``."""


class Missing:
    """R's NA. Distinct from None (NULL) and from a quiet NaN."""

    def __repr__(self) -> str:
        return "NA"


NA = Missing()

_DEPRECATION = (
    "`prepend()` was deprecated in purrr 1.0.0.\n"
    "\u2139 Please use append(after = 0) instead. "
)
_warned = False

_FLT_EPSILON = 2.0**-23


def _warn_once() -> None:
    global _warned
    if _warned:
        return
    _warned = True
    warnings.warn(_DEPRECATION, UserWarning, stacklevel=3)


def _names_of(names, n: int):
    if names is None:
        return None
    out = []
    for name in names:
        if name is None:
            out.append("")
        elif name is NA:
            out.append(NA)
        else:
            out.append(str(name))
    if len(out) != n:
        raise PrependError(
            f"names has length {len(out)} and the vector has length {n}."
        )
    return out


class _Vector:
    def __init__(self, values, names=None):
        self.values = list(values)
        self.names = _names_of(names, len(self.values))

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        body = ", ".join(repr(value) for value in self.values)
        if self.names is None:
            return f"{type(self).__name__}([{body}])"
        return f"{type(self).__name__}([{body}], names={self.names!r})"


class List(_Vector):
    """An R list. None stored in values is NULL."""

    def __init__(self, values, names=None):
        stored = [_as_list_element(value) for value in values]
        super().__init__(stored, names)


class Integer(_Vector):
    """An R integer vector. NA is the missing sentinel."""

    def __init__(self, values, names=None):
        super().__init__([_as_integer(value) for value in values], names)


class Double(_Vector):
    """An R double vector. NA is the missing sentinel; NaN is float('nan')."""

    def __init__(self, values, names=None):
        super().__init__([_as_double(value) for value in values], names)


class Logical(_Vector):
    """An R logical vector. NA is the missing sentinel."""

    def __init__(self, values, names=None):
        super().__init__([_as_logical(value) for value in values], names)


class Character(_Vector):
    """An R character vector. NA is the missing sentinel."""

    def __init__(self, values, names=None):
        super().__init__([_as_character_scalar(value) for value in values], names)


class Complex(_Vector):
    """An R complex vector. NA is the missing sentinel."""

    def __init__(self, values, names=None):
        super().__init__([_as_complex(value) for value in values], names)


class Raw(_Vector):
    """An R raw vector. Values are integers in 0..255."""

    def __init__(self, values, names=None):
        super().__init__([_as_raw(value) for value in values], names)


_ATOMIC = (Integer, Double, Logical, Character, Complex, Raw)
_VECTORS = (List, *_ATOMIC)

_RANK = {
    Raw: 1,
    Logical: 2,
    Integer: 3,
    Double: 4,
    Complex: 5,
    Character: 6,
    List: 7,
}


def _as_integer(value):
    if value is NA:
        return NA
    if isinstance(value, bool) or not isinstance(value, int):
        raise PrependError("an integer vector needs integers or NA.")
    return value


def _as_double(value):
    if value is NA:
        return NA
    if isinstance(value, bool):
        raise PrependError("a double vector needs floats or NA.")
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    raise PrependError("a double vector needs floats or NA.")


def _as_logical(value):
    if value is NA:
        return NA
    if isinstance(value, bool):
        return value
    raise PrependError("a logical vector needs True, False, or NA.")


def _as_character_scalar(value):
    if value is NA:
        return NA
    if isinstance(value, str):
        return value
    raise PrependError("a character vector needs strings or NA.")


def _as_complex(value):
    if value is NA:
        return NA
    if isinstance(value, bool):
        raise PrependError("a complex vector needs complex values or NA.")
    if isinstance(value, complex):
        return value
    if isinstance(value, (int, float)):
        return complex(value, 0.0)
    raise PrependError("a complex vector needs complex values or NA.")


def _as_raw(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise PrependError("a raw vector needs integers in 0..255.")
    return value


def _as_list_element(value):
    if value is None:
        return None
    if value is NA:
        return Logical([NA])
    if isinstance(value, _VECTORS):
        return value
    if isinstance(value, Mapping):
        return List(list(value.values()), list(value.keys()))
    if isinstance(value, list):
        return List(value)
    return _scalar(value)


def _scalar(value):
    if isinstance(value, str):
        return Character([value])
    if isinstance(value, bool):
        return Logical([value])
    if isinstance(value, int):
        return Integer([value])
    if isinstance(value, float):
        return Double([value])
    if isinstance(value, complex):
        return Complex([value])
    raise PrependError(
        f"Can't prepend {type(value).__name__}. "
        "Use a list, dict, None, string, number, or an atomic vector."
    )


def _coerce(value):
    """Turn a Python value into the R object prepend concatenates."""
    if value is None:
        return None
    if value is NA:
        return Logical([NA])
    if isinstance(value, _VECTORS):
        return value
    if isinstance(value, Mapping):
        return List(list(value.values()), list(value.keys()))
    if isinstance(value, list):
        return List(value)
    return _scalar(value)


def _is_nan(value) -> bool:
    return isinstance(value, float) and math.isnan(value)


def _character_double(value: float) -> str:
    """R as.character for a finite or infinite double. NA is handled by the caller."""
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
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


def _character_complex(value) -> str:
    if value is NA:
        return NA
    real = _character_double(value.real)
    imag = value.imag
    # -0 is not < 0, so a negative-zero imaginary part keeps the plus sign.
    if imag < 0.0:
        return f"{real}-{_character_double(abs(imag))}i"
    return f"{real}+{_character_double(imag)}i"


def _as_text(value, source) -> str:
    """R as.character of one atomic scalar. A missing value stays NA."""
    if value is NA:
        return NA
    if source is Logical:
        return "TRUE" if value else "FALSE"
    if source is Integer:
        return str(value)
    if source is Raw:
        return f"{value:02x}"
    if source is Double:
        return _character_double(value)
    if source is Complex:
        return _character_complex(value)
    return value


def _coerce_scalar(value, source, dest):
    if dest is source:
        return value
    if dest is Character:
        return _as_text(value, source)
    if value is NA and source is not Raw and source is not Double:
        return NA
    if source is Double and value is NA:
        return NA
    if dest is Logical:
        if source is Raw:
            return value != 0
        raise PrependError("can't coerce to logical.")
    if dest is Integer:
        if source is Logical:
            return NA if value is NA else (1 if value else 0)
        if source is Raw:
            return value
        raise PrependError("can't coerce to integer.")
    if dest is Double:
        if value is NA:
            return NA
        if source is Logical:
            return 1.0 if value else 0.0
        if source is Integer or source is Raw:
            return float(value)
        if source is Double:
            return value
        raise PrependError("can't coerce to double.")
    if dest is Complex:
        if value is NA:
            return NA
        if source is Double:
            return complex(value, 0.0)
        if source is Logical:
            return complex(1.0 if value else 0.0, 0.0)
        if source is Integer or source is Raw:
            return complex(float(value), 0.0)
        if source is Complex:
            return value
        raise PrependError("can't coerce to complex.")
    raise PrependError("can't coerce that atomic value.")


def combine(*args):
    """R's default ``c()`` for NULL, atomic vectors, and lists."""
    parts = [_coerce(arg) for arg in args]
    kind = None
    rank = 0
    for part in parts:
        if part is None:
            continue
        part_rank = _RANK[type(part)]
        if part_rank > rank:
            rank = part_rank
            kind = type(part)
    if kind is None:
        return None
    has_names = any(part.names is not None for part in parts if part is not None)
    values = []
    names = [] if has_names else None
    for part in parts:
        if part is None:
            continue
        if isinstance(part, List):
            for index, element in enumerate(part.values):
                values.append(element)
                if names is not None:
                    names.append("" if part.names is None else part.names[index])
            continue
        same = kind is type(part)
        for index, element in enumerate(part.values):
            if kind is List:
                values.append(type(part)([element]))
            elif same:
                values.append(element)
            else:
                values.append(_coerce_scalar(element, type(part), kind))
            if names is not None:
                names.append("" if part.names is None else part.names[index])
    return kind(values, names)


def _colon(start: float, end: float) -> list[float]:
    if math.isnan(start) or math.isnan(end):
        raise PrependError("NA/NaN argument")
    width = abs(end - start)
    count = int(width + 1.0 + _FLT_EPSILON)
    if start <= end:
        return [start + index for index in range(count)]
    return [start - index for index in range(count)]


def _exact_int(value: float) -> bool:
    if not math.isfinite(value) or abs(value) > 2**53:
        return False
    return value == math.trunc(value)


def _subset_indices(value, indices: list[float]):
    if value is None:
        return None
    chosen = []
    has_positive = False
    has_negative = False
    for index in indices:
        truncated = int(index)
        if truncated == 0:
            continue
        if truncated < 0:
            has_negative = True
        else:
            has_positive = True
        chosen.append(truncated)
    if has_positive and has_negative:
        raise PrependError("only 0's may be mixed with negative subscripts")
    n = len(value.values)
    if has_negative and not has_positive:
        drop = {abs(index) for index in chosen}
        keep = [offset for offset in range(n) if (offset + 1) not in drop]
    else:
        keep = []
        for index in chosen:
            if index > n:
                keep.append(None)
            else:
                keep.append(index - 1)
    picked = []
    names = [] if value.names is not None else None
    gained_name = False
    for offset in keep:
        if offset is None:
            picked.append(_missing_like(value))
            if names is not None:
                names.append(NA)
            else:
                gained_name = True
            continue
        picked.append(value.values[offset])
        if names is not None:
            names.append(value.names[offset])
        elif gained_name:
            names = [""] * (len(picked) - 1) + [NA]
            gained_name = False
    if gained_name:
        names = [""] * (len(picked) - 1) + [NA]
    return type(value)(picked, names)


def _missing_like(value):
    if isinstance(value, List):
        return None
    if isinstance(value, Raw):
        return 0
    return NA


def _subset_colon(value, start, end):
    start_f = float(start)
    end_f = float(end)
    n = 0 if value is None else len(value.values)
    if (
        value is not None
        and _exact_int(start_f)
        and _exact_int(end_f)
        and 1 <= start_f <= end_f <= n
    ):
        left = int(start_f) - 1
        right = int(end_f)
        names = None if value.names is None else value.names[left:right]
        return type(value)(value.values[left:right], names)
    return _subset_indices(value, _colon(start_f, end_f))


def _before_values(before):
    if isinstance(before, (Complex, Raw, List)):
        raise PrependError(
            "comparison of these types is not implemented"
        )
    if isinstance(before, _ATOMIC):
        return list(before.values)
    if isinstance(before, (list, tuple)):
        raise PrependError(
            "comparison of these types is not implemented"
        )
    return [before]


def _compare_text(left, right, op) -> bool:
    left_text = left if isinstance(left, str) else _number_text(left)
    right_text = right if isinstance(right, str) else _number_text(right)
    if op == ">":
        return left_text > right_text
    if op == "<=":
        return left_text <= right_text
    return left_text == right_text


def _number_text(value) -> str:
    if value is NA or _is_nan(value):
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _character_double(value)
    return str(value)


def _missing_compare(value) -> bool:
    return value is NA or _is_nan(value)


def _r_gt(left, right):
    if isinstance(left, str) or isinstance(right, str):
        return _compare_text(left, right, ">")
    if _missing_compare(left) or _missing_compare(right):
        return NA
    return float(left) > float(right)


def _r_le(left, right):
    if isinstance(left, str) or isinstance(right, str):
        return _compare_text(left, right, "<=")
    if _missing_compare(left) or _missing_compare(right):
        return NA
    return float(left) <= float(right)


def _is_one(value) -> bool:
    if isinstance(value, str):
        return value == "1"
    if isinstance(value, bool):
        return value
    if _missing_compare(value):
        return False
    return float(value) == 1.0


def _numeric_before(value) -> float:
    if isinstance(value, str):
        raise PrependError("non-numeric argument to binary operator")
    if _missing_compare(value):
        raise PrependError("NA/NaN argument")
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    return float(value)


def _before_accepts(before, n: int):
    """The stopifnot test ``is.null(before) || (before > 0 && before <= n)``."""
    if before is None:
        return True, None
    values = _before_values(before)
    if len(values) != 1:
        if len(values) == 0:
            return False, None
        raise PrependError(
            f"'length = {len(values)}' in coercion to 'logical(1)'"
        )
    value = values[0]
    left = _r_gt(value, 0)
    right = _r_le(value, n)
    if left is True and right is True:
        return True, value
    return False, value


def prepend(x, values, before=None):
    """Insert ``values`` at the start of ``x``, or before a 1-based subscript.

    ``before = None`` matches R's ``NULL`` and inserts at the start, including
    when ``x`` is empty. The result is R's ``c()`` of the pieces.
    """
    _warn_once()
    original = _coerce(x)
    inserted = _coerce(values)
    n = 0 if original is None else len(original.values)
    ok, position = _before_accepts(before, n)
    if not ok:
        raise PrependError(
            "is.null(before) || (before > 0 && before <= n) is not TRUE"
        )
    if position is None or _is_one(position):
        return combine(inserted, original)
    numeric = _numeric_before(position)
    return combine(
        _subset_colon(original, 1, numeric - 1),
        inserted,
        _subset_colon(original, numeric, n),
    )


def _quote_character(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return '"' + escaped + '"'


def _print_atomic(value) -> str:
    if isinstance(value, Character):
        if not value.values:
            return "character(0)"
        shown = " ".join(
            "NA" if item is NA else _quote_character(item) for item in value.values
        )
        return f"[1] {shown}"
    if isinstance(value, Logical):
        if not value.values:
            return "logical(0)"
        words = []
        for item in value.values:
            if item is NA:
                words.append("NA")
            elif item:
                words.append("TRUE")
            else:
                words.append("FALSE")
        return "[1] " + " ".join(words)
    if isinstance(value, Integer):
        if not value.values:
            return "integer(0)"
        words = ["NA" if item is NA else str(item) for item in value.values]
        return "[1] " + " ".join(words)
    if isinstance(value, Double):
        if not value.values:
            return "numeric(0)"
        return "[1] " + " ".join(_character_double(item) if item is not NA else "NA" for item in value.values)
    if isinstance(value, Complex):
        if not value.values:
            return "complex(0)"
        words = [_character_complex(item) if item is not NA else "NA" for item in value.values]
        return "[1] " + " ".join(words)
    if isinstance(value, Raw):
        if not value.values:
            return "raw(0)"
        return "[1] " + " ".join(f"{item:02x}" for item in value.values)
    return repr(value)


def r_print(value) -> str:
    """Print a prepend result the way R prints that list or vector."""
    if value is None:
        return "NULL\n"
    if isinstance(value, List):
        if not value.values:
            if value.names is not None:
                return "named list()\n"
            return "list()\n"
        lines = []
        names = value.names
        for index, item in enumerate(value.values, start=1):
            name = "" if names is None else names[index - 1]
            if isinstance(name, str) and name:
                lines.append("$" + name)
            else:
                lines.append(f"[[{index}]]")
            if item is None:
                lines.append("NULL")
            elif isinstance(item, List):
                lines.append(r_print(item).rstrip("\n"))
            else:
                lines.append(_print_atomic(item))
            lines.append("")
        return "\n".join(lines) + "\n"
    if isinstance(value, _ATOMIC):
        return _print_atomic(value) + "\n"
    return str(value) + "\n"
