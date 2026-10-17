"""Validate, prettify, and minify JSON text."""

from __future__ import annotations

import json


def validate(txt: str | list[str]) -> bool:
    """Whether ``txt`` is one JSON value. A list of strings is joined with newlines."""

    try:
        json.loads(_join(txt))
    except json.JSONDecodeError:
        return False
    return True


def prettify(txt: str | list[str], indent: int = 4) -> str:
    """Insert indentation. A positive indent is spaces. A negative indent is tabs."""

    value = json.loads(_join(txt))
    if indent < 0:
        text = json.dumps(value, indent="\t" * abs(int(indent)), ensure_ascii=False)
    else:
        text = json.dumps(value, indent=int(indent) if indent else None, ensure_ascii=False)
        if indent == 0:
            text = json.dumps(value, separators=(",", ":"), ensure_ascii=False)
    if not text.endswith("\n"):
        text += "\n"
    return text


def minify(txt: str | list[str]) -> str:
    """Drop insignificant whitespace and keep number and string tokens as written."""

    return _strip_whitespace(_join(txt))


def _join(txt: str | list[str]) -> str:
    if isinstance(txt, list):
        return "\n".join(txt)
    return txt


def _strip_whitespace(text: str) -> str:
    out: list[str] = []
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            out.append(char)
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
            out.append(char)
        elif char in " \t\r\n":
            continue
        else:
            out.append(char)
    return "".join(out)
