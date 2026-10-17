"""Concordance maps from tools 4.5.0."""

from __future__ import annotations

import re
from typing import Any


def _repeat(values: list[Any], size: int) -> list[Any]:
    if not values:
        return []
    return [values[index % len(values)] for index in range(size)]


def match_concordance(linenum: Any, concordance: dict[str, Any]) -> list[tuple[str, str]]:
    """Map output lines back to source file and source line."""
    needed = {"offset", "srcLine", "srcFile"}
    if not needed <= set(concordance):
        raise ValueError("concordance is not valid")
    if isinstance(linenum, (int, float)):
        numbers = [int(linenum)]
    else:
        numbers = [int(item) for item in linenum]
    src_lines = list(concordance["srcLine"])
    src_file = _repeat(list(concordance["srcFile"]) if isinstance(concordance["srcFile"], list) else [concordance["srcFile"]], len(src_lines))
    offset = int(concordance["offset"])
    rows = []
    for number in numbers:
        if number <= offset:
            rows.append(("", ""))
        else:
            slot = number - offset - 1
            rows.append((str(src_file[slot]), str(src_lines[slot])))
    return rows


def follow_concordance(concordance: dict[str, Any], prev: dict[str, Any] | None = None) -> dict[str, Any]:
    """Compose two concordance maps. A missing previous line keeps the current one."""
    if prev is None:
        return concordance
    cur_lines = list(concordance["srcLine"])
    cur_file = _repeat(
        list(concordance["srcFile"]) if isinstance(concordance["srcFile"], list) else [concordance["srcFile"]],
        len(cur_lines),
    )
    prev_lines = list(prev["srcLine"])
    prev_file = _repeat(
        list(prev["srcFile"]) if isinstance(prev["srcFile"], list) else [prev["srcFile"]],
        len(prev_lines),
    )
    prev_offset = int(prev["offset"])
    if prev_offset:
        prev_lines = [None] * prev_offset + prev_lines
        prev_file = [None] * prev_offset + prev_file
    span = max(cur_lines) if cur_lines else 0
    if len(prev_lines) < span:
        prev_lines = prev_lines + [None] * (span - len(prev_lines))
        prev_file = prev_file + [None] * (span - len(prev_file))
    new_file = []
    new_line = []
    for line, file_name in zip(cur_lines, cur_file):
        earlier = prev_lines[line - 1]
        if earlier is None:
            new_file.append(file_name)
            new_line.append(line)
        else:
            new_file.append(prev_file[line - 1])
            new_line.append(earlier)
    return {"offset": concordance["offset"], "srcFile": new_file, "srcLine": new_line}


def _inverse_rle(lengths, values):
    expanded = []
    for length, value in zip(lengths, values):
        expanded.extend([value] * length)
    return expanded


def _string_to_concordance(text):
    parts = text.split(":")
    if len(parts) == 4:
        offset = 0
        values = [int(item) for item in parts[3].split()]
    else:
        offset = int(re.sub(r"^ofs ([0-9]+)", r"\1", parts[3]))
        values = [int(item) for item in parts[4].split()]
    first = values[0]
    rest = values[1:]
    lengths = rest[0::2]
    steps = rest[1::2]
    diffs = _inverse_rle(lengths, steps)
    lines = [first]
    total = first
    for diff in diffs:
        total += diff
        lines.append(total)
    return {"offset": offset, "srcFile": parts[2], "srcLine": lines}


def as_rconcordance(x):
    """Parse concordance strings. A string without one is None."""
    if x is None:
        return None
    items = list(x) if isinstance(x, (list, tuple)) else [x]
    texts = []
    for item in items:
        text = item if isinstance(item, str) else str(item)
        text = re.sub(r"[^0-9]*$", "", text)
        text = re.sub(r"^.*(concordance)", "concordance", text, count=1)
        if text.startswith("concordance:"):
            texts.append(text)
    if not texts:
        return None
    result = _string_to_concordance(texts[0])
    for line in texts[1:]:
        prev = _string_to_concordance(line)
        src = result["srcFile"]
        src = _repeat(src if isinstance(src, list) else [src], len(result["srcLine"]))
        slots = range(len(prev["srcLine"]))
        width = prev["offset"] + len(prev["srcLine"])
        if len(src) < width:
            src = src + [None] * (width - len(src))
            result["srcLine"] = result["srcLine"] + [None] * (width - len(result["srcLine"]))
        files = prev["srcFile"]
        files = files if isinstance(files, list) else [files]
        for index in slots:
            src[prev["offset"] + index] = files[index % len(files)]
            result["srcLine"][prev["offset"] + index] = prev["srcLine"][index]
        result["srcFile"] = src
    return result


def _inverse_rle(lengths, values):
    expanded = []
    for length, value in zip(lengths, values):
        expanded.extend([value] * length)
    return expanded


def _string_to_concordance(text):
    parts = text.split(":")
    if len(parts) == 4:
        offset = 0
        values_index = 3
    else:
        offset = int(re.sub(r"^ofs ([0-9]+)", r"\1", parts[3]))
        values_index = 4
    values = [int(item) for item in parts[values_index].split()]
    first = values[0]
    rest = values[1:]
    lengths = rest[0::2]
    steps = rest[1::2]
    diffs = _inverse_rle(lengths, steps)
    lines = [first]
    total = first
    for diff in diffs:
        total += diff
        lines.append(total)
    return {"offset": offset, "srcFile": parts[2], "srcLine": lines}


def _add_concordance(current, text):
    prev = _string_to_concordance(text)
    if prev is None:
        return current
    files = current["srcFile"]
    if isinstance(files, str):
        files = [files] * len(current["srcLine"])
    else:
        files = _repeat(list(files), len(current["srcLine"]))
    lines = list(current["srcLine"])
    prev_files = prev["srcFile"]
    if isinstance(prev_files, str):
        prev_files = [prev_files] * len(prev["srcLine"])
    for index, line in enumerate(prev["srcLine"]):
        slot = prev["offset"] + index
        while len(lines) <= slot:
            lines.append(None)
            files.append(None)
        files[slot] = prev_files[index]
        lines[slot] = line
    current = dict(current)
    current["srcFile"] = files
    current["srcLine"] = lines
    return current


def as_rconcordance(x):
    """Parse a concordance string. A string that does not match is None."""
    if isinstance(x, (list, tuple)):
        items = ["" if item is None else str(item) for item in x]
    else:
        items = ["" if x is None else str(x)]
    kept = []
    for item in items:
        text = re.sub(r"[^0-9]*$", "", item)
        text = re.sub(r"^.*(concordance)", "concordance", text, count=1)
        if text.startswith("concordance:"):
            kept.append(text)
    if not kept:
        return None
    result = _string_to_concordance(kept[0])
    for line in kept[1:]:
        result = _add_concordance(result, line)
    return result
