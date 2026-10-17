"""Read one interactive reply and accept it only when it meets the checks.

Translated from coda 0.19-4.1 ``read.and.check`` in ``R/util.R``.
A blank line returns ``default`` when that argument was supplied.
"""

from __future__ import annotations

import math
import sys

import numpy as np

_MISSING = object()


def read_and_check(
    message="",
    what=0.0,
    lower=_MISSING,
    upper=_MISSING,
    answer_in=_MISSING,
    default=_MISSING,
):
    """Prompt until the reply has the requested mode and lies in range.

    ``what`` is numeric unless it is a string. ``lower`` and ``upper`` apply
    only to numeric replies. ``answer_in`` lists the only accepted values.
    """
    mode = _mode(what)
    have_lower = lower is not _MISSING
    have_upper = upper is not _MISSING
    have_answer = answer_in is not _MISSING
    have_default = default is not _MISSING
    if have_lower or have_upper:
        if mode != "numeric":
            raise ValueError("Can't have upper or lower limits with non numeric input")
        if have_lower and not _is_numeric_value(lower):
            raise ValueError("lower limit not numeric")
        if have_upper and not _is_numeric_value(upper):
            raise ValueError("upper limit not numeric")
        if have_lower and have_upper and upper < lower:
            raise ValueError("lower limit greater than upper limit")
    accepted = None
    if have_answer:
        raw = list(answer_in)
        if any(_mode(item) != mode for item in raw):
            raise ValueError("inconsistent values of what and answer.in")
        accepted = [_coerce(item, mode) for item in raw]
        if have_lower:
            accepted = [item for item in accepted if item >= lower]
        if have_upper:
            accepted = [item for item in accepted if item <= upper]
        if len(accepted) == 0:
            raise ValueError("No possible response matches conditions")
    if have_default:
        if _mode(default) != mode:
            raise ValueError("inconsistent values of what and default")
        if have_lower and default < lower:
            raise ValueError("default value below lower limit")
        if have_upper and default > upper:
            raise ValueError("default value above upper limit")
        if have_answer and not any(item == default for item in accepted):
            raise ValueError("default value does not satisfy conditions")

    err = True
    while err:
        if len(message) > 0:
            sys.stdout.write(f"\n{message}\n")
            if have_default:
                sys.stdout.write(f"(Default = {_cat(default)})\n")
        while True:
            sys.stdout.write("1:")
            sys.stdout.flush()
            ans = _readline()
            if isinstance(ans, str) and len(ans) > 0:
                break
            if have_default:
                ans = default
                break
        err1 = False
        if mode == "numeric":
            err1 = True
            ans = _as_numeric(ans)
            message = "You must enter a number"
            if isinstance(ans, float) and math.isnan(ans):
                pass
            elif have_lower and have_upper and (ans < lower or ans > upper):
                message = f"You must enter a number between {_cat(lower)} and {_cat(upper)}"
            elif have_lower and ans < lower:
                message = f"You must enter a number >= {_cat(lower)}"
            elif have_upper and ans > upper:
                message = f"You must enter a number <= {_cat(upper)}"
            else:
                err1 = False
        err2 = False
        if have_answer:
            missing = isinstance(ans, float) and math.isnan(ans)
            if not missing and not any(item == ans for item in accepted):
                shown = ",".join(_cat(item) for item in accepted)
                message = f"You must enter one of the following: {shown}"
                err2 = True
        err = err1 or err2
    return ans


def _readline():
    try:
        return input()
    except EOFError:
        return ""


def _mode(value):
    if isinstance(value, str):
        return "character"
    if _is_numeric_value(value):
        return "numeric"
    raise ValueError("inconsistent values of what and answer.in")


def _is_numeric_value(value):
    return isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(value, bool)


def _coerce(value, mode):
    if mode == "numeric":
        return _as_numeric(value)
    return str(value)


def _as_numeric(value):
    if _is_numeric_value(value):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return float("nan")


def _cat(value):
    if isinstance(value, str):
        return value
    number = float(value)
    if math.isfinite(number) and number.is_integer():
        return str(int(number))
    return str(number)
