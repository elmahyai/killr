"""Roman numeral conversion and arithmetic (``utils::as.roman``)."""

from __future__ import annotations

import math
import operator
import re
from collections.abc import Iterable

_TOKENS = (
    ("M", 1000),
    ("CM", 900),
    ("D", 500),
    ("CD", 400),
    ("C", 100),
    ("XC", 90),
    ("L", 50),
    ("XL", 40),
    ("X", 10),
    ("IX", 9),
    ("V", 5),
    ("IV", 4),
    ("I", 1),
)
_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
_ROMAN_RE = re.compile(r"^M{0,9}D?C{0,6}L?X{0,6}V?I{0,6}$")
_MAX_ROMAN = 3899


class Roman(list):
    """A small vector class carrying R's ``roman`` arithmetic semantics."""

    def __init__(self, values: Iterable[int | None] = ()):
        super().__init__(values)

    def __str__(self) -> str:
        return " ".join(_number_to_roman(value) or "NA" for value in self)

    def __repr__(self) -> str:
        return str(self)

    def __eq__(self, other):
        if isinstance(other, Roman):
            return _recycle_compare(self, other, operator.eq)
        return list.__eq__(self, other)

    def __lt__(self, other):
        return _recycle_compare(self, _as_roman_operand(other), operator.lt)

    def __le__(self, other):
        return _recycle_compare(self, _as_roman_operand(other), operator.le)

    def __gt__(self, other):
        return _recycle_compare(self, _as_roman_operand(other), operator.gt)

    def __ge__(self, other):
        return _recycle_compare(self, _as_roman_operand(other), operator.ge)

    def _op(self, other, fn):
        right = other if isinstance(other, Roman) else as_roman(other)
        return Roman(_recycle_binary(self, right, fn))

    def __add__(self, other):
        return self._op(other, operator.add)

    def __radd__(self, other):
        return as_roman(other)._op(self, operator.add)

    def __sub__(self, other):
        return self._op(other, operator.sub)

    def __rsub__(self, other):
        return as_roman(other)._op(self, operator.sub)

    def __mul__(self, other):
        return self._op(other, operator.mul)

    def __rmul__(self, other):
        return as_roman(other)._op(self, operator.mul)

    def __truediv__(self, other):
        return self._op(other, lambda a, b: a / b if b is not None and b != 0 else None)

    def __rtruediv__(self, other):
        return as_roman(other)._op(self, lambda a, b: a / b if b is not None and b != 0 else None)

    def __pow__(self, other):
        return self._op(other, operator.pow)

    def __floordiv__(self, other):
        return self._op(other, operator.floordiv)

    def __mod__(self, other):
        return self._op(other, operator.mod)


def as_roman(x):
    """Coerce numbers and character numerals to a ``Roman`` vector.

    Character strings made solely of decimal digits are treated as numbers;
    other strings use R's permissive Roman grammar.  Values outside 1..3899
    are represented by ``None`` (R's ``NA``).
    """
    scalar = isinstance(x, (str, int, float, bool)) or x is None
    items = [x] if scalar else list(x)
    values = [_coerce_one(item) for item in items]
    result = Roman(values)
    return result


def _coerce_one(value):
    if value is None:
        return None
    if isinstance(value, str):
        if value == "" or value.isdigit():
            try:
                return _range(int(value)) if value else None
            except ValueError:
                return None
        return _roman_to_number(value)
    if isinstance(value, bool):
        return _range(int(value))
    if isinstance(value, (int, float)):
        if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
            return None
        return _range(math.trunc(value))
    raise TypeError("cannot coerce 'x' to roman")


def _range(value):
    return value if 1 <= value <= _MAX_ROMAN else None


def _as_roman_operand(value):
    return value if isinstance(value, Roman) else as_roman(value)


def _roman_to_number(text: str):
    upper = text.upper()
    expanded = upper
    for pair, replacement in (("CM", "DCCCC"), ("CD", "CCCC"), ("XC", "LXXXX"),
                               ("XL", "XXXX"), ("IX", "VIIII"), ("IV", "IIII")):
        expanded = expanded.replace(pair, replacement)
    if not _ROMAN_RE.fullmatch(expanded):
        return None
    total = sum(_VALUES[char] for char in expanded)
    return _range(total)


def _number_to_roman(value):
    if value is None:
        return None
    value = math.trunc(value)
    if not 1 <= value <= _MAX_ROMAN:
        return None
    output = []
    for token, amount in _TOKENS:
        count, value = divmod(value, amount)
        output.append(token * count)
    return "".join(output)


def _recycle_binary(left, right, fn):
    if not left or not right:
        return []
    return [_binary_value(left[i % len(left)], right[i % len(right)], fn)
            for i in range(max(len(left), len(right)))]


def _binary_value(left, right, fn):
    if left is None or right is None:
        return None
    try:
        return _range(fn(left, right))
    except (ArithmeticError, ValueError):
        return None


def _recycle_compare(left, right, fn):
    if not left or not right:
        return []
    return [None if (a is None or b is None) else fn(a, b)
            for i in range(max(len(left), len(right)))
            for a, b in [(left[i % len(left)], right[i % len(right)])]]
