"""Paragraph wrapping for stringr 1.6.0.

``str_wrap`` calls the finished ``stri_wrap`` and joins each paragraph's
lines with a newline, which is what ``str_c(collapse = "\\n")`` does.
A width of 0 or less becomes 1, so each word lands on its own line.
"""

from __future__ import annotations

from stringi import stri_c, stri_wrap
from stringi._na import is_na

from stringr.case import (
    check_bool,
    check_number_decimal,
    check_number_whole,
    copy_names,
)


def _join_lines(lines) -> object:
    if is_na(lines):
        return lines
    if isinstance(lines, str):
        return lines
    joined = stri_c(list(lines), collapse="\n")
    if isinstance(joined, list):
        return joined[0] if joined else ""
    return joined


def str_wrap(string, width=80, indent=0, exdent=0, whitespace_only=True):
    """Wrap each string into a paragraph. Lines are separated by newlines."""

    check_number_decimal(width, "width")
    if width <= 0:
        width = 1
    check_number_whole(indent, "indent")
    check_number_whole(exdent, "exdent")
    check_bool(whitespace_only, "whitespace_only")
    pieces = stri_wrap(
        string,
        width=width,
        indent=indent,
        exdent=exdent,
        whitespace_only=whitespace_only,
        simplify=False,
    )
    return copy_names(string, [_join_lines(lines) for lines in pieces])
