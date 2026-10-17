"""Template scan from glue's C scanner.

The scanner walks the template once. A doubled delimiter is emitted as one
delimiter. Quotes, backticks, and comments hide a closing delimiter unless
``literal`` is true.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class GlueError(ValueError):
    """A glue template or expression failed."""


def scan(
    text: str,
    transformer: Callable[[str], Any],
    open: str,
    close: str,
    comment: str,
    literal: bool,
) -> list[Any]:
    if open == "":
        raise GlueError("The opening delimiter must not be empty.")
    if close == "":
        raise GlueError("The closing delimiter must not be empty.")

    comment_char = comment[0] if comment else "\0"
    open_len = len(open)
    close_len = len(close)
    delim_equal = close[:open_len] == open
    out: list[Any] = []
    buf: list[str] = []
    delim_level = 0
    start = 0
    state = "text"
    prev = "text"
    i = 0
    limit = len(text)

    while i < limit:
        if state == "text":
            if text.startswith(open, i):
                if text.startswith(open, i + open_len):
                    i += open_len
                else:
                    state = "delim"
                    delim_level = 1
                    start = i + open_len
                    i += 1
                    continue
            if text.startswith(close, i) and text.startswith(close, i + close_len):
                i += close_len
            buf.append(text[i])
        elif state == "escape":
            state = prev
        elif state == "single":
            if text[i] == "\\":
                prev = "single"
                state = "escape"
            elif text[i] == "'":
                state = "delim"
        elif state == "double":
            if text[i] == "\\":
                prev = "double"
                state = "escape"
            elif text[i] == '"':
                state = "delim"
        elif state == "backtick":
            if text[i] == "\\":
                prev = "backtick"
                state = "escape"
            elif text[i] == "`":
                state = "delim"
        elif state == "comment":
            if text[i] == "\n":
                state = "delim"
        else:
            if not delim_equal and text.startswith(open, i):
                delim_level += 1
                i += open_len - 1
            elif text.startswith(close, i):
                delim_level -= 1
                i += close_len - 1
            elif not literal and text[i] == comment_char:
                state = "comment"
            elif not literal and text[i] == "'":
                state = "single"
            elif not literal and text[i] == '"':
                state = "double"
            elif not literal and text[i] == "`":
                state = "backtick"
            if delim_level == 0:
                expr = text[start : i - close_len + 1]
                result = transformer(expr)
                if buf:
                    out.append("".join(buf))
                    buf = []
                out.append(result)
                state = "text"
        i += 1

    if not out or buf:
        out.append("".join(buf))

    if state == "delim":
        raise GlueError(f"Expecting '{close}'")
    if state == "single":
        raise GlueError("Unterminated quote (')")
    if state == "double":
        raise GlueError('Unterminated quote (")')
    if state == "backtick":
        raise GlueError("Unterminated quote (`)")
    if state == "comment":
        raise GlueError(
            "A '#' comment in a glue expression must terminate with a newline."
        )
    return out
