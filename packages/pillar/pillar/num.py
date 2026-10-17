"""Numeric vectors that remember how a tibble column should format them.

``num()`` requires a numeric vector, stores doubles, and sets class
``pillar_num``. ``set_num_opts()`` writes the same pillar attribute and keeps
the class it was given. The formatted attribute is what
``vec_ptype_full.pillar_num`` returns. The abbreviation is
``vec_ptype_abbr.pillar_num`` when that class is set, and the ordinary
abbreviation otherwise.

``format.pillar_num`` and ``pillar_shaft`` are left out. They need the numeric
shaft, which is still unassigned.
"""

from __future__ import annotations

import math
from typing import Any

from glue._text import r_character_double

_NOTATIONS = ("fit", "dec", "sci", "eng", "si")
_PILLAR_NUM_CLASS = ("pillar_num", "pillar_vctr", "vctrs_vctr", "double")
_INT_LIMIT = 4503599627370496  # 2^52, the largest magnitude rlang::is_integerish keeps
_BASE_ABBR = {
    "double": "dbl",
    "integer": "int",
    "logical": "lgl",
    "character": "chr",
}


def _is_bool(value: Any) -> bool:
    return isinstance(value, bool)


def _is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _atoms(value: Any) -> list[Any]:
    """One R vector. A string is one element, not a sequence of characters."""

    if isinstance(value, PillarNum):
        return list(value.data)
    if isinstance(value, (str, bytes)):
        return [value]
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _paste(value: Any) -> str:
    """paste0 of one atom. NULL is not pasted; NA is the letters NA."""

    if value is None:
        return "NA"
    if _is_bool(value):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return value
    if _is_int(value):
        return str(value)
    if isinstance(value, float):
        return r_character_double(value)
    return str(value)


def _is_integerish(value: Any) -> bool:
    """rlang::is_integerish of one atom. NA, NaN, and Inf count. A bool does not."""

    if value is None or _is_bool(value) or isinstance(value, str):
        return False
    if _is_int(value):
        return abs(value) <= _INT_LIMIT
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return True
        if abs(value) > _INT_LIMIT:
            return False
        return value == math.trunc(value)
    return False


def _check_digits(digits: Any) -> None:
    """stopifnot(is.null(digits) || is_integerish(digits))."""

    if digits is None:
        return
    items = list(digits) if isinstance(digits, (list, tuple)) else [digits]
    if items and all(_is_integerish(item) for item in items):
        return
    if not items:
        return
    raise ValueError("is.null(digits) || is_integerish(digits) is not TRUE")


def _require_numeric(value: Any) -> list[float | None]:
    """stopifnot(is.numeric(x)), then x[] <- as.numeric(x)."""

    if value is None:
        raise ValueError("is.numeric(x) is not TRUE")
    items = _atoms(value)
    out: list[float | None] = []
    for item in items:
        if item is None:
            out.append(None)
            continue
        if _is_bool(item) or not isinstance(item, (int, float)):
            raise ValueError("is.numeric(x) is not TRUE")
        out.append(float(item))
    return out


def _notation_choices(shown: str) -> str:
    listed = ", ".join(f'"{name}"' for name in _NOTATIONS[:-1])
    return f'`notation` must be one of {listed}, or "{_NOTATIONS[-1]}", not "{shown}".'


def _not_character(value: Any) -> str:
    if _is_bool(value):
        token = "TRUE" if value else "FALSE"
        return f"`notation` must be a character vector, not `{token}`."
    if isinstance(value, float) and math.isinf(value):
        token = "Inf" if value > 0 else "-Inf"
        return f"`notation` must be a character vector, not `{token}`."
    if isinstance(value, float) and math.isnan(value):
        return "`notation` must be a character vector, not `NaN`."
    if isinstance(value, (int, float)):
        return f"`notation` must be a character vector, not the number {_paste(value)}."
    if isinstance(value, (list, tuple)):
        return "`notation` must be a character vector, not a list."
    return f"`notation` must be a character vector, not a {type(value).__name__}."


