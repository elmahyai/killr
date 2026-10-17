"""Widths, padding, and the gutter/column assembly of a formatted diff."""

from __future__ import annotations

import re

from crayon import col_nchar, has_style, strip_style

_PUNCT = re.compile(r" ([!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~])")
_WS = re.compile(r"[ \t]+")


def nchar2(text: str, sgr_supported: bool = False) -> int:
    if text is None:
        return 0
    if sgr_supported:
        counted = col_nchar(text)
        if isinstance(counted, list):
            return int(counted[0] or 0)
        return int(counted or 0)
    return len(text)


def chr_trim(text: str, width: int, sgr_supported: bool = False) -> str:
    if nchar2(text, sgr_supported) > width:
        return text[: width - 2] + ".."
    return text


def rpad(text: str, width: int, sgr_supported: bool = False) -> str:
    if text is None:
        text = ""
    extra = width - nchar2(text, sgr_supported)
    if extra <= 0:
        return text
    return text + (" " * extra)


def wrap_pieces(text: str, width: int, sgr_supported: bool = False) -> list[str]:
    if text is None:
        return [None]
    if text == "":
        return [""]
    size = nchar2(text, sgr_supported)
    if size <= width or width <= 0:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        pieces.append(text[start : start + width])
        start += width
    return pieces


def normalize_whitespace(text: str) -> str:
    trimmed = text.strip(" \t\r\n")
    collapsed = _WS.sub(" ", trimmed)
    return _PUNCT.sub(r"\1", collapsed)


def strip_hz_control(text: str, stops: list[int]) -> str:
    """Expand tabs and drop carriage returns. Plain lines are unchanged."""

    if "\t" not in text and "\r" not in text:
        return text
    text = text.strip("\r")
    if "\r" in text:
        text = text.split("\r")[-1]
    if "\t" not in text:
        return text
    stop = stops[-1] if stops else 8
    out = []
    column = 0
    for char in text:
        if char == "\t":
            advance = stop - (column % stop)
            if advance == 0:
                advance = stop
            out.append(" " * advance)
            column += advance
        else:
            out.append(char)
            column += 1
    return "".join(out)


def split_new_line(lines: list[str]) -> list[str]:
    if not any(line != "" for line in lines):
        return list(lines)
    out = []
    for line in lines:
        if line == "":
            out.append("")
            continue
        parts = line.split("\n")
        out.extend(parts)
    return out


def maybe_strip_sgr(lines: list[str], enabled: bool) -> list[str]:
    if not enabled:
        return lines
    if not any(_has(line) for line in lines):
        return lines
    return [strip_style(line) if isinstance(strip_style(line), str) else line for line in lines]


def _has(line: str) -> bool:
    flag = has_style(line)
    if isinstance(flag, list):
        return bool(flag[0])
    return bool(flag)


def render_gutters(types: list[str], lengths: list[int], lengths_max: list[int], gutter: dict) -> list[list[str]]:
    rows = []
    for kind, length, length_max in zip(types, lengths, lengths_max):
        if kind in ("insert", "delete", "match", "guide", "fill", "context.sep"):
            pieces = []
            if length:
                pieces.append(gutter[kind])
            continued = gutter[f"{kind}.ctd"]
            pieces.extend([continued] * max(length - 1, 0))
            pieces.extend([gutter["fill"]] * max(length_max - length, 0))
            rows.append(pieces)
        else:
            rows.append([""] * length)
    return rows


def render_column(gutters: list[list[str]], texts: list[list[str]]) -> list[str]:
    out = []
    for gutter_pieces, text_pieces in zip(gutters, texts):
        for gutter, text in zip(gutter_pieces, text_pieces):
            out.append(f"{gutter}{'' if text is None else text}")
    return out
