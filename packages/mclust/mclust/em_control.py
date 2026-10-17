"""Control values for the EM algorithm.

A length-1 ``tol`` is repeated. A length-1 ``itmax`` is paired with
``.Machine$integer.max``, and only then is an infinite limit replaced by
that integer. ``itmax = Inf`` is therefore the integer limit twice.
"""

from __future__ import annotations

import math
import sys

__all__ = ["em_control"]

_MISSING = object()
_INT_MAX = 2147483647


def em_control(eps=_MISSING, tol=_MISSING, itmax=_MISSING, equal_pro=False):
    """Tolerances and iteration limits for EM.

    ``eps`` is the singularity tolerance. ``tol`` holds the relative
    tolerances for the log-likelihood and for the inner loop of models
    with an iterative M-step. ``itmax`` holds the matching iteration
    limits. ``equal_pro`` is whether the mixing proportions are equal.
    """
    if eps is _MISSING:
        eps = sys.float_info.epsilon
    if tol is _MISSING:
        tol = [1.0e-05, math.sqrt(sys.float_info.epsilon)]
    if itmax is _MISSING:
        itmax = [_INT_MAX, _INT_MAX]

    _reject_outside_unit(eps, "eps")
    _reject_outside_unit(tol, "tol")
    _reject_negative(itmax, "itmax")

    tol = _repeat_length_one(tol)
    itmax = _pad_itmax(itmax)
    itmax = _replace_infinite(itmax)
    return _Control(
        eps=_vector(eps),
        tol=_vector(tol),
        itmax=_vector(itmax),
        equalPro=equal_pro,
    )


class _Control(dict):
    """The named list ``emControl`` returns."""

    def __str__(self):
        lines = []
        for name in ("eps", "tol", "itmax", "equalPro"):
            lines.append("$" + name)
            lines.append("[1] " + _format_component(self[name]))
            lines.append("")
        return "\n".join(lines) + "\n"


def _reject_outside_unit(value, name):
    _reject_negative(value, name)
    flags = [_compare(item, 1) for item in _elements(value)]
    result = _any(flags)
    if result is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if result:
        raise ValueError(f"{name} is not less than 1")


def _reject_negative(value, name):
    flags = [_negative(item) for item in _elements(value)]
    result = _any(flags)
    if result is None:
        raise ValueError("missing value where TRUE/FALSE needed")
    if result:
        raise ValueError(f"{name} is negative")


def _elements(value):
    """Values ``any()`` and ``length()`` see. ``None`` is R's ``NULL``."""
    if value is None:
        return []
    if isinstance(value, str):
        raise TypeError("comparison of these types is not implemented")
    if isinstance(value, (bool, int, float)):
        return [value]
    return list(value)


def _negative(value):
    if _is_missing(value):
        return None
    return value < 0


def _compare(value, bound):
    """``value >= bound``. A missing comparison is ``None``, which is R's NA."""
    if _is_missing(value):
        return None
    return value >= bound


def _is_missing(value):
    return isinstance(value, float) and math.isnan(value)


def _any(flags):
    """R's ``any``: TRUE wins, otherwise NA if any comparison was missing."""
    saw_missing = False
    for flag in flags:
        if flag is True:
            return True
        if flag is None:
            saw_missing = True
    if saw_missing:
        return None
    return False


def _repeat_length_one(value):
    if value is None:
        return None
    elements = _elements(value)
    if len(elements) == 1:
        return [elements[0], elements[0]]
    return elements


def _pad_itmax(value):
    """A single limit sets the outer loop. The inner limit stays at the integer max."""
    if value is None:
        return None
    elements = _elements(value)
    if len(elements) != 1:
        return elements
    outer = elements[0]
    if isinstance(outer, bool):
        return [int(outer), _INT_MAX]
    if isinstance(outer, int):
        return [outer, _INT_MAX]
    return [float(outer), float(_INT_MAX)]


def _replace_infinite(value):
    if value is None:
        return None
    elements = list(value)
    infinite = [isinstance(item, float) and math.isinf(item) for item in elements]
    if not any(infinite):
        return elements
    replaced = []
    for item, is_infinite in zip(elements, infinite):
        if is_infinite or isinstance(item, bool):
            replaced.append(float(_INT_MAX if is_infinite else int(item)))
        else:
            replaced.append(float(item))
    return replaced


def _vector(value):
    if value is None:
        return None
    if isinstance(value, list):
        return value
    return _elements(value)


def _format_component(value):
    if value is None:
        return "NULL"
    if isinstance(value, (bool, int, float)):
        return _format_atom(value)
    if len(value) == 0:
        return ""
    return " ".join(_format_atom(item) for item in value)


def _format_atom(value):
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    if value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    absolute = abs(value)
    if absolute <= 1e-4 or absolute >= 1e6:
        return _scientific(value)
    return f"{value:.7g}"


def _scientific(value):
    text = f"{value:.6e}"
    mantissa, exponent = text.split("e")
    mantissa = mantissa.rstrip("0").rstrip(".")
    return f"{mantissa}e{exponent}"
