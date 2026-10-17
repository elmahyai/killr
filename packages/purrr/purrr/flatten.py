"""Flatten one level of a list.

``flatten`` was superseded in purrr 1.0.0 by ``list_flatten``. The installed
``lifecycle::signal_stage`` does not signal, so this translation does not warn.

Each direct element must be a vector or ``NULL``. ``NULL`` and length-zero
vectors contribute nothing. An atomic vector becomes one length-one vector
per element, and a list contributes its elements unchanged. Names on an
element replace the parent's name. A length-one element with no names of its
own keeps the parent's name. R 4.5 fills an unused name with ``""``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping


class FlattenError(Exception):
    """Raised when flatten cannot accept a value."""


class Missing:
    """R's NA. Distinct from None (NULL) and from a quiet NaN."""

    def __repr__(self) -> str:
        return "NA"


NA = Missing()

_IDENTIFIER = re.compile(r"^(?:\.(?![0-9])|[A-Za-z])[A-Za-z0-9._]*$")


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
        raise FlattenError(
            f"names has length {len(out)} and the vector has length {n}."
        )
    return out


class _Vector:
    def __init__(self, values, names=None, attrs=None):
        self.values = list(values)
        self.names = _names_of(names, len(self.values))
        self.attrs = dict(attrs) if attrs else None

    def __len__(self) -> int:
        return len(self.values)

    def __repr__(self) -> str:
        body = ", ".join(repr(value) for value in self.values)
        if self.names is None:
            return f"{type(self).__name__}([{body}])"
        return f"{type(self).__name__}([{body}], names={self.names!r})"


class List(_Vector):
    """An R list. None stored in values is NULL."""


class Integer(_Vector):
    """An R integer vector. NA is the missing sentinel."""

    def __init__(self, values, names=None, attrs=None):
        super().__init__([_as_integer(value) for value in values], names, attrs)


class Double(_Vector):
    """An R double vector. NA is the missing sentinel; NaN is float('nan')."""

    def __init__(self, values, names=None, attrs=None):
        super().__init__([_as_double(value) for value in values], names, attrs)


class Logical(_Vector):
    """An R logical vector. NA is the missing sentinel."""

    def __init__(self, values, names=None, attrs=None):
        super().__init__([_as_logical(value) for value in values], names, attrs)


class Character(_Vector):
    """An R character vector. NA is the missing sentinel."""

    def __init__(self, values, names=None, attrs=None):
        super().__init__(
            [_as_character(value) for value in values], names, attrs
        )


class Complex(_Vector):
    """An R complex vector. NA is the missing sentinel."""

    def __init__(self, values, names=None, attrs=None):
        super().__init__([_as_complex(value) for value in values], names, attrs)


class Raw(_Vector):
    """An R raw vector. Values are integers in 0..255."""

    def __init__(self, values, names=None, attrs=None):
        super().__init__([_as_raw(value) for value in values], names, attrs)


_ATOMIC = (Integer, Double, Logical, Character, Complex, Raw)
_VECTORS = (List, *_ATOMIC)


def _as_integer(value):
    if value is NA:
        return NA
    if isinstance(value, bool) or not isinstance(value, int):
        raise FlattenError("an integer vector needs integers or NA.")
    return value


def _as_double(value):
    if value is NA:
        return NA
    if isinstance(value, bool):
        raise FlattenError("a double vector needs floats or NA.")
    if isinstance(value, int):
        return float(value)
    if isinstance(value, float):
        return value
    raise FlattenError("a double vector needs floats or NA.")


def _as_logical(value):
    if value is NA:
        return NA
    if isinstance(value, bool):
        return value
    raise FlattenError("a logical vector needs True, False, or NA.")


def _as_character(value):
    if value is NA:
        return NA
    if isinstance(value, str):
        return value
    raise FlattenError("a character vector needs strings or NA.")


