"""``str_interp``, the superseded ``${}`` and ``$[format]{}`` interpolator."""

from __future__ import annotations

import re
from typing import Any

from stringi._na import NA, is_na


_START = re.compile(r"\$(\[.*?\])?\{")
_COMPLETE = re.compile(r"\$(\[.*?\])?\{.+\}")
_FORMAT = re.compile(r"\$(\[(.+?)\])?")


def _collapse(string: Any) -> Any:
    """Join a character vector with an empty separator, the way ``str_c`` does.

    A missing element makes the whole string missing. An empty vector
    collapses to an empty string.
    """

    if isinstance(string, str) or is_na(string):
        parts = [string]
    elif isinstance(string, (list, tuple)):
        parts = list(string)
    else:
        raise TypeError("string must be a character vector.")
    if any(not isinstance(part, str) and not is_na(part) for part in parts):
        raise TypeError("string must be a character vector.")
    if any(is_na(part) for part in parts):
        return NA
    return "".join(parts)


def _match_brace(opening: list[int], closing: list[int]) -> int:
    """Position of the brace that closes the first opening brace.

    Positions are 1-based indexes into one placeholder part. This is the
    path used by the R helper: openings before the last close are +1,
    closes are -1, and the first return to zero after the first +1 wins.
    """

    if not closing:
        raise ValueError("Invalid template string for interpolation.")
    max_close = max(closing)
    path = [0] * (max_close + 1)
    for pos in opening:
        if pos < max_close:
            path[pos] = 1
    for pos in closing:
        if 1 <= pos <= max_close:
            path[pos] = -1
    cumpath = []
    total = 0
    for value in path[1:]:
        total += value
        cumpath.append(total)
    first_open = None
    for index, value in enumerate(cumpath, start=1):
        if value == 1:
            first_open = index
            break
    if first_open is None:
        raise ValueError("Invalid template string for interpolation.")
    matches = [index for index, value in enumerate(cumpath, start=1) if index > first_open and value == 0]
    if not matches:
        raise ValueError("Invalid template string for interpolation.")
    return min(matches)


def _placeholders(string: str) -> tuple[list[int], list[str]] | None:
    starts = [match.start() + 1 for match in _START.finditer(string)]
    if not starts:
        return None
    parts = []
    for index, start in enumerate(starts):
        stop = starts[index + 1] - 1 if index + 1 < len(starts) else len(string)
        parts.append(string[start - 1 : stop])
    if any(_COMPLETE.search(part) is None for part in parts):
        raise ValueError("Invalid template string for interpolation.")
    lengths = []
    for part in parts:
        chars = list(part)
        opens = [i + 1 for i, char in enumerate(chars) if char == "{"]
        closes = [i + 1 for i, char in enumerate(chars) if char == "}"]
        lengths.append(_match_brace(opens, closes))
    matches = []
    for start, length in zip(starts, lengths):
        matches.append(string[start - 1 : start - 1 + length])
    return starts, matches


def _expression(match: str) -> str:
    stripped = re.sub(r"\$(\[.+?\])?\{", "", match, count=1)
    return stripped[:-1]


def _format(match: str) -> str:
    found = _FORMAT.match(match)
    if found is None or not found.group(2):
        return "%s"
    return "%" + found.group(2)


def _sprintf(fmt: str, value: Any) -> str:
    spec = fmt[-1] if fmt else "s"
    if spec in "diouxX":
        value = int(value)
    elif spec in "fFeEgG":
        value = float(value)
    return fmt % value


def _eval_one(expression: str, env: dict[str, Any]) -> Any:
    try:
        return eval(expression, {"__builtins__": __builtins__}, dict(env))  # noqa: S307
    except SyntaxError as exc:
        raise ValueError(f"Failed to parse input {expression!r}") from exc


def str_interp(string: Any, env: dict[str, Any] | None = None) -> list:
    """Interpolate ``${expression}`` and ``$[format]{expression}`` placeholders.

    ``string`` is collapsed with an empty separator before scanning, so a
    character vector becomes one template. ``env`` is a dict of names. The
    result is a length-1 character vector.
    """

    if env is None:
        env = {}
    collapsed = _collapse(string)
    if is_na(collapsed):
        raise ValueError("missing value where TRUE/FALSE needed")
    found = _placeholders(collapsed)
    if found is None:
        return [collapsed]
    starts, matches = found
    replacements = []
    for match in matches:
        value = _eval_one(_expression(match), env)
        replacements.append(_sprintf(_format(match), value))
    out = []
    previous = 0
    for start, match, replacement in zip(starts, matches, replacements):
        begin = start - 1
        out.append(collapsed[previous:begin])
        out.append(replacement)
        previous = begin + len(match)
    out.append(collapsed[previous:])
    return ["".join(out)]
