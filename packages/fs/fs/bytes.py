"""Human-readable file sizes from fs 2.1.0.

``None`` is R's NA. ``float('nan')`` is R's NaN.
"""

from __future__ import annotations

import math
import re

_UNITS = (
    ("B", 1.0),
    ("K", 1024.0),
    ("M", 1024.0**2),
    ("G", 1024.0**3),
    ("T", 1024.0**4),
    ("P", 1024.0**5),
    ("E", 1024.0**6),
    ("Z", 1024.0**7),
    ("Y", 1024.0**8),
)
_UNIT_SIZE = {name: size for name, size in _UNITS}
_PARSE = re.compile(r"^(?P<size>[\d.]+)\s*(?P<unit>[KMGTPEZY]?)i?[Bb]?$")
_ARITHMETIC = {"+", "-", "*", "/", "^"}
_COMPARE = {"<", ">", "==", "!=", "<=", ">="}


class FsBytes(list):
    """A numeric vector of byte counts. Text such as ``1KB`` is 1024 bytes."""

    def __str__(self) -> str:
        return " ".join(format_fs_bytes(self))


def _parse_one(text: str) -> float | None:
    match = _PARSE.fullmatch(text)
    if match is None:
        return None
    size = match.group("size")
    if size.count(".") > 1:
        return None
    try:
        magnitude = float(size)
    except ValueError:
        return None
    unit = match.group("unit") or "B"
    return magnitude * _UNIT_SIZE[unit]


_MISSING = object()


def fs_bytes(x=_MISSING) -> FsBytes:
    """Coerce ``x`` to byte sizes. Numbers are counts. Text is parsed."""
    if x is _MISSING:
        return FsBytes()
    if x is None:
        return FsBytes([None])
    if isinstance(x, FsBytes):
        return FsBytes(x)
    if isinstance(x, bool):
        return FsBytes([float(x)])
    if isinstance(x, (int, float)):
        if isinstance(x, float) and math.isnan(x):
            return FsBytes([float("nan")])
        return FsBytes([float(x)])
    if isinstance(x, (list, tuple)):
        return FsBytes([_coerce_item(item) for item in x])
    return FsBytes([_parse_one(str(x))])


def _coerce_item(item):
    if item is None:
        return None
    if isinstance(item, str):
        return _parse_one(item)
    if isinstance(item, bool):
        return float(item)
    if isinstance(item, (int, float)):
        return float(item)
    return _parse_one(str(item))


as_fs_bytes = fs_bytes


def _significant(value: float, digits: int = 3) -> float:
    if value == 0 or not math.isfinite(value):
        return value
    power = math.floor(math.log10(abs(value)))
    factor = 10 ** (digits - 1 - power)
    return round(value * factor) / factor


def _places(value: float) -> int:
    rounded = _significant(value)
    if rounded == 0 or not math.isfinite(rounded):
        return 0
    text = f"{rounded:.12f}".rstrip("0")
    if "." not in text:
        return 0
    return len(text.split(".", 1)[1])


def _drop0(text: str) -> str:
    if text is None or "." not in text:
        return text
    head, tail = text.split(".", 1)
    tail = tail.rstrip("0")
    if not tail:
        return head
    return f"{head}.{tail}"


def _format_field(values: list[float | None]) -> list[str]:
    """Match ``format(x, scientific=FALSE, digits=3, drop0trailing=TRUE)``."""
    finite = [value for value in values if value is not None and math.isfinite(value)]
    places = max((_places(value) for value in finite), default=0)
    raw = []
    for value in values:
        if value is None:
            raw.append("NA")
        elif isinstance(value, float) and math.isnan(value):
            raw.append("NaN")
        elif math.isinf(value):
            raw.append("Inf" if value > 0 else "-Inf")
        else:
            raw.append(f"{value:.{places}f}")
    width = max((len(text) for text in raw), default=0)
    justified = [text.rjust(width) for text in raw]
    return [_drop0(text) for text in justified]


def format_fs_bytes(x, scientific: bool = False, digits: int = 3) -> list[str]:
    """Format sizes in units of 1024, the way ``format.fs_bytes`` does."""
    values = list(fs_bytes(x))
    scaled: list[float | None] = []
    units: list[str] = []
    for value in values:
        if value is None:
            scaled.append(None)
            units.append("")
            continue
        if isinstance(value, float) and math.isnan(value):
            scaled.append(float("nan"))
            units.append("")
            continue
        if value == 0:
            scaled.append(0.0)
            units.append("")
            continue
        if value < 0:
            scaled.append(float("nan"))
            units.append("NA")
            continue
        if math.isinf(value):
            exponent = len(_UNITS) - 1
        else:
            exponent = min(int(math.floor(math.log(value, 1024))), len(_UNITS) - 1)
        scaled.append(round(value / (1024**exponent), 2))
        units.append("" if exponent == 0 else _UNITS[exponent][0])
    return [text + unit for text, unit in zip(_format_field(scaled), units)]


def sum_bytes(*parts) -> FsBytes:
    total = 0.0
    seen = False
    for part in parts:
        for value in fs_bytes(part):
            seen = True
            if value is None or (isinstance(value, float) and math.isnan(value)):
                return FsBytes([None if value is None else float("nan")])
            total += value
    if not seen:
        return FsBytes([0.0])
    return FsBytes([total])


def min_bytes(x) -> FsBytes:
    values = list(fs_bytes(x))
    if any(value is None for value in values):
        return FsBytes([None])
    finite = [value for value in values if not (isinstance(value, float) and math.isnan(value))]
    if not finite:
        return FsBytes([float("nan")])
    return FsBytes([min(finite)])


def max_bytes(x) -> FsBytes:
    values = list(fs_bytes(x))
    if any(value is None for value in values):
        return FsBytes([None])
    finite = [value for value in values if not (isinstance(value, float) and math.isnan(value))]
    if not finite:
        return FsBytes([float("nan")])
    return FsBytes([max(finite)])


def operate(op: str, left, right):
    """Arithmetic keeps byte sizes. Comparisons follow R, and NA compares as missing."""
    if op not in _ARITHMETIC and op not in _COMPARE:
        raise TypeError(f"'{op}' not defined for \"fs_bytes\" objects")
    ones = list(fs_bytes(left))
    twos = list(fs_bytes(right))
    if len(ones) == 1 and len(twos) != 1:
        ones = ones * len(twos)
    elif len(twos) == 1 and len(ones) != 1:
        twos = twos * len(ones)
    if op in _COMPARE:
        return [_compare(op, one, two) for one, two in zip(ones, twos)]
    return FsBytes([_arith(op, one, two) for one, two in zip(ones, twos)])


def _missing(value) -> bool:
    return value is None or (isinstance(value, float) and math.isnan(value))


def _compare(op: str, left, right):
    if _missing(left) or _missing(right):
        return None
    return {
        "<": left < right,
        ">": left > right,
        "<=": left <= right,
        ">=": left >= right,
        "==": left == right,
        "!=": left != right,
    }[op]


def _arith(op: str, left, right):
    if left is None or right is None:
        return None
    if isinstance(left, float) and math.isnan(left):
        return float("nan")
    if isinstance(right, float) and math.isnan(right):
        return float("nan")
    if op == "+":
        return left + right
    if op == "-":
        return left - right
    if op == "*":
        return left * right
    if op == "/":
        return left / right
    return left**right
