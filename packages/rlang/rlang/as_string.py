"""Cast symbols to strings."""

from __future__ import annotations

from rlang import RLangError, abort, is_string


class Symbol:
    """R symbol (SYMSXP) as stored in native encoding."""

    __slots__ = ("_name",)

    def __init__(self, name: str):
        self._name = name

    def __repr__(self) -> str:
        return self._name


def _is_symbol(x: object) -> bool:
    return isinstance(x, Symbol)


def _is_hex(ch: str) -> bool:
    return ("0" <= ch <= "9") or ("A" <= ch <= "F")


def _has_codepoint(text: str, start: int) -> bool:
    if start + 8 > len(text):
        return False
    if text[start : start + 3] != "<U+":
        return False
    for offset in range(3, 7):
        if not _is_hex(text[start + offset]):
            return False
    return text[start + 7] == ">"


def _has_unicode_escape(text: str) -> bool:
    index = 0
    while index < len(text):
        if _has_codepoint(text, index):
            return True
        index += 1
    return False


def _unserialise_unicode(text: str) -> str:
    if not _has_unicode_escape(text):
        return text
    out: list[str] = []
    index = 0
    while index < len(text):
        if _has_codepoint(text, index):
            codepoint = int(text[index + 3 : index + 7], 16)
            out.append(chr(codepoint))
            index += 8
        else:
            out.append(text[index])
            index += 1
    return "".join(out)


def _obj_type_friendly(x: object) -> str:
    if isinstance(x, list):
        return "a list"
    if isinstance(x, dict):
        return "an environment"
    if isinstance(x, bool):
        return "a logical vector"
    if isinstance(x, int):
        return "an integer vector"
    if isinstance(x, float):
        return "a double vector"
    if isinstance(x, str):
        return "a character vector"
    if isinstance(x, Symbol):
        return "a symbol"
    return f"a {type(x).__name__}"


def _abort_coercion(x: object, to_type: str) -> None:
    abort(f"Can't convert {_obj_type_friendly(x)} to {to_type}.")


def as_string(x: object) -> str:
    if is_string(x):
        return str(x)
    if _is_symbol(x):
        return _unserialise_unicode(x._name)
    _abort_coercion(x, "a string")
    raise RLangError("unreachable")
