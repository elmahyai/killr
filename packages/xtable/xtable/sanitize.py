"""sanitize from xtable 1.8-8.

The LaTeX path hides each backslash as the word ``SANITIZE.BACKSLASH``,
then replaces the other special characters, then writes that word as
``$\\backslash$``. A string that already contains the word is rewritten
too. Any ``type`` other than ``"latex"`` escapes ``&``, ``>``, and ``<``
for HTML, in that order, so the replacements are not escaped again.
"""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
_INT_MIN = -2147483647
_INT_MAX = 2147483647

# The same order as the R function. The backslash is replaced first, and
# the placeholder is replaced last, after ``$``, ``|``, ``{``, and ``}``
# have already been handled. Those characters inside a replacement stay.
_LATEX = (
    ("\\", "SANITIZE.BACKSLASH"),
    ("$", "\\$"),
    (">", "$>$"),
    ("<", "$<$"),
    ("|", "$|$"),
    ("{", "\\{"),
    ("}", "\\}"),
    ("%", "\\%"),
    ("&", "\\&"),
    ("_", "\\_"),
    ("#", "\\#"),
    ("^", "\\verb|^|"),
    ("~", "\\~{}"),
    ("SANITIZE.BACKSLASH", "$\\backslash$"),
)
_HTML = (
    ("&", "&amp;"),
    (">", "&gt;"),
    ("<", "&lt;"),
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


class Strings(list):
    """A character vector. ``names`` is R's names attribute."""

    def __init__(self, values, names=None):
        super().__init__(values)
        self.names = None if names is None else list(names)


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


def _items(text: object) -> tuple[list, list | None]:
    if isinstance(text, Strings):
        return list(text), text.names
    if isinstance(text, dict):
        return list(text.values()), [str(key) for key in text.keys()]
    if text is None:
        return [], None
    if is_na(text) or isinstance(text, (str, bool, int, float)):
        return [text], None
    if isinstance(text, (list, tuple)):
        return list(text), None
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
            if math.isnan(item):
                return "NaN"
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
        if math.isnan(item):
            return "NaN"
        return _character_double(item)
    raise ValueError(
        f"cannot coerce type '{type(item).__name__}' to vector of type 'character'"
    )


def _as_character(text: object) -> tuple[list, list | None]:
    items, names = _items(text)
    mode = _mode(items)
    values = [_one(item, mode) for item in items]
    if names is not None and len(names) != len(values):
        names = None
    return values, names


def _is_latex(kind: object) -> bool:
    """R's ``if (type == "latex")``."""

    if isinstance(kind, Strings):
        kind = list(kind)
    if kind is None:
        raise ValueError("argument is of length zero")
    if isinstance(kind, (list, tuple)):
        if len(kind) == 0:
            raise ValueError("argument is of length zero")
        if len(kind) > 1:
            raise ValueError("the condition has length > 1")
        kind = kind[0]
    if kind is NA:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(kind, str):
        return kind == "latex"
    text = _one(kind, _mode([kind]))
    if text is NA:
        raise ValueError("missing value where TRUE/FALSE needed")
    return text == "latex"


def _replace(values: list, pairs: tuple[tuple[str, str], ...]) -> list:
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


def sanitize(str, type="latex"):
    """Sanitize characters that are special in LaTeX or HTML.

    ``str`` is an atomic vector: a string, number, or logical, or a list
    of those. ``None`` is ``NULL`` and returns an empty vector. A missing
    element stays missing. ``type`` ``"latex"`` is the LaTeX path. Every
    other length-one value takes the HTML path. ``gsub`` coerces ``str``
    with ``as.character`` before replacing.
    """

    values, names = _as_character(str)
    pairs = _LATEX if _is_latex(type) else _HTML
    return Strings(_replace(values, pairs), names)
