"""Split delimited text the way readr's second edition does."""

from __future__ import annotations

import re
from collections import Counter


def guess_delim(lines, delims=(",", "\t", " ", "|", ":", ";")) -> str:
    """Pick the delimiter that most consistently splits the sample lines."""
    if not lines:
        return ""
    cleaned = [re.sub(r'"[^"]*"', "", line) for line in lines]
    stats = []
    for delim in delims:
        lengths = []
        for line in cleaned:
            if delim == "":
                lengths.append(len(line))
            else:
                lengths.append(line.count(delim) + 1 if line != "" or True else 1)
        counts = Counter(lengths)
        smallest = min(counts)
        stats.append((smallest, counts[smallest]))
    top_lines = 0
    top_index = -1
    for index, (fields, lines_with) in enumerate(stats):
        if (fields >= 2 and lines_with > top_lines) or (
            top_lines == lines_with and (top_index < 0 or stats[top_index][0] < fields)
        ):
            top_lines = lines_with
            top_index = index
    if top_index < 0:
        raise ValueError(
            "Could not guess the delimiter. Pass delim= to specify it."
        )
    return delims[top_index]


def _unescape(character: str) -> str:
    return {"n": "\n", "r": "\r", "t": "\t"}.get(character, character)


def parse_records(
    text: str,
    delim: str,
    quote: str = '"',
    escape_backslash: bool = False,
    escape_double: bool = True,
    comment: str = "",
    skip_empty_rows: bool = True,
) -> list[list[tuple[str, bool]]]:
    """Return rows of (field, was_quoted) pairs. A blank line is one empty field."""
    records: list[tuple[int, list[tuple[str, bool]]]] = []
    row: list[tuple[str, bool]] = []
    field: list[str] = []
    quoted = False
    in_quote = False
    at_start = True
    index = 0
    length = len(text)
    quote_char = quote[:1] if quote else ""
    line_no = 1
    row_line = 1

    def finish_field() -> None:
        nonlocal field, quoted
        row.append(("".join(field), quoted))
        field = []
        quoted = False

    def finish_row() -> None:
        nonlocal row, at_start
        finish_field()
        empty = skip_empty_rows and len(row) == 1 and row[0][0] == "" and not row[0][1]
        if not empty:
            records.append((row_line, row))
        row = []
        at_start = True

    while index < length:
        character = text[index]
        if in_quote:
            if escape_backslash and character == "\\" and index + 1 < length:
                field.append(_unescape(text[index + 1]))
                index += 2
                continue
            if quote_char and character == quote_char:
                if escape_double and index + 1 < length and text[index + 1] == quote_char:
                    field.append(quote_char)
                    index += 2
                    continue
                in_quote = False
                index += 1
                continue
            if character in "\r\n":
                if character == "\r" and index + 1 < length and text[index + 1] == "\n":
                    field.append("\r\n")
                    index += 2
                else:
                    field.append(character)
                    index += 1
                line_no += 1
                continue
            field.append(character)
            index += 1
            at_start = False
            continue
        if at_start and comment and text.startswith(comment, index):
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            line_no = text.count("\n", 0, index) + 1
            row_line = line_no
            at_start = True
            continue
        if escape_backslash and character == "\\" and index + 1 < length:
            field.append(_unescape(text[index + 1]))
            index += 2
            at_start = False
            continue
        if quote_char and character == quote_char and not field:
            in_quote = True
            quoted = True
            index += 1
            at_start = False
            continue
        if delim and text.startswith(delim, index):
            finish_field()
            index += len(delim)
            at_start = False
            continue
        if character in "\n\r":
            if character == "\r" and index + 1 < length and text[index + 1] == "\n":
                index += 1
            finish_row()
            line_no += 1
            row_line = line_no
            index += 1
            continue
        field.append(character)
        index += 1
        at_start = False
    if field or row or (text and not text.endswith(("\n", "\r"))):
        if field or row:
            finish_row()
    return records


def whitespace_records(text: str, quote: str = '"', comment: str = "", skip_empty_rows: bool = True):
    """Split on runs of whitespace, outside quotes."""
    records = []
    row: list[tuple[str, bool]] = []
    field: list[str] = []
    in_quote = False
    quoted = False
    index = 0
    length = len(text)
    quote_char = quote[:1] if quote else ""
    at_start = True
    pending_break = False
    line_no = 1
    row_line = 1

    def finish_field():
        nonlocal field, quoted, pending_break
        if field or quoted:
            row.append(("".join(field), quoted))
        field = []
        quoted = False
        pending_break = False

    def finish_row():
        nonlocal row, at_start
        finish_field()
        if row or not skip_empty_rows:
            if row:
                records.append((row_line, row))
        row = []
        at_start = True

    while index < length:
        character = text[index]
        if in_quote:
            if quote_char and character == quote_char:
                if index + 1 < length and text[index + 1] == quote_char:
                    field.append(quote_char)
                    index += 2
                    continue
                in_quote = False
                index += 1
                continue
            field.append(character)
            index += 1
            continue
        if at_start and comment and text.startswith(comment, index):
            newline = text.find("\n", index)
            index = length if newline < 0 else newline + 1
            continue
        if character in "\n\r":
            if character == "\r" and index + 1 < length and text[index + 1] == "\n":
                index += 1
            finish_row()
            line_no += 1
            row_line = line_no
            index += 1
            continue
        if character in " \t":
            if field or quoted:
                finish_field()
            pending_break = True
            index += 1
            at_start = False
            continue
        if quote_char and character == quote_char and not field:
            in_quote = True
            quoted = True
            index += 1
            at_start = False
            continue
        field.append(character)
        index += 1
        at_start = False
    if field or row:
        finish_row()
    return records


def log_records(text: str) -> list[list[tuple[str, bool]]]:
    """Apache common/combined log lines. A dash is a missing field."""
    pattern = re.compile(
        r'^(\S+) (\S+) (\S+) \[([^\]]*)\] "(.*)" (\S+) (\S+)\s*$'
    )
    records = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line:
            continue
        matched = pattern.match(line)
        if not matched:
            records.append((line_no, [(line, False)]))
            continue
        fields = []
        for value in matched.groups():
            if value == "-":
                fields.append(("", False))
            else:
                fields.append((value, False))
        records.append((line_no, fields))
    return records
