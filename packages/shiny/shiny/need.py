"""Validation messages, from shiny 1.14.0 `R/utils.R`."""

from __future__ import annotations

import math
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

from shiny.truthy import isTruthy
from shiny.values import Missing, ShinyError, Vector, WithClass

_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
_MISSING = object()
_FORMALS = ("expr", "message", "label")
_EMPTY_DEPARSE = {
    "double": "numeric(0)",
    "integer": "integer(0)",
    "logical": "logical(0)",
    "character": "character(0)",
    "complex": "complex(0)",
    "raw": "raw(0)",
}


class Delayed:
    """An R promise. Forced once, the first time `need` reaches it."""

    def __init__(self, fn) -> None:
        self._fn = fn
        self._forced = False
        self._value = None

    def force(self):
        if not self._forced:
            self._value = self._fn()
            self._forced = True
        return self._value


class Invisible:
    """R's invisible return. A truthy `expr` is invisible NULL."""

    def __init__(self, value) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"Invisible({self.value!r})"


class NeedError(Exception):
    """An error `need` raises before it tests the value."""

    def __init__(self, message: str, classes) -> None:
        super().__init__(message)
        self.message = message
        self.classes = tuple(classes)


def need(*args, **kwargs):
    """Return `message` when `expr` is not truthy, otherwise invisible NULL.

    `message` or `label` is required. With only `label`, the message is
    ``paste(label, "must be provided")``. `message` is forced before
    `expr`, and `label` is forced only when that default message is built.
    A shorter name selects the same argument. ``FALSE`` is a silent failure.
    """
    bound, unused = _bind(args, kwargs)
    if unused:
        raise _unused_error(unused)
    expr = bound.get("expr", _MISSING)
    message = bound.get("message", _MISSING)
    label = bound.get("label", _MISSING)
    if message is _MISSING and label is _MISSING:
        raise NeedError(
            "`need()` requires either a `message` or `label` argument.",
            ("rlang_error", "error", "condition"),
        )
    if message is _MISSING:
        message = _default_message(_force(label))
    else:
        message = _force(message)
    expr = _force(expr)
    if expr is _MISSING:
        raise NeedError(
            'argument "expr" is missing, with no default',
            ("getvarError", "missingArgError", "error", "condition"),
        )
    if not isTruthy(expr):
        return message
    return Invisible(None)


def _bind(args, kwargs):
    bound = {}
    unused = []
    exact = {key: value for key, value in kwargs.items() if key in _FORMALS}
    bound.update(exact)
    remaining = [name for name in _FORMALS if name not in bound]
    for key, value in kwargs.items():
        if key in exact:
            continue
        matches = [name for name in remaining if name.startswith(key)]
        if len(matches) == 1:
            bound[matches[0]] = value
            remaining.remove(matches[0])
        else:
            unused.append(f"{key} = {_deparse(value)}")
    open_formals = [name for name in _FORMALS if name not in bound]
    for index, value in enumerate(args):
        if index < len(open_formals):
            bound[open_formals[index]] = value
        else:
            unused.append(_deparse(value))
    return bound, unused


def _unused_error(items):
    if len(items) == 1:
        text = f"unused argument ({items[0]})"
    else:
        text = "unused arguments (" + ", ".join(items) + ")"
    return NeedError(text, ("simpleError", "error", "condition"))


def _deparse(value) -> str:
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _character_double(value)
    if value is None:
        return "NULL"
    return str(value)


def _force(value):
    if isinstance(value, Delayed):
        return value.force()
    return value


def _default_message(label):
    pieces = _paste_strings(label)
    if len(pieces) == 0:
        pieces = [""]
    texts = [f"{piece} must be provided" for piece in pieces]
    if len(texts) == 1:
        return texts[0]
    return Vector(texts, "character")


def _paste_strings(label) -> list[str]:
    if isinstance(label, list):
        return [_list_element(item) for item in label]
    return _atomic_strings(label)


def _list_element(item) -> str:
    if item is None:
        return "NULL"
    if isinstance(item, Vector) and len(item.data) == 0:
        return _EMPTY_DEPARSE[item.mode]
    if isinstance(item, (bytes, bytearray)) and len(item) == 0:
        return "raw(0)"
    parts = _atomic_strings(item)
    if len(parts) == 0:
        return "NULL"
    if len(parts) != 1:
        raise ShinyError("list element must have length 1")
    return parts[0]


def _atomic_strings(label) -> list[str]:
    if isinstance(label, WithClass) and "factor" in label.classes:
        return _factor_strings(label)
    if isinstance(label, WithClass):
        return _atomic_strings(label.value)
    if label is None:
        return []
    if isinstance(label, Missing):
        return ["NA"]
    if isinstance(label, bool):
        return ["TRUE" if label else "FALSE"]
    if isinstance(label, int):
        return [str(label)]
    if isinstance(label, float):
        return [_character_double(label)]
    if isinstance(label, str):
        return [label]
    if isinstance(label, complex):
        return [_complex_character(label)]
    if isinstance(label, (bytes, bytearray)):
        if len(label) == 0:
            return []
        return [f"{byte:02x}" for byte in label]
    if isinstance(label, Vector):
        if len(label.data) == 0:
            return []
        return [_vector_item(item, label.mode) for item in label.data]
    raise ShinyError(
        f"cannot coerce type '{type(label).__name__}' to vector of type 'character'"
    )


def _factor_strings(value: WithClass) -> list[str]:
    inner = value.value
    if isinstance(inner, Vector):
        codes = inner.data
    elif isinstance(inner, int) and not isinstance(inner, bool):
        codes = [inner]
    else:
        codes = [inner]
    levels = list(getattr(value, "levels", ()))
    pieces = []
    for code in codes:
        if isinstance(code, Missing):
            pieces.append("NA")
        else:
            pieces.append(levels[int(code) - 1])
    return pieces


def _vector_item(item, mode: str) -> str:
    if isinstance(item, Missing):
        return "NA"
    if mode == "character":
        return item
    if mode == "logical":
        return "TRUE" if item else "FALSE"
    if mode == "integer":
        return str(item)
    if mode == "double":
        return _character_double(item)
    if mode == "complex":
        return _complex_character(item)
    if mode == "raw":
        return f"{item:02x}"
    raise ShinyError(
        f"cannot coerce type '{mode}' to vector of type 'character'"
    )


def _complex_character(value: complex) -> str:
    real = _character_double(value.real)
    imag = value.imag
    if imag == 0.0:
        return real + "+0i"
    if isinstance(imag, float) and math.isnan(imag):
        return real + "+NaNi"
    if imag < 0.0:
        return real + "-" + _character_double(-imag) + "i"
    return real + "+" + _character_double(imag) + "i"


def _character_double(value: float) -> str:
    """R ``as.character`` for one double, which ``paste`` uses."""

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
