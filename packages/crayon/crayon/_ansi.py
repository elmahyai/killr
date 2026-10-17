"""Color-aware nchar, substr, substring, strsplit, and align."""

from __future__ import annotations

import math
import re
from typing import Any

from crayon._options import get_option
from crayon._text import character_vector, one_or_many

# perl=TRUE and the default TRE engine both match this on crayon's own tags.
ANSI_REGEX = re.compile(
    r"(?:(?:\x1b\[)|\x9b)"
    r"(?:(?:[0-9]{1,3})?(?:(?:;[0-9]{0,3})*)?[A-M|f-m])"
    r"|\x1b[A-M]"
)


def _rows(pattern: str, text: str, fixed: bool = False) -> list[dict[str, int]]:
    if pattern == "":
        return [
            {"start": index, "end": index - 1, "length": 0}
            for index in range(1, len(text) + 1)
        ]
    if fixed:
        found = []
        cursor = 0
        while True:
            at = text.find(pattern, cursor)
            if at < 0:
                break
            start = at + 1
            length = len(pattern)
            found.append({"start": start, "end": start + length - 1, "length": length})
            cursor = at + max(length, 1)
        return found
    found = []
    for match in re.finditer(pattern, text):
        start = match.start() + 1
        length = match.end() - match.start()
        found.append({"start": start, "end": start + length - 1, "length": length})
    return found


def _ansi_rows(text: str) -> list[dict[str, int]]:
    found = []
    for match in ANSI_REGEX.finditer(text):
        start = match.start() + 1
        length = match.end() - match.start()
        found.append({"start": start, "end": start + length - 1, "length": length})
    return found


def _non_matching(
    tables: list[list[dict[str, int]]],
    strings: list[str | None],
    empty: bool = False,
) -> list[list[dict[str, int]]]:
    result = []
    for rows, text in zip(tables, strings):
        if text is None:
            result.append([{"start": 1, "end": 0, "length": 0}])
            continue
        size = len(text)
        if not rows:
            result.append([{"start": 1, "end": size, "length": size}])
            continue
        starts = [1] + [row["end"] + 1 for row in rows]
        ends = [row["start"] - 1 for row in rows] + [size]
        made = []
        for start, end in zip(starts, ends):
            length = end - start + 1
            if empty or length != 0:
                made.append({"start": start, "end": end, "length": length})
        result.append(made)
    return result


def _map_to_ansi(
    strings: list[str | None],
    text: list[list[dict[str, int]]] | None = None,
):
    if text is None:
        tables = [_ansi_rows(item or "") for item in strings]
        text = _non_matching(tables, strings, empty=True)
    maps = []
    for rows in text:
        bounds = [1]
        acc = 1
        for row in rows:
            acc += row["length"]
            bounds.append(acc)
        bounds.append(math.inf)
        if rows:
            offset = [row["start"] - 1 for row in rows]
            offset.append(rows[-1]["end"])
        else:
            offset = []
        offset.append(None)
        maps.append((bounds, offset))

    def mapper(positions: list[int]) -> list[int | None]:
        if len(maps) == 0:
            return []
        if len(positions) >= len(maps):
            chosen = list(positions[: len(maps)])
        else:
            chosen = [positions[index % len(positions)] for index in range(len(maps))]
        located: list[int | None] = []
        for position, (bounds, offset) in zip(chosen, maps):
            if position < 1:
                located.append(position)
                continue
            slot = None
            for index, bound in enumerate(bounds):
                if position < bound:
                    slot = index - 1
                    break
            if slot is None or slot < 0 or offset[slot] is None:
                located.append(None)
                continue
            located.append(offset[slot] + position - bounds[slot] + 1)
        return located

    return mapper


def _r_substr(text: str, start: int, stop: int) -> str:
    if start < 1:
        start = 1
    if start > stop or start > len(text):
        return ""
    if stop > len(text):
        stop = len(text)
    return text[start - 1 : stop]


def _codes(text: str) -> str:
    if text == "":
        return ""
    return "".join(match.group(0) for match in ANSI_REGEX.finditer(text))


def _integers(value: Any) -> list[int | None]:
    if isinstance(value, bool):
        return [int(value)]
    if isinstance(value, int):
        return [value]
    if isinstance(value, float):
        if math.isnan(value):
            return [None]
        return [int(value)]
    if isinstance(value, str):
        try:
            if value.strip() == "" or any(ch in value for ch in ".eE+"):
                if re.fullmatch(r"[+-]?\d+", value):
                    return [int(value)]
                return [None]
            return [int(value)]
        except ValueError:
            return [None]
    if isinstance(value, (list, tuple)):
        found: list[int | None] = []
        for item in value:
            found.extend(_integers(item))
        return found
    return [None]


def strip_style(string: Any) -> Any:
    values = character_vector(string)
    cleaned: list[str | None] = []
    for item in values:
        if item is None:
            cleaned.append(None)
        else:
            cleaned.append(ANSI_REGEX.sub("", item))
    return one_or_many(cleaned)


def has_style(string: Any) -> Any:
    values = character_vector(string)
    flags = [False if item is None else ANSI_REGEX.search(item) is not None for item in values]
    return one_or_many(flags)


def _nchar_one(text: str | None, kind: str) -> int | None:
    if text is None:
        return None
    if kind == "bytes":
        return len(text.encode("utf-8"))
    return len(text)