def _match_notation(notation: Any) -> str | None:
    """rlang::arg_match. Omitted and NULL stay unset. A choice must be exact."""

    if notation is None:
        return None
    if isinstance(notation, str):
        values = [notation]
    elif isinstance(notation, (list, tuple)):
        if len(notation) == 0:
            raise ValueError("`notation` must be length 1, not length 0")
        if any(not isinstance(item, str) for item in notation):
            raise ValueError("`notation` must be a character vector, not a list.")
        values = list(notation)
    else:
        raise ValueError(_not_character(notation))
    if len(values) > 1 and set(values) != set(_NOTATIONS):
        raise ValueError(_notation_choices(values[0]))
    chosen = values[0]
    if chosen not in _NOTATIONS:
        raise ValueError(_notation_choices(chosen))
    return chosen


def _logical1(value: Any) -> bool | None:
    """Coerce one atom the way ``if`` and ``&&`` do. None means NA."""

    if isinstance(value, (list, tuple)):
        raise ValueError(f"'length = {len(value)}' in coercion to 'logical(1)'")
    if _is_bool(value):
        return value
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return value != 0
    raise ValueError("invalid 'x' type in 'x && y'")


def _fixed_exponent_conflicts(fixed_exponent: Any, notation: str) -> None:
    """``if (fixed_exponent && notation == "dec")``, including the installed spelling."""

    left = _logical1(fixed_exponent)
    if left is False:
        return
    right = notation == "dec"
    if left is True:
        if right:
            raise ValueError(
                'Incomatible arguments: `notation = "dec"` and `fixed_exponent` given'
            )
        return
    if right:
        raise ValueError("missing value where TRUE/FALSE needed")


def _coerce_number(value: Any) -> float:
    """The number ``if (digits >= 0)`` compares. NA raises the if() error."""

    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument is of length zero")
        raise ValueError("the condition has length > 1")
    if isinstance(value, str):
        try:
            value = float(value)
        except ValueError:
            raise ValueError("missing value where TRUE/FALSE needed") from None
    if _is_bool(value):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            raise ValueError("missing value where TRUE/FALSE needed")
        return float(value)
    raise ValueError("missing value where TRUE/FALSE needed")


def _negate(value: Any) -> Any:
    """Unary minus. A string is the installed error, not a coerced number."""

    if isinstance(value, str):
        raise ValueError("invalid argument to unary operator")
    if _is_bool(value):
        return -1 if value else 0
    if isinstance(value, (int, float)):
        return -value
    raise ValueError("invalid argument to unary operator")


def _format_attr(
    sigfig: Any,
    digits: Any,
    label: Any,
    scale: Any,
    notation: str | None,
    fixed_exponent: Any,
    extra_sigfig: Any,
) -> str:
    """format.pillar_num_attr. digits >= 0 keeps the bang."""

    if notation is None:
        class_ = "pillar_num"
    else:
        class_ = f"pillar_num({notation})"
    if digits is not None:
        if _coerce_number(digits) >= 0:
            out = f"{class_}:.{_paste(digits)}!"
        else:
            out = f"{class_}:.{_paste(_negate(digits))}"
    elif sigfig is not None:
        out = f"{class_}:{_paste(sigfig)}"
        if extra_sigfig is True:
            out = out + "*"
    elif extra_sigfig is True:
        out = class_ + "*"
    else:
        out = class_
    if label is not None:
        out = out + "{" + _paste(label) + "}"
    if scale is not None:
        out = out + "*" + _paste(scale)
    if fixed_exponent is not None:
        out = out + "|" + _paste(fixed_exponent)
    return out


def _abbr_pillar_num(sigfig: Any, digits: Any, notation: str | None) -> str:
    """vec_ptype_abbr.pillar_num. digits > 0 keeps the bang. Zero does not."""

    if notation is None:
        notation = "num"
    if digits is not None:
        if _coerce_number(digits) > 0:
            return f"{notation}:.{_paste(digits)}!"
        return f"{notation}:.{_paste(_negate(digits))}"
    if sigfig is not None:
        return f"{notation}:{_paste(sigfig)}"
    return notation