def _as_complex(value):
    if value is NA:
        return NA
    if isinstance(value, bool):
        raise FlattenError("a complex vector needs complex values or NA.")
    if isinstance(value, complex):
        return value
    if isinstance(value, (int, float)):
        return complex(value, 0.0)
    raise FlattenError("a complex vector needs complex values or NA.")


def _as_raw(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 255:
        raise FlattenError("a raw vector needs integers in 0..255.")
    return value


def _friendly(value) -> str:
    """rlang's friendly type for the values flatten rejects."""
    if value is None:
        return "NULL"
    if isinstance(value, Double):
        return "a number" if len(value) == 1 else "a double vector"
    if isinstance(value, Integer):
        return "an integer" if len(value) == 1 else "an integer vector"
    if isinstance(value, Logical):
        if len(value) == 1:
            item = value.values[0]
            if item is NA:
                return "a missing value"
            return "`TRUE`" if item else "`FALSE`"
        return "a logical vector"
    if isinstance(value, Character):
        return "a string" if len(value) == 1 else "a character vector"
    if isinstance(value, Complex):
        return "a complex number" if len(value) == 1 else "a complex vector"
    if isinstance(value, Raw):
        return "a raw value" if len(value) == 1 else "a raw vector"
    if isinstance(value, bool):
        return "`TRUE`" if value else "`FALSE`"
    if isinstance(value, int):
        return "an integer"
    if isinstance(value, float):
        return "a number"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, complex):
        return "a complex number"
    if isinstance(value, bytes):
        return "a raw value" if len(value) == 1 else "a raw vector"
    if callable(value):
        return "a function"
    return f"a {type(value).__name__} object"


def _copy_names(names):
    if names is None:
        return None
    return list(names)


def _coerce_inner(value):
    """Coerce a value that already sits inside a list. Do not type-check it."""
    if value is None:
        return None
    if isinstance(value, List):
        return List(
            [_coerce_inner(item) for item in value.values],
            _copy_names(value.names),
        )
    if isinstance(value, _ATOMIC):
        return value
    if isinstance(value, Mapping):
        return List(
            [_coerce_inner(item) for item in value.values()],
            [str(key) for key in value.keys()],
        )
    if isinstance(value, list):
        return List([_coerce_inner(item) for item in value])
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
    return value


def _coerce_element(value, index: int):
    """Coerce one direct element. A non-vector is the installed type error."""
    if value is None:
        return None
    if isinstance(value, _ATOMIC):
        return value
    if isinstance(value, List):
        return List(
            [_coerce_inner(item) for item in value.values],
            _copy_names(value.names),
        )
    if isinstance(value, Mapping):
        return List(
            [_coerce_inner(item) for item in value.values()],
            [str(key) for key in value.keys()],
        )
    if isinstance(value, list):
        return List([_coerce_inner(item) for item in value])
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
    raise FlattenError(
        f"`.x[[{index}]]` must be a vector, not {_friendly(value)}."
    )


def _as_list(value) -> List:
    if isinstance(value, List):
        elements = [
            _coerce_element(item, index)
            for index, item in enumerate(value.values, start=1)
        ]
        return List(elements, _copy_names(value.names))
    if isinstance(value, Mapping):
        elements = [
            _coerce_element(item, index)
            for index, item in enumerate(value.values(), start=1)
        ]
        return List(elements, [str(key) for key in value.keys()])
    if isinstance(value, list):
        elements = [
            _coerce_element(item, index)
            for index, item in enumerate(value, start=1)
        ]
        return List(elements)
    raise FlattenError(f"`.x` must be a list, not {_friendly(value)}.")


def _scalar(vector, offset: int):
    """One atomic element as a new length-one vector. Attributes are not kept."""
    return type(vector)([vector.values[offset]])


def _usable_parent_name(name) -> bool:
    return name is not NA and name != ""


