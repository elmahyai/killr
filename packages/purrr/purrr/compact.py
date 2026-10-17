"""Discard list and vector elements whose predicate result is empty.

``compact`` maps ``.p`` (identity by default), then drops every element for
which that result has length zero. ``NULL`` and a length-zero vector are
empty. A length-one ``NA``, ``NaN``, ``0``, ``FALSE``, or ``""`` is not.
"""

from __future__ import annotations

import math
import re
from collections.abc import Mapping


class CompactError(Exception):
    """Raised when compact cannot map or pluck."""


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
        raise CompactError(
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


class Raw(_Vector):
    """An R raw vector. Values are integers in 0..255."""


_ATOMIC = (Integer, Double, Logical, Character, Raw)
_VECTORS = (List, *_ATOMIC)


def _coerce(value):
    """Turn a Python container into the R object compact walks."""
    if value is None:
        return None
    if value is NA:
        return Logical([NA])
    if isinstance(value, _VECTORS):
        kind = type(value)
        return kind(
            [_coerce(item) if kind is List else item for item in value.values],
            None if value.names is None else list(value.names),
        )
    if isinstance(value, Mapping):
        return List(
            [_coerce(item) for item in value.values()],
            list(value.keys()),
        )
    if isinstance(value, list):
        return List([_coerce(item) for item in value])
    if isinstance(value, str):
        return Character([value])
    if isinstance(value, bool):
        return Logical([value])
    if isinstance(value, int):
        return Double([float(value)])
    if isinstance(value, float):
        return Double([value])
    raise CompactError(
        f"Can't compact {type(value).__name__}. "
        "Use a list, dict, None, or an atomic vector."
    )


def _is_empty(value) -> bool:
    """rlang::is_empty in purrr 1.2.2, which is length(x) == 0."""
    if value is None:
        return True
    if isinstance(value, _VECTORS):
        return len(value.values) == 0
    if isinstance(value, str) or value is NA or isinstance(value, (bool, int, float)):
        return False
    if isinstance(value, (list, tuple, dict)):
        return len(value) == 0
    try:
        return len(value) == 0
    except TypeError:
        return False


def _length(value) -> int:
    if value is None:
        return 0
    if isinstance(value, _VECTORS):
        return len(value.values)
    return 1


def _scalar(value, offset: int):
    if isinstance(value, List):
        return value.values[offset]
    kind = type(value)
    return kind([value.values[offset]])


def _extract_position(value, index):
    n = _length(value)
    position = float(index)
    if not math.isfinite(position):
        return None
    if position < 0:
        position = n + position + 1
    if position == 0 or position < 0 or position > n:
        return None
    offset = int(position - 1)
    if offset < 0 or offset >= n:
        return None
    return _scalar(value, offset)


def _extract_name(value, name):
    if not isinstance(name, str) or name == "":
        return None
    names = value.names if isinstance(value, _VECTORS) else None
    if not names:
        return None
    for offset, stored in enumerate(names):
        if stored is NA or stored is None or stored == "":
            continue
        if stored == name:
            return _scalar(value, offset)
    return None


def _extract(value, index):
    if callable(index) and not isinstance(index, type):
        return index(value)
    if isinstance(index, str):
        return _extract_name(value, index)
    if isinstance(index, bool) or index is NA:
        return None
    if isinstance(index, (int, float)):
        return _extract_position(value, index)
    if isinstance(index, _ATOMIC) and len(index.values) == 1:
        return _extract(value, index.values[0])
    raise CompactError("Index must be a character or numeric vector.")


def _pluck(value, indexes, default=None):
    current = value
    for index in indexes:
        if callable(index) and not isinstance(index, type):
            current = index(current)
            continue
        if current is None:
            return default
        current = _extract(current, index)
    if current is None:
        return default
    return current


def _unwrap_index(index):
    if isinstance(index, _ATOMIC):
        if len(index.values) != 1:
            raise CompactError(
                f"Index must be length 1, not {len(index.values)}."
            )
        return index.values[0]
    if isinstance(index, List):
        raise CompactError("Index must be a character or numeric vector.")
    return index


def _indexes(predicate):
    if isinstance(predicate, str):
        return [predicate]
    if isinstance(predicate, bool):
        return None
    if isinstance(predicate, (int, float)):
        return [predicate]
    if isinstance(predicate, _ATOMIC):
        return list(predicate.values)
    if isinstance(predicate, (list, tuple)):
        return [_unwrap_index(item) for item in predicate]
    if isinstance(predicate, List):
        return [_unwrap_index(item) for item in predicate.values]
    return None


def _as_mapper(predicate):
    if predicate is None:
        raise CompactError("Can't convert `.f`, `NULL`, to a function.")
    if isinstance(predicate, (bool, Logical, Missing)):
        raise CompactError("Can't convert `.f`, a logical vector, to a function.")
    if callable(predicate) and not isinstance(predicate, type):
        return predicate
    indexes = _indexes(predicate)
    if indexes is None:
        raise CompactError("Can't convert `.f` to a function.")

    def mapper(value, indexes=tuple(indexes)):
        return _pluck(value, indexes)

    return mapper


def _items(value):
    if value is None:
        return
    if isinstance(value, List):
        yield from value.values
        return
    if isinstance(value, _ATOMIC):
        for offset in range(len(value.values)):
            yield _scalar(value, offset)
        return
    raise CompactError(
        f"Can't compact {type(value).__name__}. "
        "Use a list, dict, None, or an atomic vector."
    )


def _subset(value, keep: list[bool]):
    if value is None:
        return None
    values = [item for item, wanted in zip(value.values, keep) if wanted]
    if value.names is None:
        names = None
    else:
        names = [name for name, wanted in zip(value.names, keep) if wanted]
    return type(value)(values, names)


def identity(value):
    """The default predicate. The element is kept when it has a length."""
    return value


def compact(x, p=_OMITTED):
    """Drop elements of x for which p(element) is empty.

    p defaults to identity. A callable is used as itself. A string, integer,
    or list of those is a pluck specification: the element is dropped when
    the plucked value is NULL or has length zero. An explicit None is NULL
    and is an error, matching as_mapper(NULL).
    """
    mapper = identity if p is _OMITTED else _as_mapper(p)
    original = _coerce(x)
    keep: list[bool] = []
    for index, item in enumerate(_items(original), start=1):
        try:
            mapped = mapper(item)
        except CompactError:
            raise
        except Exception as exc:
            raise CompactError(f"In index: {index}. {exc}") from exc
        keep.append(not _is_empty(mapped))
    return _subset(original, keep)


def _quote_character(text: str) -> str:
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _format_name(name: str) -> str:
    if _IDENTIFIER.fullmatch(name):
        return name
    escaped = name.replace("\\", "\\\\").replace("`", "\\`")
    return f"`{escaped}`"


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
        words = [_print_double(item) for item in value.values]
        return "[1] " + " ".join(words)
    if isinstance(value, Raw):
        if not value.values:
            return "raw(0)"
        words = [f"{int(item):02x}" for item in value.values]
        return "[1] " + " ".join(words)
    return repr(value)


def _print_double(item) -> str:
    if item is NA:
        return "NA"
    if isinstance(item, float) and math.isnan(item):
        return "NaN"
    if item == math.inf:
        return "Inf"
    if item == -math.inf:
        return "-Inf"
    return format(item, ".15g")


def r_print(value) -> str:
    """Print a compact result the way R prints that list or vector."""
    if value is None:
        return "NULL"
    if isinstance(value, List):
        if not value.values:
            if value.names is not None:
                return "named list()"
            return "list()"
        lines = []
        names = value.names
        for index, item in enumerate(value.values, start=1):
            name = "" if names is None else names[index - 1]
            if isinstance(name, str) and name:
                lines.append("$" + _format_name(name))
            else:
                lines.append(f"[[{index}]]")
            lines.append(r_print(item))
            lines.append("")
        return "\n".join(lines) + "\n"
    if isinstance(value, _ATOMIC):
        return _print_atomic(value)
    return str(value)
