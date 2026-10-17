"""Rd delimiter matching. A backslash escapes the next character, and % comments to the newline."""

from __future__ import annotations

from typing import Any

from tools.file_ext import NA


def _one(text: str, opener: str, closer: str) -> int:
    size = len(text)
    index = 0
    while index < size:
        char = text[index]
        if char == "\\":
            index += 2
            continue
        if char == "%":
            while index < size and text[index] != "\n":
                index += 1
            continue
        if char == opener:
            start = index
            depth = 1
            index += 1
            while index < size and depth:
                char = text[index]
                if char == "\\":
                    index += 2
                    continue
                if char == "%":
                    while index < size and text[index] != "\n":
                        index += 1
                    continue
                if char == opener:
                    depth += 1
                elif char == closer:
                    depth -= 1
                index += 1
            return start + 1 if depth == 0 else -1
        index += 1
    return -1


def delim_match(x: Any, delim: tuple[str, str] | list[str] = ("{", "}"), syntax: str = "Rd") -> Any:
    """1-based position of the first balanced opening delimiter, or -1."""
    if isinstance(x, (list, tuple)) and any(not isinstance(item, (str, NA)) for item in x):
        raise ValueError("argument 'x' must be a character vector")
    if not isinstance(x, (str, NA, list, tuple)):
        raise ValueError("argument 'x' must be a character vector")
    if len(delim) != 2 or any(len(item) != 1 for item in delim):
        raise ValueError("argument 'delim' must specify two characters")
    if syntax != "Rd":
        raise ValueError("only Rd syntax is currently supported")
    opener, closer = delim
    if isinstance(x, (str, NA)):
        if isinstance(x, NA):
            return -1
        return _one(x, opener, closer)
    return [-1 if isinstance(item, NA) else _one(item, opener, closer) for item in x]
