"""HTML escaping from htmltools 0.5.9.

``htmlEscape`` coerces with ``as.character``, then replaces ``&``, ``<``,
and ``>``. With ``attribute`` true it also replaces quotes, carriage
return, and newline. Replacements are not scanned again, so ``&amp;``
stays a single escape.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
_INT_MIN = -2147483647
_INT_MAX = 2147483647

_TRUE_WORDS = {"TRUE", "True", "true", "T"}
_FALSE_WORDS = {"FALSE", "False", "false", "F"}

# The same order as the R loop. ``&`` is first, so a replacement such as
# ``&amp;`` is not escaped again.
_TEXT_PAIRS = (("&", "&amp;"), ("<", "&lt;"), (">", "&gt;"))
_ATTR_PAIRS = _TEXT_PAIRS + (
    ("'", "&#39;"),
    ('"', "&quot;"),
    ("\r", "&#13;"),
    ("\n", "&#10;"),
)


class NAType:
    """R's missing value. The string ``"NA"`` is a real string."""

    def __repr__(self) -> str:
        return "NA"

    def __str__(self) -> str:
        return "NA"

    def __eq__(self, other: object) -> bool:
        return other is NA

    def __hash__(self) -> int:
        return id(NAType)

    def __bool__(self) -> bool:
        raise ValueError("missing value where TRUE/FALSE needed")


NA = NAType()


def is_na(value: object) -> bool:
    return value is NA


def _round_sig(value: Decimal, digits: int) -> Decimal:
    if value == 0:
        return Decimal(0)
    adjusted = value.adjusted()
    quantum = Decimal("1e{}".format(adjusted - (digits - 1)))
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if rounded != 0 and rounded.adjusted() > adjusted:
        adjusted = rounded.adjusted()
        quantum = Decimal("1e{}".format(adjusted - (digits - 1)))
        rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return rounded


def _fixed_and_sci(rounded: Decimal) -> tuple[str, str]:
    if rounded == 0:
        return "0", "0e+00"
    text = format(rounded, "f")
    if "." in text:
        whole, frac = text.split(".")
        digits = (whole + frac).lstrip("0").rstrip("0") or "0"
    else:
        digits = text.lstrip("0").rstrip("0") or "0"
    adjusted = rounded.adjusted()
    if adjusted >= 0:
        if adjusted + 1 >= len(digits):
            fixed = digits + ("0" * (adjusted + 1 - len(digits)))
        else:
            fixed = digits[: adjusted + 1] + "." + digits[adjusted + 1 :]
    else:
        fixed = "0." + ("0" * (-adjusted - 1)) + digits
    mantissa = digits if len(digits) == 1 else digits[0] + "." + digits[1:]
    return fixed, f"{mantissa}e{adjusted:+03d}"


def _character_double(value: float) -> str:
    """R ``as.character`` for one double.

    Fifteen significant digits, or sixteen when the magnitude is in
    ``[1e15, 1e16)``. The shorter of the fixed and scientific forms
    wins. On a tie, a one-digit mantissa uses scientific notation when
    the exponent is at most -4 or at least 5. An exact integer keeps
    its digits when that text is shorter than the scientific form.
    The exponent has a sign and at least two digits.
    """

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0.0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = math.copysign(1.0, value) < 0.0
    magnitude = abs(value)
    digits = 16 if 1e15 <= magnitude < 1e16 else 15
    with localcontext(_DECIMAL):
        rounded = _round_sig(Decimal(magnitude), digits)
        fixed, scientific = _fixed_and_sci(rounded)
        exponent = rounded.adjusted()
    # An exact integer keeps every digit when that text is shorter than
    # scientific notation, and also when the two are the same length and
    # the scientific mantissa has a decimal point. Rounding to 15 digits
    # would turn the spare digits into zeros. A one-digit power of ten
    # such as 1e+05 stays scientific: its exact text is not shorter, and
    # the mantissa has no decimal point.
    if magnitude.is_integer():
        exact = str(int(magnitude))
        mantissa = scientific.split("e", 1)[0]
        if len(exact) < len(scientific) or (
            len(exact) == len(scientific) and "." in mantissa
        ):
            chosen = exact
        else:
            chosen = _choose_notation(fixed, scientific, exponent)
    else:
        chosen = _choose_notation(fixed, scientific, exponent)
    if negative:
        return "-" + chosen
    return chosen


