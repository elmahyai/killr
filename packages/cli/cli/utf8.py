"""Grapheme clusters and display width.

Grapheme boundaries come from the regex module, which matched cli's
graph breaker. Display width uses cli's charwidth table: an emoji
code point freezes the width of the rest of that cluster.
"""

from __future__ import annotations

import gzip
import math
from functools import lru_cache
from pathlib import Path

import regex

from glue._text import r_character

_DISPLAY = (0, 0, 0, 1, 1, 2, 2)
_EMOJI = 6
_TYPES = ("chars", "bytes", "width", "graphemes", "codepoints")


@lru_cache(maxsize=1)
def _charwidth_table() -> bytes:
    path = Path(__file__).resolve().parent / "data" / "charwidth.bin.gz"
    with gzip.open(path, "rb") as handle:
        table = handle.read()
    if len(table) != 0x110000:
        raise RuntimeError("cli charwidth table has the wrong length")
    return table


def charwidth(code: int) -> int:
    """cli's width class for one code point."""

    table = _charwidth_table()
    if code < 0 or code >= len(table):
        return 0
    return table[code]


def graphemes(text: str) -> list[str]:
    if text == "":
        return []
    return regex.findall(r"\X", text)


def grapheme_width(cluster: str) -> int:
    total = 0
    done = False
    for char in cluster:
        kind = charwidth(ord(char))
        if done:
            continue
        total += _DISPLAY[kind]
        if kind == _EMOJI:
            done = True
    return total


def display_width(text: str) -> int:
    return sum(grapheme_width(cluster) for cluster in graphemes(text))


def _as_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return r_character(value)


def _vector(x) -> list:
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _scalar(x, out):
    if not isinstance(x, (list, tuple)) and len(out) == 1:
        return out[0]
    return out


def _match_arg(value, choices: tuple[str, ...]) -> str:
    if value is None:
        return choices[0]
    if not isinstance(value, str):
        raise TypeError("type must be a string")
    hits = [choice for choice in choices if choice.startswith(value)]
    if len(hits) != 1:
        raise ValueError(f"type must match one of {choices}")
    return hits[0]


def _measure(text: str, kind: str) -> int:
    if kind == "graphemes":
        return len(graphemes(text))
    if kind == "bytes":
        return len(text.encode("utf-8"))
    if kind == "codepoints":
        return len(text)
    return display_width(text)


def utf8_nchar(x, type="chars"):
    """Count graphemes, bytes, code points, or display width."""

    kind = _match_arg(type, _TYPES)
    if kind == "chars":
        kind = "graphemes"
    out = []
    for value in _vector(x):
        text = _as_text(value)
        out.append(None if text is None else _measure(text, kind))
    return _scalar(x, out)


def _as_int(value) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError("start and stop must be numeric")
    if isinstance(value, float) and math.isnan(value):
        raise ValueError("start and stop must not be NA")
    return int(value)


def _substr_one(text: str, start: int, stop: int) -> str:
    pieces = graphemes(text)
    pos = 1
    index = 0
    while pos < start and index < len(pieces):
        index += 1
        pos += 1
    taken = []
    while pos <= stop and index < len(pieces):
        taken.append(pieces[index])
        index += 1
        pos += 1
    return "".join(taken)


def utf8_substr(x, start, stop):
    """Substring by grapheme cluster. Indexes are 1-based and inclusive."""

    starts = _vector(start)
    stops = _vector(stop)
    if not starts or not stops:
        raise ValueError("start and stop must have at least length 1")
    values = _vector(x)
    out = []
    for i, value in enumerate(values):
        text = _as_text(value)
        if text is None:
            out.append(None)
            continue
        out.append(
            _substr_one(
                text,
                _as_int(starts[i % len(starts)]),
                _as_int(stops[i % len(stops)]),
            )
        )
    return _scalar(x, out)


def utf8_graphemes(x):
    """Split each string into grapheme clusters."""

    out = []
    for value in _vector(x):
        text = _as_text(value)
        out.append(None if text is None else graphemes(text))
    return _scalar(x, out)
