"""Predicates, string helpers, quotes, conditions, and the null coalesce."""

from __future__ import annotations

import re

from backports._values import (
    NA,
    BackportError,
    as_character,
    is_na,
    is_null,
    is_true,
    length_of,
    recycle,
    trimws,
)

__all__ = [
    "anyNA",
    "dQuote",
    "endsWith",
    "errorCondition",
    "hasName",
    "isFALSE",
    "isTRUE",
    "is_namespace_loaded",
    "lengths",
    "null_coalesce",
    "sQuote",
    "startsWith",
    "strrep",
    "trimws",
    "valid_factor",
    "warningCondition",
]


def isTRUE(x) -> bool:
    return isinstance(x, bool) and x is True


def isFALSE(x) -> bool:
    return isinstance(x, bool) and x is False


def hasName(x, name):
    names = _names_of(x)
    wanted = list(name) if isinstance(name, (list, tuple)) else [name]
    found = [item in names for item in wanted]
    if isinstance(name, (list, tuple)):
        return found
    return found[0]


def _names_of(x):
    if isinstance(x, dict):
        return list(x.keys())
    named = getattr(x, "names", None)
    if named is None:
        return []
    return list(named)


def anyNA(x, recursive=False) -> bool:
    if is_true(recursive) and isinstance(x, (list, tuple)):
        return any(anyNA(item, recursive=False) or _list_has_na(item) for item in x)
    if isinstance(x, (list, tuple)):
        return any(_element_is_na(item) for item in x)
    if isinstance(x, dict):
        return anyNA(list(x.values()), recursive=recursive)
    return is_na(x)


def _list_has_na(value) -> bool:
    if isinstance(value, (list, tuple)):
        return anyNA(value, recursive=True)
    return False


def _element_is_na(value) -> bool:
    if isinstance(value, (list, tuple, dict)):
        return False
    return is_na(value)


def lengths(x, use_names=True):
    if isinstance(x, dict):
        values = [length_of(item) for item in x.values()]
        if is_true(use_names):
            return dict(zip(x.keys(), values))
        return values
    if isinstance(x, (list, tuple)):
        return [length_of(item) for item in x]
    if isinstance(x, str) or is_na(x) or isinstance(x, (bool, int, float)) or x is None:
        return [1] if x is not None else []
    return [1 for _ in x]


def startsWith(x, prefix):
    return _edge(x, prefix, from_start=True)


def endsWith(x, suffix):
    return _edge(x, suffix, from_start=False)


def _edge(x, other, from_start):
    xs = x if isinstance(x, (list, tuple)) else [x]
    ys = other if isinstance(other, (list, tuple)) else [other]
    if any(not isinstance(item, str) and not is_na(item) for item in xs + ys):
        raise BackportError("non-character object(s)")
    left, right = recycle(xs, ys)
    out = [_edge_one(item, piece, from_start) for item, piece in zip(left, right)]
    if isinstance(x, (list, tuple)) or isinstance(other, (list, tuple)):
        return out
    return out[0] if out else []


def _edge_one(text, piece, from_start):
    if is_na(text) or is_na(piece):
        return NA
    if from_start:
        return text[: len(piece)] == piece
    if len(piece) > len(text):
        return False
    return text[len(text) - len(piece) :] == piece


def strrep(x, times):
    texts = as_character(x)
    if len(texts) == 0:
        return texts
    counts = times if isinstance(times, (list, tuple)) else [times]
    if len(counts) == 0:
        return []
    scalar = not isinstance(x, (list, tuple)) and not isinstance(times, (list, tuple))
    texts, counts = recycle(texts, counts)
    repeated = [_repeat_one(text, count) for text, count in zip(texts, counts)]
    if scalar:
        return repeated[0]
    return repeated


def _repeat_one(text, times):
    if is_na(text) or is_na(times):
        return NA
    count = int(times)
    if count <= 0:
        return ""
    return text * count


def null_coalesce(x, y):
    if is_null(x):
        return y
    return x


def URLencode(URL, reserved=False, repeated=False):
    if isinstance(URL, (list, tuple)):
        if len(URL) == 0:
            return []
        URL = URL[0]
    if not isinstance(URL, str):
        raise BackportError("URL must be a character string")
    if not repeated and re.search(r"%[0-9A-Fa-f]{2}", URL):
        return URL
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~-")
    if not reserved:
        allowed.update("][!$&'()*+,;=:/?@#")
    pieces = []
    for char in URL:
        if char in allowed:
            pieces.append(char)
            continue
        pieces.append("".join(f"%{byte:02X}" for byte in char.encode("utf-8")))
    return "".join(pieces)


def dQuote(x, q=True):
    return _quote(x, q, straight='"', tex=("``", "''"), utf=(0x201C, 0x201D), index=(2, 3))


def sQuote(x, q=True):
    return _quote(x, q, straight="'", tex=("`", "'"), utf=(0x2018, 0x2019), index=(0, 1))


def _quote(x, q, straight, tex, utf, index):
    values = x if isinstance(x, (list, tuple)) else [x]
    if len(values) == 0:
        return []
    before = after = straight
    if q is not None:
        if q is True:
            q = "UTF-8"
        if q == "TeX":
            before, after = tex
        if q == "UTF-8":
            before, after = chr(utf[0]), chr(utf[1])
        if isinstance(q, (list, tuple)) and len(q) >= 4:
            before, after = q[index[0]], q[index[1]]
    quoted = [f"{before}{item}{after}" for item in values]
    if isinstance(x, (list, tuple)):
        return quoted
    return quoted[0]


class Condition:
    """A warning or error condition. Printing matches R's default condition print."""

    def __init__(self, message, call=None, classes=(), extra=None):
        self.message = message
        self.call = call
        self.classes = tuple(classes)
        self.extra = dict(extra or {})

    def inherits(self, classes) -> bool:
        wanted = (classes,) if isinstance(classes, str) else tuple(classes)
        return any(name in self.classes for name in wanted)

    def __repr__(self) -> str:
        kind = "warning" if "warning" in self.classes else "error"
        return f"<{kind}: {self.message}>"


def warningCondition(msg, *extra, class_=None, call=None, **fields):
    return _condition(msg, extra, fields, class_, call, "warning")


def errorCondition(msg, *extra, class_=None, call=None, **fields):
    return _condition(msg, extra, fields, class_, call, "error")


def _condition(msg, extra, fields, class_, call, kind):
    classes = []
    if class_:
        classes.extend([class_] if isinstance(class_, str) else list(class_))
    classes.extend([kind, "condition"])
    payload = {}
    if extra:
        payload["extra"] = extra
    payload.update(fields)
    return Condition(msg, call=call, classes=tuple(classes), extra=payload)


class Factor:
    def __init__(self, levels):
        self.levels = [str(item) for item in levels]


def valid_factor(object):
    levels = getattr(object, "levels", None)
    if not isinstance(levels, (list, tuple)) or any(not isinstance(item, str) for item in levels):
        return 'factor levels must be "character"'
    seen = set()
    for index, level in enumerate(levels, start=1):
        if level in seen:
            return f"duplicated level [{index}] in factor"
        seen.add(level)
    return True


_LOADED = {"backports"}


def mark_namespace_loaded(name: str) -> None:
    _LOADED.add(name)


def is_namespace_loaded(name) -> bool:
    names = name if isinstance(name, (list, tuple)) else [name]
    found = [item in _LOADED for item in names]
    if isinstance(name, (list, tuple)):
        return found
    return found[0]
