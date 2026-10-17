"""isOrdered from xts 0.14.3. The loops follow isOrdered.c."""

from __future__ import annotations

_NA_INTEGER = -2147483648


class XtsError(Exception):
    """An error raised with R's stop message."""


def isOrdered(x, increasing: bool = True, strictly: bool = True) -> bool:
    """Whether ``x`` is ordered. An empty vector is ordered."""
    if x is None:
        return True
    values = list(x)
    if any(isinstance(item, str) for item in values):
        raise XtsError("character ordering unsupported")
    if values and not all(_is_number(item) or item is None for item in values):
        values = [float(item) for item in values]
    if len(values) <= 1:
        return True
    integers = all(isinstance(item, int) and not isinstance(item, bool) or item is None for item in values)
    if integers:
        return _ordered_integer(values, increasing, strictly)
    return _ordered_real([float(item) for item in values], increasing, strictly)


def _ordered_real(values: list[float], increasing: bool, strictly: bool) -> bool:
    pairs = zip(values, values[1:])
    if increasing and strictly:
        return all(right > left for left, right in pairs)
    if increasing:
        return all(right >= left for left, right in pairs)
    if strictly:
        return all(right < left for left, right in pairs)
    return all(right <= left for left, right in pairs)


def _ordered_integer(values: list, increasing: bool, strictly: bool) -> bool:
    numbers = [_NA_INTEGER if item is None else int(item) for item in values]
    last = len(numbers) - 1
    if increasing:
        if numbers[0] == _NA_INTEGER:
            return False
        for index in range(last):
            follows = numbers[index + 1] <= numbers[index] if strictly else numbers[index + 1] < numbers[index]
            if follows:
                if index == last - 1 and numbers[index + 1] == _NA_INTEGER:
                    continue
                return False
        return True
    if numbers[last] == _NA_INTEGER:
        return False
    for index in range(last):
        follows = numbers[index + 1] >= numbers[index] if strictly else numbers[index + 1] > numbers[index]
        if follows:
            if index == 0 and numbers[index] == _NA_INTEGER:
                continue
            return False
    return True


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
