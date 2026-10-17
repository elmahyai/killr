"""Quote each element the way R's encodeString does."""

from __future__ import annotations

from typing import Any

from glue._text import NA, Glue, character_vector, encode_one


def _quote(x: Any, mark: str) -> Glue:
    if isinstance(x, (list, tuple, Glue)) and len(x) == 0:
        return Glue(())
    values = character_vector(x)
    if values is None:
        return Glue(())
    quoted = [NA if item is NA else encode_one(str(item), mark) for item in values]
    return Glue(tuple(quoted))


def single_quote(x: Any) -> Glue:
    """Wrap each element in single quotes, escaping with encodeString rules."""

    return _quote(x, "'")


def double_quote(x: Any) -> Glue:
    """Wrap each element in double quotes, escaping with encodeString rules."""

    return _quote(x, '"')


def backtick(x: Any) -> Glue:
    """Wrap each element in backticks, escaping with encodeString rules."""

    return _quote(x, "`")
