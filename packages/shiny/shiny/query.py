"""GET query strings, from shiny 1.14.0 `R/utils.R`."""

from __future__ import annotations

import re

from shiny.values import Missing, NamedList, ShinyError, Vector

_STR = str
_NESTED = re.compile(r"\[.+\]")
_BRACKETS = re.compile(r"[\[\]]")


def parseQueryString(str, nested=False):
    """Named list of pairs from a query string.

    A leading ``?`` is optional. ``+`` becomes a space before percent-decoding.
    With ``nested``, keys that contain ``[]`` become nested lists.
    """
    if str is None:
        return NamedList()
    text = _one_string(str)
    if text is None:
        return NamedList()
    if len(text) == 0:
        return NamedList()
    if text[0] == "?":
        text = text[1:]

    pairs = [item for item in text.split("&") if item != ""]
    keys = []
    values = []
    for pair in pairs:
        pieces = pair.split("=")
        keys.append(pieces[0])
        values.append(pieces[1] if len(pieces) > 1 else "")
    keys = [_url_decode(key.replace("+", " ")) for key in keys]
    values = [_url_decode(value.replace("+", " ")) for value in values]
    result = NamedList(list(zip(keys, values)))
    if not nested:
        return result

    for index, key in enumerate(keys):
        if _NESTED.search(key) is None:
            continue
        parts = [part for part in _BRACKETS.split(key) if part != ""]
        _assign_nested(result, parts, values[index])
        result.remove_first(key)
    return result


def format_query(value) -> str:
    """Hex form of a query list, so invalid UTF-8 still compares."""
    if isinstance(value, _STR):
        return "s:" + value.encode("utf-8", "surrogateescape").hex()
    if isinstance(value, NamedList):
        if not value.pairs:
            return "l:()"
        parts = []
        for name, item in value.pairs:
            name_hex = name.encode("utf-8", "surrogateescape").hex()
            parts.append(f"s:{name_hex}={format_query(item)}")
        return "l:(" + "|".join(parts) + ")"
    raise TypeError(type(value).__name__)


def _one_string(value):
    """The length-one character `str` argument, or an R error."""
    if isinstance(value, Vector):
        if value.mode != "character":
            raise ShinyError("non-character argument")
        if len(value.data) == 0:
            raise ShinyError("missing value where TRUE/FALSE needed")
        if len(value.data) != 1:
            raise ShinyError(
                f"'length = {len(value.data)}' in coercion to 'logical(1)'"
            )
        item = value.data[0]
        if isinstance(item, Missing):
            raise ShinyError("missing value where TRUE/FALSE needed")
        return item
    if isinstance(value, _STR):
        return value
    raise ShinyError("non-character argument")


def _hex_value(char: str):
    code = ord(char)
    if 48 <= code <= 57:
        return code - 48
    if 65 <= code <= 70:
        return code - 55
    if 97 <= code <= 102:
        return code - 87
    return None


def _url_decode(text: str) -> str:
    """httpuv `decodeURIComponent`.

    A valid `%HH` is one byte. Any other `%` plus the next two characters, when
    they exist, is copied unchanged, and a `%` sequence that starts inside that
    triplet is not decoded. The bytes are kept, including ones that are not
    UTF-8. A zero byte is R's embedded-nul error.
    """
    raw = bytearray()
    index = 0
    size = len(text)
    while index < size:
        char = text[index]
        if char == "%" and index + 2 < size:
            high = _hex_value(text[index + 1])
            low = _hex_value(text[index + 2])
            if high is not None and low is not None:
                raw.append((high << 4) | low)
            else:
                raw.extend(text[index : index + 3].encode("utf-8"))
            index += 3
            continue
        raw.extend(char.encode("utf-8"))
        index += 1
    if 0 in raw:
        shown = bytearray()
        for byte in raw:
            if byte == 0:
                shown.extend(b"\\0")
            else:
                shown.append(byte)
        body = shown.decode("utf-8", "surrogateescape")
        raise ShinyError(f"embedded nul in string: '{body}'")
    return raw.decode("utf-8", "surrogateescape")


def _get(obj: NamedList, path: list[str]):
    current = obj
    for key in path:
        if not isinstance(current, NamedList):
            raise ShinyError("subscript out of bounds")
        found = None
        for name, value in current.pairs:
            if name == key:
                found = value
                break
        if found is None:
            return None
        current = found
    return current


def _set(obj: NamedList, path: list[str], value) -> None:
    if len(path) == 1:
        obj.set_first(path[0], value)
        return
    head, *rest = path
    child = obj.first(head)
    if child is None:
        child = NamedList()
        obj.pairs.append((head, child))
    elif not isinstance(child, NamedList):
        raise ShinyError("subscript out of bounds")
    _set(child, rest, value)


def _assign_nested(obj: NamedList, path: list[str], value) -> None:
    for length in range(1, len(path) + 1):
        current = _get(obj, path[:length])
        if current is None:
            _set(obj, path[:length], NamedList())
    _set(obj, path, value)
