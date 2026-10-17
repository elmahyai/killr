"""sanitize.final from xtable 1.8-8."""

from __future__ import annotations

from xtable.string_connection import StringConnection, is_string


def sanitize_final(str_conn: StringConnection, *, type: str = "latex") -> StringConnection:
    if type == "latex":
        return str_conn
    text = str_conn.text
    # R uses gsub(..., fixed = TRUE): "  *" is a literal pattern, not
    # a regular expression matching an arbitrary run of whitespace.
    text = text.replace("  *", " ")
    text = text.replace(' align="left"', "")
    str_conn.text = text
    return str_conn
