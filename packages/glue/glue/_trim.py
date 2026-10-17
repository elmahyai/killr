"""Trim a template the way glue's C trim does.

Leading whitespace on the first line is removed, and a first-line newline
is removed with it. Later lines lose the shortest indentation of the
non-blank lines. A backslash at the end of a line continues that line.
Trailing whitespace is removed through the last newline.
"""

from __future__ import annotations


def trim_text(text: str) -> str:
    if "\n" not in text:
        return text

    limit = len(text)
    start = 0
    while start < limit and text[start] in " \t":
        start += 1

    new_line = False
    if start < limit and text[start] == "\n":
        new_line = True
        start += 1

    index = start
    if not new_line:
        while index < limit and text[index] != "\n":
            index += 1
        new_line = True

    indent = 0
    min_indent = 2**63
    while index < limit:
        if text[index] == "\n":
            new_line = True
            indent = 0
        elif new_line:
            if text[index] in " \t":
                indent += 1
            else:
                if indent < min_indent:
                    min_indent = indent
                indent = 0
                new_line = False
        index += 1

    if limit > 0 and text[limit - 1] != "\n" and new_line and indent < min_indent:
        min_indent = indent

    new_line = True
    index = start
    out: list[str] = []
    while index < limit:
        if text[index] == "\n":
            new_line = True
        elif text[index] == "\\" and index + 1 < limit and text[index + 1] == "\n":
            new_line = True
            index += 2
            continue
        elif new_line:
            skipped = 0
            while index + skipped < limit and text[index + skipped] in " \t":
                skipped += 1
            at_break = index + skipped < limit and text[index + skipped] == "\n"
            if at_break and skipped < min_indent:
                out.extend(text[index : index + skipped])
                index += skipped
            elif index + min_indent < limit and text[index] in " \t":
                index += min_indent
            new_line = False
            continue
        out.append(text[index])
        index += 1

    chars = out + ["\0"]
    end = len(out)
    cursor = len(out)
    while cursor > 0:
        if chars[cursor] == "\n":
            end = cursor
            break
        if chars[cursor] in "\0 \t":
            cursor -= 1
        else:
            break
    return "".join(out[:end])
