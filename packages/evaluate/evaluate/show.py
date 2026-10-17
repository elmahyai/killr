"""R-style printing for values captured by evaluate."""

from __future__ import annotations

import math
import sys

from evaluate.types import NA, Vector


def as_list(value):
    if isinstance(value, Vector):
        return list(value.data)
    if isinstance(value, list):
        return list(value)
    return [value]


def is_atomic_vector(value) -> bool:
    return isinstance(value, Vector)


def format_atom(value, quote: bool = False) -> str:
    if value is None:
        return "NULL"
    if value is NA or isinstance(value, type(NA)):
        return "NA"
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return "NaN"
        if math.isinf(value):
            return "Inf" if value > 0 else "-Inf"
        if value == 0:
            return "0"
        if value.is_integer() and abs(value) < 1e15:
            return str(int(value))
        return repr(value)
    if isinstance(value, str):
        if quote:
            return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'
        return value
    return str(value)


def format_value(value) -> str:
    if isinstance(value, Vector):
        if len(value.data) == 0:
            return "numeric(0)"
        parts = [format_atom(item, quote=True) for item in value.data]
        return "[1] " + " ".join(parts)
    if isinstance(value, list):
        return format_value(Vector(value))
    if value is None:
        return "NULL"
    return "[1] " + format_atom(value, quote=True)


def _cat_one(arg, sep: str) -> str:
    if isinstance(arg, Vector):
        return sep.join(format_atom(item) for item in arg.data)
    return format_atom(arg)


def cat(*args, sep: str = " ", end: str = "", file=None):
    from evaluate.types import Invisible

    text = sep.join(_cat_one(arg, sep) for arg in args)
    if file is None:
        file = sys.stdout
    file.write(text + end)
    return Invisible(None)


def write_out(text: str) -> None:
    sys.stdout.write(text)


def r_print(value, **_ignored):
    from evaluate.types import Invisible

    text = format_value(value)
    if not text.endswith("\n"):
        text += "\n"
    write_out(text)
    return Invisible(value)