def _infer(data: list[Any]) -> tuple[tuple[str, ...], str]:
    """class() and typeof() of an atomic vector that has no class of its own."""

    if not data:
        return ("numeric",), "double"
    if all(isinstance(item, str) for item in data):
        return ("character",), "character"
    if any(_is_bool(item) for item in data) and all(item is None or _is_bool(item) for item in data):
        return ("logical",), "logical"
    if all(item is None or _is_int(item) for item in data):
        return ("integer",), "integer"
    if all(item is None or _is_int(item) or isinstance(item, float) for item in data):
        return ("numeric",), "double"
    return ("list",), "list"


class PillarNum:
    """A vector plus its pillar attribute.

    ``.data`` is the values. ``.pillar`` is the formatted attribute.
    ``.abbr`` is ``vec_ptype_abbr`` for this object's class.
    ``.classes`` is the R class vector. ``num()`` sets ``pillar_num``.
    ``set_num_opts()`` keeps whatever class the input already had.
    """

    def __init__(
        self,
        data: list[Any],
        classes: tuple[str, ...],
        typeof: str,
        sigfig: Any,
        digits: Any,
        label: Any,
        scale: Any,
        notation: str | None,
        fixed_exponent: Any,
        extra_sigfig: Any,
    ) -> None:
        self.data = data
        self.classes = classes
        self.typeof = typeof
        self.sigfig = sigfig
        self.digits = digits
        self.label = label
        self.scale = scale
        self.notation = notation
        self.fixed_exponent = fixed_exponent
        self.extra_sigfig = extra_sigfig

    @property
    def pillar(self) -> str:
        return _format_attr(
            self.sigfig,
            self.digits,
            self.label,
            self.scale,
            self.notation,
            self.fixed_exponent,
            self.extra_sigfig,
        )

    @property
    def abbr(self) -> str:
        if "pillar_num" in self.classes:
            return _abbr_pillar_num(self.sigfig, self.digits, self.notation)
        return _BASE_ABBR.get(self.typeof, self.typeof)

    def __repr__(self) -> str:
        return (
            f"PillarNum(data={self.data!r}, pillar={self.pillar!r}, "
            f"abbr={self.abbr!r}, classes={self.classes!r})"
        )


def set_num_opts(
    x: Any,
    sigfig: Any = None,
    digits: Any = None,
    label: Any = None,
    scale: Any = None,
    notation: Any = None,
    fixed_exponent: Any = None,
    extra_sigfig: Any = None,
) -> PillarNum:
    """Attach pillar numeric options and leave the data and class unchanged."""

    if x is None:
        raise ValueError("attempt to set an attribute on NULL")
    if isinstance(x, PillarNum):
        data = list(x.data)
        classes = x.classes
        typeof = x.typeof
    else:
        data = _atoms(x)
        classes, typeof = _infer(data)
    notation = _match_notation(notation)
    if fixed_exponent is not None and notation is not None:
        _fixed_exponent_conflicts(fixed_exponent, notation)
    if scale is not None and label is None:
        raise ValueError("Must set `label` if `scale` is provided.")
    if digits is not None and extra_sigfig is not None:
        raise ValueError("Incompatible arguments: `extra_sigfig` and `digits`.")
    return PillarNum(
        data,
        classes,
        typeof,
        sigfig,
        digits,
        label,
        scale,
        notation,
        fixed_exponent,
        extra_sigfig,
    )


def num(
    x: Any,
    sigfig: Any = None,
    digits: Any = None,
    label: Any = None,
    scale: Any = None,
    notation: Any = None,
    fixed_exponent: Any = None,
    extra_sigfig: Any = None,
) -> PillarNum:
    """Build a pillar_num vector. Integers become floats. A bool is not numeric."""

    data = _require_numeric(x)
    _check_digits(digits)
    out = set_num_opts(
        data,
        sigfig=sigfig,
        digits=digits,
        label=label,
        scale=scale,
        notation=notation,
        fixed_exponent=fixed_exponent,
        extra_sigfig=extra_sigfig,
    )
    out.classes = _PILLAR_NUM_CLASS
    out.typeof = "double"
    return out
