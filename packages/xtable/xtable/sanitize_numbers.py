"""sanitize.numbers from xtable 1.8-8.

LaTeX-only styling for numeric strings: optional ``$-$`` negatives and
scientific notation as ``$m \\times 10^{e}$``.
"""

from __future__ import annotations

import re
from typing import Any

from xtable.sanitize import (
    NA,
    Strings,
    _character_double,
    _is_latex,
    is_na,
)

_EXPONENT = re.compile(
    r"^\$?(-?)\$?([0-9.]+)[eE]\$?(-?)\+?\$?0*(\d+)$"
)
_EXPONENT_REPL = r"$\1\2 \\times 10^{\3\4}$"


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


def _r_if_condition(value: object) -> bool:
    """R ``if (x)`` on a length-one value."""

    if isinstance(value, Strings):
        value = list(value)
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError("argument is of length zero")
        if len(value) > 1:
            raise ValueError("the condition has length > 1")
        value = value[0]
    if value is NA:
        raise ValueError("missing value where TRUE/FALSE needed")
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, float):
        if value != value:
            raise ValueError("missing value where TRUE/FALSE needed")
        return value != 0.0
    if isinstance(value, str):
        lower = value.lower()
        if lower in ("true", "t"):
            return True
        if lower in ("false", "f"):
            return False
        raise ValueError("argument is not interpretable as logical")
    raise ValueError("argument is not interpretable as logical")


def _as_text(item: object) -> str:
    if is_na(item):
        return "NA"
    if isinstance(item, bool):
        return "TRUE" if item else "FALSE"
    if isinstance(item, int) and not isinstance(item, bool):
        return str(item)
    if isinstance(item, float):
        if item != item:
            return "NaN"
        if item == float("inf"):
            return "Inf"
        if item == float("-inf"):
            return "-Inf"
        return _character_double(item)
    if isinstance(item, str):
        return item
    return str(item)


def _element_text(item: object) -> str:
    return item if isinstance(item, str) else _as_text(item)


def sanitize_numbers(
    text,
    type,
    math_style_negative: object = False,
    math_style_exponents: object = False,
):
    """Same as R ``sanitize.numbers`` for ``type``, negatives, and exponents."""

    if not _is_latex(type):
        return text

    values, names = _items(text)
    result: list[Any] = list(values)
    modified = False

    if _r_if_condition(math_style_negative):
        modified = True
        for i, item in enumerate(result):
            if is_na(item):
                continue
            result[i] = _element_text(item).replace("-", "$-$")

    if _r_if_condition(math_style_exponents):
        if isinstance(math_style_exponents, bool) and not math_style_exponents:
            pass
        elif (
            isinstance(math_style_exponents, bool)
            and math_style_exponents
            or math_style_exponents == "$$"
        ):
            modified = True
            for i, item in enumerate(result):
                if is_na(item):
                    continue
                result[i] = _EXPONENT.sub(
                    _EXPONENT_REPL, _element_text(item)
                )
        elif math_style_exponents == "ensuremath":
            modified = True
            for i, item in enumerate(result):
                if is_na(item):
                    continue
                result[i] = _EXPONENT.sub(
                    r"\\ensuremath{\1\2 \\times 10^{\3\4}}",
                    _element_text(item),
                )

    if not modified:
        if isinstance(text, str):
            return Strings([text], None)
        return text
    return Strings(result, names)