def _choose_notation(fixed: str, scientific: str, exponent: int) -> str:
    """Pick fixed or scientific the way R's as.character does at scipen 0.

    The shorter text wins. On a tie, a mantissa with a decimal point stays
    fixed. A one-digit mantissa uses scientific notation when the exponent
    is -4 or less, or 5 or more, and stays fixed for exponents -3 through 4.
    """

    if len(scientific) < len(fixed):
        return scientific
    if len(scientific) > len(fixed):
        return fixed
    mantissa = scientific.split("e", 1)[0]
    if "." in mantissa:
        return fixed
    if exponent <= -4 or exponent >= 5:
        return scientific
    return fixed


def _character_integer(value: int) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if _INT_MIN <= value <= _INT_MAX:
        return str(value)
    return _character_double(float(value))


def _as_flag(attribute: object) -> bool:
    """R's ``if (attribute)`` on one value."""

    if isinstance(attribute, (list, tuple)):
        if len(attribute) == 0:
            raise ValueError("argument is of length zero")
        if len(attribute) > 1:
            raise ValueError("the condition has length > 1")
        raise ValueError("argument is not interpretable as logical")
    if attribute is None:
        raise ValueError("argument is of length zero")
    if attribute is NA:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(attribute, bool):
        return attribute
    if isinstance(attribute, int):
        return attribute != 0
    if isinstance(attribute, float):
        if math.isnan(attribute):
            raise ValueError("argument is not interpretable as logical")
        return attribute != 0.0
    if isinstance(attribute, str):
        if attribute in _TRUE_WORDS:
            return True
        if attribute in _FALSE_WORDS:
            return False
        raise ValueError("argument is not interpretable as logical")
    raise ValueError("argument is not interpretable as logical")


def _items(text: object) -> list:
    if text is None:
        return []
    if is_na(text) or isinstance(text, (str, bool, int, float)):
        return [text]
    if isinstance(text, (list, tuple)):
        return list(text)
    raise ValueError(
        f"cannot coerce type '{type(text).__name__}' to vector of type 'character'"
    )


def _mode(items: list) -> str:
    if any(isinstance(item, str) for item in items):
        return "character"
    if any(isinstance(item, float) for item in items):
        return "double"
    if any(isinstance(item, int) and not isinstance(item, bool) for item in items):
        return "integer"
    return "logical"


def _one(item: object, mode: str) -> str | NAType:
    if is_na(item):
        return NA
    if mode == "logical":
        if isinstance(item, bool):
            return "TRUE" if item else "FALSE"
        raise ValueError(
            f"cannot coerce type '{type(item).__name__}' to vector of type 'character'"
        )
    if mode == "integer":
        if isinstance(item, bool):
            return _character_integer(item)
        if isinstance(item, int):
            return _character_integer(item)
        raise ValueError(
            f"cannot coerce type '{type(item).__name__}' to vector of type 'character'"
        )
    if mode == "double":
        if isinstance(item, bool):
            return _character_double(1.0 if item else 0.0)
        if isinstance(item, int):
            return _character_double(float(item))
        if isinstance(item, float):
            return _character_double(item)
        raise ValueError(
            f"cannot coerce type '{type(item).__name__}' to vector of type 'character'"
        )
    if isinstance(item, str):
        return item
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, int):
        return _character_integer(item)
    if isinstance(item, float):
        return _character_double(item)
    raise ValueError(
        f"cannot coerce type '{type(item).__name__}' to vector of type 'character'"
    )


def _as_character(text: object) -> list:
    items = _items(text)
    mode = _mode(items)
    return [_one(item, mode) for item in items]


def _escape(values: list, pairs: tuple[tuple[str, str], ...]) -> list:
    needles = tuple(old for old, _new in pairs)

    def hits(item: object) -> bool:
        return isinstance(item, str) and any(needle in item for needle in needles)

    if not any(hits(item) for item in values):
        return list(values)
    out: list = []
    for item in values:
        if not isinstance(item, str):
            out.append(item)
            continue
        for old, new in pairs:
            if old in item:
                item = item.replace(old, new)
        out.append(item)
    return out


def htmlEscape(text, attribute=False):
    """Escape HTML entities in ``text``.

    ``text`` is an atomic vector: a string, number, or logical, or a
    list of those. ``None`` is ``NULL`` and returns an empty list. A
    missing element stays missing. ``attribute`` follows R's ``if``:
    true also escapes ``'``, ``"``, carriage return, and newline.
    """

    flag = _as_flag(attribute)
    values = _as_character(text)
    if flag:
        return _escape(values, _ATTR_PAIRS)
    return _escape(values, _TEXT_PAIRS)
