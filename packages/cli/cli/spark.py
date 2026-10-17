"""Sparkline bar and line graphs."""

from __future__ import annotations

import math

from cli.unicode_output import is_utf8_output


def _seq(start: float, end: float, length: int) -> list[float]:
    if length == 1:
        return [float(start)]
    span = end - start
    return [start + span * (index / (length - 1)) for index in range(length)]


def _missing(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def _numeric(x) -> list[float]:
    if isinstance(x, (int, float)) and not isinstance(x, bool):
        values = [x]
    else:
        values = list(x)
    out = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, (int, float)) and value is not None:
            raise TypeError("sparkline input must be numeric")
        if _missing(value):
            out.append(float("nan"))
        else:
            out.append(float(value))
    return out


def spark_bar_chars(x, bars: list[str] | None = None) -> list[str]:
    values = _numeric(x)
    if bars is None:
        if is_utf8_output():
            bars = [chr(code) for code in range(0x2581, 0x2589)]
        else:
            bars = ["_", ",", "*", "#"]
    breaks = _seq(0, 1, len(bars) + 1)
    chars = []
    for value in values:
        if _missing(value) or value < breaks[0] or value > breaks[-1]:
            chars.append(" ")
            continue
        chosen = " "
        for index in range(len(bars)):
            left = breaks[index]
            right = breaks[index + 1]
            inside = left <= value <= right if index == 0 else left < value <= right
            if inside:
                chosen = bars[index]
                break
        chars.append(chosen)
    return chars


def spark_bar(x) -> str:
    """Block sparkline. Values outside 0 to 1, and missing values, are spaces."""

    return "".join(spark_bar_chars(x))


def _find_interval(value: float, vec: list[float]) -> int:
    """1-based findInterval with all.inside = TRUE."""

    if _missing(value):
        return 0
    n = len(vec)
    if value < vec[0]:
        return 1
    if value >= vec[-1]:
        return n - 1
    index = 0
    while index < n and vec[index] <= value:
        index += 1
    return index


def _braille(indexes: list[int]) -> str:
    remap = [7, 3, 2, 1, 8, 6, 5, 4]
    dots = [remap[item - 1] for item in indexes]
    raised = [dot in dots for dot in range(1, 9)]
    value = 10240 + sum((1 if bit else 0) * (1 << position) for position, bit in enumerate(raised))
    return chr(value)


def spark_line(x) -> str:
    """Braille sparkline, or an ASCII stand-in when UTF-8 output is off."""

    values = _numeric(x)
    if len(values) % 2 == 1:
        values.append(float("nan"))
    if is_utf8_output():
        breaks = _seq(0, 1, 5)
        indexes = [_find_interval(value, breaks) for value in values]
        chars = []
        for start in range(0, len(indexes), 2):
            pair = indexes[start : start + 2]
            if any(item == 0 for item in pair):
                chars.append(" ")
                continue
            chars.append(_braille([pair[0], pair[1] + 4]))
        return "".join(chars)
    pairs = []
    for start in range(0, len(values), 2):
        left, right = values[start], values[start + 1]
        if _missing(left) or _missing(right):
            pairs.append(float("nan"))
        else:
            pairs.append((left + right) / 2)
    return "".join(spark_bar_chars(pairs, ["_", ",", "-", "^"]))