def col_nchar(x: Any, type: str = "chars", **kwargs: Any) -> Any:
    del kwargs
    stripped = strip_style(x)
    values = stripped if isinstance(stripped, list) else [stripped]
    return one_or_many([_nchar_one(item, type) for item in values])


def col_substr(x: Any, start: Any, stop: Any) -> Any:
    values = character_vector(x)
    if len(values) == 0:
        return []
    starts = _integers(start)
    stops = _integers(stop)
    if len(starts) == 0 or len(stops) == 0:
        raise ValueError("invalid substring arguments")
    if any(item is None for item in starts) or any(item is None for item in stops):
        raise ValueError("non-numeric substring arguments not supported")
    tables = [_ansi_rows(item or "") for item in values]
    pieces = _non_matching(tables, values, empty=True)
    mapper = _map_to_ansi(values, pieces)
    mapped_start = mapper([int(item) for item in starts])
    mapped_stop = mapper([int(item) for item in stops])
    out: list[str | None] = []
    for text, left, right in zip(values, mapped_start, mapped_stop):
        if text is None or left is None or right is None:
            out.append(None)
            continue
        before = _r_substr(text, 1, left - 1)
        after = _r_substr(text, right + 1, len(text))
        middle = _r_substr(text, left, right)
        out.append(_codes(before) + middle + _codes(after))
    return one_or_many(out)


def col_substring(text: Any, first: Any, last: int = 1_000_000) -> Any:
    values = character_vector(text)
    first_v = first if isinstance(first, (list, tuple)) else [first]
    last_v = last if isinstance(last, (list, tuple)) else [last]
    count = max(len(values), len(first_v), len(last_v))
    if len(values) and len(values) < count:
        values = [values[index % len(values)] for index in range(count)]
    if len(values) == 0:
        return []
    return col_substr(values, _integers(first_v), _integers(last_v))


def col_strsplit(x: Any, split: Any, fixed: bool = False, **kwargs: Any) -> list[list[str]]:
    del kwargs
    try:
        if isinstance(split, (list, tuple)):
            if len(split) > 1:
                raise ValueError
            split = "" if len(split) == 0 else str(split[0])
        else:
            split = str(split)
    except Exception as exc:
        raise ValueError(
            "`split` must be character of length <= 1, or must coerce to that"
        ) from exc
    plain_value = strip_style(x)
    plain = plain_value if isinstance(plain_value, list) else [plain_value]
    sources = character_vector(x)
    pattern = "" if split is None else split
    splits = [_rows(pattern, item or "", fixed=fixed) for item in plain]
    chunks = _non_matching(splits, [item or "" for item in plain], empty=True)
    patterns = [pattern] * len(sources)
    trimmed = []
    for index, rows in enumerate(chunks):
        piece = list(rows)
        current = patterns[index] if index < len(patterns) else pattern
        if piece and current == "" and piece[0]["length"] == 0:
            piece = piece[1:]
        if piece and piece[-1]["length"] == 0:
            piece = piece[:-1]
        trimmed.append(piece)
    result: list[list[str]] = []
    for rows, source in zip(trimmed, sources):
        if source is None or not rows:
            result.append([])
            continue
        parts = col_substring(
            source,
            [row["start"] for row in rows],
            [row["end"] for row in rows],
        )
        if isinstance(parts, list):
            result.append(["" if part is None else part for part in parts])
        else:
            result.append([parts])
    return result


def _match_arg(value: Any, choices: tuple[str, ...]) -> str:
    if isinstance(value, (list, tuple)):
        if list(value) == list(choices):
            return choices[0]
        raise ValueError("align must be a single choice")
    text = str(value)
    matches = [choice for choice in choices if choice.startswith(text)]
    if len(matches) == 1:
        return matches[0]
    raise ValueError(f"'{text}' does not match one of {', '.join(choices)}")


def _spaces(count: int) -> str:
    if count <= 0:
        return ""
    return " " * count


def col_align(
    text: Any,
    width: Any = None,
    align: Any = ("left", "center", "right"),
    type: str = "width",
) -> Any:
    if width is None:
        width = get_option("width", 80)
    side = _match_arg(align, ("left", "center", "right"))
    values = character_vector(text)
    if len(values) == 0:
        return []
    counts = col_nchar(values, type=type)
    widths_n = counts if isinstance(counts, list) else [counts]
    width_v = width if isinstance(width, (list, tuple)) else [width]
    if len(width_v) == 1:
        width_v = width_v * len(values)
    elif len(width_v) < len(values):
        width_v = [width_v[index % len(width_v)] for index in range(len(values))]
    else:
        width_v = list(width_v[: len(values)])
    aligned = []
    for item, count, wide in zip(values, widths_n, width_v):
        if item is None or count is None or wide is None:
            aligned.append(None)
            continue
        gap = int(wide) - int(count)
        if side == "left":
            aligned.append(item + _spaces(gap))
        elif side == "center":
            left = math.ceil(gap / 2) if gap > 0 else 0
            right = math.floor(gap / 2) if gap > 0 else 0
            aligned.append(_spaces(left) + item + _spaces(right))
        else:
            aligned.append(_spaces(gap) + item)
    return one_or_many(aligned)