def flatten(x):
    """Flatten one level of a list.

    ``x`` is a list, a dict, or None is not accepted. Top-level ``NULL`` is
    dropped. A list element is copied as it is, so a factor stored inside a
    list stays a factor, while a factor stored directly becomes integers.
    """
    original = _as_list(x)
    parent_names = original.names
    has_names = False
    total = 0
    for index, element in enumerate(original.values):
        if element is None:
            continue
        total += len(element.values)
        if has_names:
            continue
        if element.names is not None:
            has_names = True
        elif (
            len(element.values) == 1
            and parent_names is not None
            and _usable_parent_name(parent_names[index])
        ):
            has_names = True

    values = []
    names = [] if has_names else None
    for index, element in enumerate(original.values):
        if element is None:
            continue
        count = len(element.values)
        element_names = element.names
        named = element_names is not None
        for offset in range(count):
            if isinstance(element, List):
                values.append(element.values[offset])
            else:
                values.append(_scalar(element, offset))
            if names is None:
                continue
            if named:
                names.append(element_names[offset])
            elif count == 1:
                if parent_names is not None:
                    names.append(parent_names[index])
                else:
                    names.append("")
            else:
                # Allocated names start as "" on this R.
                names.append("")
    return List(values, names)


def _quote_character(text: str) -> str:
    escaped = (
        text.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )
    return '"' + escaped + '"'


def _format_name(name: str) -> str:
    if _IDENTIFIER.fullmatch(name):
        return name
    escaped = name.replace("\\", "\\\\").replace("`", "\\`")
    return f"`{escaped}`"


def _print_double(item) -> str:
    if item is NA:
        return "NA"
    if isinstance(item, float) and math.isnan(item):
        return "NaN"
    if item == math.inf:
        return "Inf"
    if item == -math.inf:
        return "-Inf"
    if item == 0.0:
        return "0"
    if isinstance(item, float) and item.is_integer() and abs(item) < 1e15:
        return str(int(item))
    return format(item, ".7g")


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
        if value.attrs and value.attrs.get("class") == "factor":
            labels = value.attrs.get("levels") or []
            words = []
            for item in value.values:
                if item is NA:
                    words.append("NA")
                else:
                    words.append(labels[item - 1])
            return "[1] " + " ".join(words)
        if not value.values:
            return "integer(0)"
        words = ["NA" if item is NA else str(item) for item in value.values]
        return "[1] " + " ".join(words)
    if isinstance(value, Double):
        if not value.values:
            return "numeric(0)"
        return "[1] " + " ".join(_print_double(item) for item in value.values)
    if isinstance(value, Complex):
        if not value.values:
            return "complex(0)"
        words = []
        for item in value.values:
            if item is NA:
                words.append("NA")
            else:
                words.append(f"{_print_double(item.real)}+{_print_double(item.imag)}i")
        return "[1] " + " ".join(words)
    if isinstance(value, Raw):
        if not value.values:
            return "raw(0)"
        return "[1] " + " ".join(f"{item:02x}" for item in value.values)
    return repr(value)


def r_print(value) -> str:
    """Print a flatten result the way R prints that list or vector."""
    if value is None:
        return "NULL\n"
    if isinstance(value, List):
        if not value.values:
            if value.names is not None:
                return "named list()\n"
            return "list()\n"
        lines = []
        stored_names = value.names
        for index, item in enumerate(value.values, start=1):
            name = "" if stored_names is None else stored_names[index - 1]
            if isinstance(name, str) and name:
                lines.append("$" + _format_name(name))
            else:
                lines.append(f"[[{index}]]")
            if item is None:
                lines.append("NULL")
            elif isinstance(item, List):
                lines.append(r_print(item).rstrip("\n"))
            elif isinstance(item, _ATOMIC):
                lines.append(_print_atomic(item))
            else:
                lines.append(str(item))
            lines.append("")
        return "\n".join(lines) + "\n"
    if isinstance(value, _ATOMIC):
        return _print_atomic(value) + "\n"
    return str(value) + "\n"
