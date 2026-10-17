"""CSS length checks, the htmltools function shiny 1.14.0 re-exports."""

from __future__ import annotations

import math
import re
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

from shiny.values import Missing, ShinyError, Vector

# R's default TRE engine. `.` matches a newline, and `\d` is ASCII.
_CSS = re.compile(
    r"^(?:auto|inherit|fit-content|calc\(.*\)|(?:\.\d+|\d+(?:\.\d+)?)(?:%|in|cm|mm|ch|em|ex|rem|pt|pc|px|vh|vw|vmin|vmax))$",
    re.DOTALL,
)
_DIGITS = re.compile(r"[0-9]*")
_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
_UNIT_ERROR = '"{}" is not a valid CSS unit (e.g., "100%", "400px", "auto")'
_TYPE_ERROR = "CSS units must be a single-element numeric or character vector"


def validateCssUnit(x):
    """A CSS length, or the original missing value.

    ``NULL`` and ``NA`` are returned unchanged. A single number is turned
    into that many pixels. A single string must be ``auto``, ``inherit``,
    ``fit-content``, ``calc(...)``, or a number with a CSS length unit.
    A string of digits is read as a number of pixels.
    """

    if x is None:
        return None
    flags = _na_flags(x)
    if len(flags) == 0:
        raise ShinyError("missing value where TRUE/FALSE needed")
    if len(flags) != 1:
        raise ShinyError(f"'length = {len(flags)}' in coercion to 'logical(1)'")
    if flags[0]:
        return x
    if _length(x) > 1 or (not _is_character(x) and not _is_numeric(x)):
        raise ShinyError(_TYPE_ERROR)
    if _is_character(x):
        text = _one_string(x)
        if len(text) > 0 and _DIGITS.sub("", text) == "":
            x = float(text)
        elif _CSS.fullmatch(text) is None:
            raise ShinyError(_UNIT_ERROR.format(text))
        else:
            return text
    if _is_numeric(x):
        return _paste_px(x)
    return x


def _na_flags(value) -> list[bool]:
    if isinstance(value, Vector):
        return [_is_na_atom(item, value.mode) for item in value.data]
    if isinstance(value, list):
        return [_is_na_list_element(item) for item in value]
    if isinstance(value, (bytes, bytearray)):
        return [False] * len(value)
    if isinstance(value, Missing):
        return [True]
    if isinstance(value, float) and math.isnan(value):
        return [True]
    return [False]


def _is_na_atom(item, mode: str) -> bool:
    if isinstance(item, Missing):
        return True
    if mode == "double" and isinstance(item, float) and math.isnan(item):
        return True
    if mode == "complex" and isinstance(item, complex):
        return math.isnan(item.real) or math.isnan(item.imag)
    return False


def _is_na_list_element(item) -> bool:
    if isinstance(item, Missing):
        return True
    if isinstance(item, float) and math.isnan(item):
        return True
    if isinstance(item, Vector) and len(item.data) == 1:
        return _is_na_atom(item.data[0], item.mode)
    return False


def _length(value) -> int:
    if isinstance(value, Vector):
        return len(value.data)
    if isinstance(value, list):
        return len(value)
    if isinstance(value, (bytes, bytearray)):
        return len(value)
    return 1


def _is_character(value) -> bool:
    if isinstance(value, str):
        return True
    return isinstance(value, Vector) and value.mode == "character"


def _is_numeric(value) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return True
    return isinstance(value, Vector) and value.mode in ("integer", "double")


def _one_string(value) -> str:
    if isinstance(value, str):
        return value
    return value.data[0]


def _paste_px(value) -> str:
    if isinstance(value, Vector):
        item = value.data[0]
        if value.mode == "integer":
            return str(int(item)) + "px"
        return _character_double(float(item)) + "px"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value) + "px"
    return _character_double(float(value)) + "px"


def _character_double(value: float) -> str:
    """R ``as.character`` for one double.

    Fifteen significant digits, or sixteen when the magnitude sits in
    ``[1e15, 1e16)``. Scientific notation is used when it is shorter than
    fixed notation. An exact integer is kept when that text is no longer
    than the scientific form.
    """

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = math.copysign(1.0, value) < 0
    magnitude = abs(value)
    digits = 16 if 1e15 <= magnitude < 1e16 else 15
    with localcontext(_DECIMAL):
        rounded = _round_sig(Decimal(magnitude), digits)
        fixed, scientific = _fixed_and_sci(rounded)
    if negative:
        fixed = "-" + fixed
        scientific = "-" + scientific
    if magnitude.is_integer():
        exact = str(int(magnitude))
        if negative:
            exact = "-" + exact
        if len(exact) <= len(scientific):
            return exact
    if len(scientific) < len(fixed):
        return scientific
    return fixed


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
