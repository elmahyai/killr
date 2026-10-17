"""Keep elements whose predicate is false or missing.

``discard`` is the complement of ``keep``. A logical predicate is used as a
mask: an element stays when the mask is ``FALSE`` or ``NA``. Any other
predicate is mapped. Each result must be one ``TRUE`` or one ``FALSE``, and
the false elements stay. A string, number, or list of those plucks; the
element stays when the plucked value is ``FALSE``.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping


class DiscardError(Exception):
    """Raised when discard cannot predicate, pluck, or subset."""


class Missing:
    """R's NA. Distinct from None (NULL) and from a quiet NaN."""

    def __repr__(self) -> str:
        return "NA"


NA = Missing()

_IDENTIFIER = re.compile(r"^(?:\.(?![0-9])|[A-Za-z])[A-Za-z0-9._]*$")
_OMITTED = object()


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
        raise DiscardError(
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

    def __str__(self) -> str:
        return r_print(self)


class List(_Vector):
    """An R list. None stored in values is NULL."""


class Integer(_Vector):
    """An R integer vector. NA is the missing sentinel."""


class Double(_Vector):
    """An R double vector. NA is the missing sentinel; NaN is float('nan')."""


class Logical(_Vector):
    """An R logical vector. NA is the missing sentinel."""


class Character(_Vector):
    """An R character vector. NA is the missing sentinel."""


class Complex(_Vector):
    """An R complex vector. NA is the missing sentinel."""


class Raw(_Vector):
    """An R raw vector. Values are integers in 0..255."""


_ATOMIC = (Integer, Double, Logical, Character, Complex, Raw)
_VECTORS = (List, *_ATOMIC)


def _length(value) -> int:
    if value is None:
        return 0
    if isinstance(value, _VECTORS):
        return len(value.values)
    return 1


def _coerce(value):
    """Turn a Python container into the R object discard subsets."""
    if value is None or isinstance(value, _VECTORS):
        return value
    if value is NA:
        return Logical([NA])
    if isinstance(value, Mapping):
        return List(
            [_coerce(item) for item in value.values()],
            list(value.keys()),
        )
    if isinstance(value, (list, tuple)):
        return List([_coerce(item) for item in value])
    if isinstance(value, str):
        return Character([value])
    if isinstance(value, bool):
        return Logical([value])
    if isinstance(value, int):
        return Double([float(value)])
    if isinstance(value, float):
        return Double([value])
    if isinstance(value, complex):
        return Complex([value])
    if isinstance(value, (bytes, bytearray)):
        return Raw([int(item) for item in value])
    raise DiscardError(
        f"Can't discard {type(value).__name__}. "
        "Use a list, dict, None, or an atomic vector."
    )


def _is_bool_token(value) -> bool:
    return value is True or value is False or value is NA


def _logical_mask(predicate):
    """Return mask values when predicate is a logical vector, else None."""
    if predicate is NA or predicate is True or predicate is False:
        return [predicate]
    if isinstance(predicate, Logical):
        return list(predicate.values)
    if isinstance(predicate, (list, tuple)) and predicate:
        if all(_is_bool_token(item) for item in predicate):
            return list(predicate)
    return None


def _keep_element(flag) -> bool:
    """discard keeps the element when the predicate is FALSE or NA."""
    if flag is NA:
        return True
    return not flag


def _subset(value, keep: list[bool]):
    if value is None:
        return None
    values = [item for item, wanted in zip(value.values, keep, strict=True) if wanted]
    if value.names is None:
        names = None
    else:
        names = [name for name, wanted in zip(value.names, keep, strict=True) if wanted]
    return type(value)(values, names)


def _items(value):
    if value is None:
        return
    names = value.names
    for offset, item in enumerate(value.values):
        name = None if names is None else names[offset]
        yield name, item


def _friendly(value) -> str:
    if value is None:
        return "NULL"
    if value is NA or (isinstance(value, Logical) and value.values == [NA]):
        return "`NA`"
    if isinstance(value, Logical):
        if not value.values:
            return "an empty logical vector"
        return "a logical vector"
    if isinstance(value, Integer):
        if not value.values:
            return "an empty integer vector"
        if len(value.values) == 1 and value.values[0] is NA:
            return "an integer `NA`"
        if len(value.values) == 1:
            return "an integer"
        return "an integer vector"
    if isinstance(value, Double):
        if not value.values:
            return "an empty numeric vector"
        item = value.values[0]
        if len(value.values) == 1 and (
            item is NA or (isinstance(item, float) and math.isnan(item))
        ):
            return "a numeric `NA`"
        if len(value.values) == 1:
            return "a number"
        return "a numeric vector"
    if isinstance(value, Character):
        if not value.values:
            return "an empty character vector"
        if len(value.values) == 1 and value.values[0] is NA:
            return "a character `NA`"
        if len(value.values) == 1:
            return "a string"
        return "a character vector"
    if isinstance(value, Complex):
        if not value.values:
            return "an empty complex vector"
        if len(value.values) == 1 and value.values[0] is NA:
            return "a complex `NA`"
        return "a complex vector"
    if isinstance(value, Raw):
        if not value.values:
            return "an empty raw vector"
        return "a raw vector"
    if isinstance(value, List):
        if not value.values:
            return "an empty list"
        return "a list"
    if isinstance(value, str):
        return "a string"
    if isinstance(value, bool):
        return "`TRUE`" if value else "`FALSE`"
    if isinstance(value, int):
        return "an integer `NA`" if value is NA else "an integer"
    if isinstance(value, float):
        if math.isnan(value):
            return "a numeric `NA`"
        return "a number"
    if isinstance(value, (list, tuple)):
        if not value:
            return "an empty list"
        return "a list"
    return f"a {type(value).__name__}"


def _require_bool(value):
    if value is True or value is False:
        return value
    if isinstance(value, Logical) and len(value.values) == 1:
        item = value.values[0]
        if item is True or item is False:
            return item
    raise DiscardError(
        "`.p()` must return a single `TRUE` or `FALSE`, "
        f"not {_friendly(value)}."
    )


def _indexed(index: int, name, exc: BaseException) -> DiscardError:
    lines = [f"In index: {index}."]
    if isinstance(name, str) and name != "":
        lines.append(f"With name: {name}.")
    lines.append(str(exc))
    return DiscardError("\n".join(lines))


def _offset_number(n: int, val: float):
    """purrr's non-strict numeric pluck offset, or None when it misses."""
    if not math.isfinite(val):
        return None
    if val < 0:
        val = n + val + 1
    if val == 0 or val < 0 or val > n:
        return None
    return int(val - 1)


def _offset_name(names, key):
    if not isinstance(key, str) or key == "":
        return None
    if not names:
        return None
    for offset, name in enumerate(names):
        if name is NA or name is None:
            continue
        if name == key:
            return offset
    return None


def _pluck_step(value, index, position: int):
    if isinstance(index, _ATOMIC):
        if len(index.values) != 1:
            raise DiscardError(
                f"Index {position} must have length 1, not {len(index.values)}."
            )
        index = index.values[0]
    if isinstance(index, (list, tuple, List)):
        raise DiscardError(
            f"Index {position} must be a character or numeric vector, not a list."
        )
    if isinstance(index, bool):
        word = "`TRUE`" if index else "`FALSE`"
        raise DiscardError(
            f"Index {position} must be a character or numeric vector, not {word}."
        )
    if value is None:
        return None
    if not isinstance(value, _VECTORS):
        return None
    if isinstance(index, str):
        offset = _offset_name(value.names, index)
    elif index is NA:
        offset = None
    elif isinstance(index, (int, float)):
        offset = _offset_number(len(value.values), float(index))
    else:
        raise DiscardError(
            f"Index {position} must be a character or numeric vector, "
            f"not {_friendly(index)}."
        )
    if offset is None:
        return None
    return value.values[offset]


def _pluck(value, indexes, default):
    current = value
    for position, index in enumerate(indexes, start=1):
        if current is None:
            return default
        current = _pluck_step(current, index, position)
    if current is None:
        return default
    return current


def _unwrap_index(index, position: int):
    if isinstance(index, _ATOMIC):
        if len(index.values) != 1:
            raise DiscardError(
                f"Index {position} must have length 1, not {len(index.values)}."
            )
        return index.values[0]
    if isinstance(index, (list, tuple, List)):
        raise DiscardError(
            f"Index {position} must be a character or numeric vector, not a list."
        )
    return index


def _indexes(predicate):
    if isinstance(predicate, str):
        return [predicate]
    if isinstance(predicate, (int, float)) and not isinstance(predicate, bool):
        return [predicate]
    if isinstance(predicate, (Character, Integer, Double)):
        return list(predicate.values)
    if isinstance(predicate, (list, tuple)):
        return [
            _unwrap_index(item, position)
            for position, item in enumerate(predicate, start=1)
        ]
    return None


def _as_predicate(predicate, args, kwargs, default):
    if predicate is None:
        raise DiscardError("Can't convert `.f`, `NULL`, to a function.")
    if callable(predicate) and not isinstance(predicate, type):

        def call(element, predicate=predicate, args=args, kwargs=kwargs):
            return predicate(element, *args, **kwargs)

        return call
    indexes = _indexes(predicate)
    if indexes is None:
        raise DiscardError("Can't convert `.f` to a function.")
    used = None if default is _OMITTED else default

    def call(element, indexes=tuple(indexes), used=used):
        return _pluck(element, indexes, used)

    return call


def discard(x, p, *args, default=_OMITTED, **kwargs):
    """Drop elements of x where p is TRUE.

    A logical p, including one NA, is a mask of the same length as x.
    Elements where that mask is FALSE or NA are kept. A callable is mapped
    across the elements; a string, integer, or list of those plucks first.
    default is the value used when a pluck misses, matching .default.
    Extra arguments are passed to a callable and ignored for a mask or a pluck.
    """
    original = _coerce(x)
    mask = _logical_mask(p)
    if mask is not None:
        if len(mask) != _length(original):
            raise DiscardError("length(.p) == length(.x) is not TRUE")
        where = mask
    else:
        predicate = _as_predicate(p, args, kwargs, default)
        where = []
        for index, (name, element) in enumerate(_items(original), start=1):
            try:
                result = predicate(element)
                where.append(_require_bool(result))
            except DiscardError as exc:
                raise _indexed(index, name, exc) from exc
            except Exception as exc:
                raise _indexed(index, name, exc) from exc
    keep = [_keep_element(flag) for flag in where]
    return _subset(original, keep)


def _quote_character(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _format_name(name: str) -> str:
    if _IDENTIFIER.fullmatch(name):
        return name
    escaped = name.replace("\\", "\\\\").replace("`", "\\`")
    return f"`{escaped}`"


def _tag(prefix: str, index: int, name) -> str:
    if isinstance(name, str) and name:
        return prefix + "$" + _format_name(name)
    if name is NA:
        return prefix + "$<NA>"
    return prefix + f"[[{index}]]"


def _print_double(item) -> str:
    if item is NA:
        return "NA"
    if isinstance(item, float) and math.isnan(item):
        return "NaN"
    if item == math.inf:
        return "Inf"
    if item == -math.inf:
        return "-Inf"
    text = format(item, ".15g")
    if text == "-0":
        return "0"
    return text


def _atomic_words(value) -> list[str]:
    if isinstance(value, Character):
        return ["NA" if item is NA else _quote_character(item) for item in value.values]
    if isinstance(value, Logical):
        words = []
        for item in value.values:
            if item is NA:
                words.append("NA")
            elif item:
                words.append("TRUE")
            else:
                words.append("FALSE")
        return words
    if isinstance(value, Integer):
        return ["NA" if item is NA else str(int(item)) for item in value.values]
    if isinstance(value, Double):
        return [_print_double(item) for item in value.values]
    if isinstance(value, Complex):
        words = []
        for item in value.values:
            if item is NA:
                words.append("NA")
            else:
                real = format(item.real, ".15g")
                imag = format(abs(item.imag), ".15g")
                sign = "+" if item.imag >= 0 else "-"
                words.append(f"{real}{sign}{imag}i")
        return words
    if isinstance(value, Raw):
        return [f"{int(item) & 255:02x}" for item in value.values]
    return [repr(item) for item in value.values]


def _empty_atomic(value) -> str:
    if isinstance(value, Character):
        label = "character(0)"
    elif isinstance(value, Logical):
        label = "logical(0)"
    elif isinstance(value, Integer):
        label = "integer(0)"
    elif isinstance(value, Double):
        label = "numeric(0)"
    elif isinstance(value, Complex):
        label = "complex(0)"
    elif isinstance(value, Raw):
        label = "raw(0)"
    else:
        label = "NULL"
    if value.names is not None:
        return "named " + label
    return label


def _print_atomic(value) -> str:
    if not value.values:
        return _empty_atomic(value)
    words = _atomic_words(value)
    if value.names is None:
        return "[1] " + " ".join(words)
    shown = []
    labels = []
    for name, word in zip(value.names, words):
        if name is NA:
            label = "<NA>"
        elif name is None:
            label = ""
        else:
            label = str(name)
        width = max(len(label), len(word))
        labels.append(label.rjust(width))
        shown.append(word.rjust(width))
    return " ".join(labels) + "\n" + " ".join(shown)


def _print_list(value, prefix: str) -> str:
    if not value.values:
        if value.names is not None:
            return "named list()"
        return "list()"
    parts = []
    for index, item in enumerate(value.values, start=1):
        name = None if value.names is None else value.names[index - 1]
        tag = _tag(prefix, index, name)
        if isinstance(item, List):
            # A nested list already ends in a blank line. R adds one more.
            parts.append(tag + "\n" + _print_list(item, tag) + "\n")
        elif item is None:
            parts.append(tag + "\nNULL\n\n")
        elif isinstance(item, _ATOMIC):
            parts.append(tag + "\n" + _print_atomic(item) + "\n\n")
        else:
            parts.append(tag + "\n" + str(item) + "\n\n")
    return "".join(parts)


def r_print(value) -> str:
    """Print a discard result the way R prints that list or vector."""
    if value is None:
        return "NULL"
    if isinstance(value, List):
        if not value.values:
            if value.names is not None:
                return "named list()"
            return "list()"
        return _print_list(value, "")
    if isinstance(value, _ATOMIC):
        return _print_atomic(value)
    return str(value)
