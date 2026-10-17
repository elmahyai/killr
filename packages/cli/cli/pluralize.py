"""Pluralization helpers and pluralize()."""

from __future__ import annotations

import inspect
import math
from typing import Any

from cli.collapse import ansi_collapse
from glue import glue, identity_transformer
from glue._text import NA


class CliNo:
    """A number that prints as 'no' when it is zero."""

    def __init__(self, value: float):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError("no() expects one number")
        if isinstance(value, float) and math.isnan(value):
            raise ValueError("no() does not accept a missing value")
        self.value = value

    def __int__(self) -> int:
        return int(self.value)

    def __float__(self) -> float:
        return float(self.value)


class CliQty:
    """A quantity that is used for pluralization and prints as empty."""

    def __init__(self, value):
        self.value = value


def _finite_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def make_quantity(obj) -> Any:
    if isinstance(obj, CliNo):
        obj = obj.value
    if isinstance(obj, CliQty):
        obj = obj.value
    if isinstance(obj, bool):
        return 1
    if isinstance(obj, (int, float)):
        if _finite_number(obj):
            return int(obj)
        return obj
    if isinstance(obj, str):
        return 1
    if obj is None:
        return 0
    return len(obj)


def no(expr) -> CliNo:
    """Print zero as the word no. The value is still the quantity."""

    return CliNo(expr)


def qty(expr) -> CliQty:
    """Set the plural quantity without printing the value."""

    return CliQty(make_quantity(expr))


def _as_piece(value) -> str:
    if isinstance(value, CliNo):
        if make_quantity(value) == 0:
            return "no"
        return str(int(value.value)) if float(value.value) == int(value.value) else str(value.value)
    if isinstance(value, CliQty):
        return ""
    if value is None or value is NA:
        return "NA"
    if isinstance(value, str):
        return value
    return str(value)


def inline_collapse(value, style: dict | None = None) -> str:
    style = style or {}
    last = style.get("vec-last", style.get("vec_last", ", and "))
    sep = style.get("vec-sep", style.get("vec_sep", ", "))
    sep2 = style.get("vec-sep2", style.get("vec_sep2", last[1:] if str(last).startswith(",") else last))
    trunc = style.get("vec-trunc", style.get("vec_trunc", 20))
    if isinstance(value, (CliNo, CliQty, str)) or isinstance(value, (int, float)) or value is None:
        pieces = [_as_piece(value)]
    elif isinstance(value, (list, tuple)):
        pieces = [_as_piece(item) for item in value]
    else:
        pieces = [_as_piece(value)]
    collapsed = ansi_collapse(pieces, sep=sep, sep2=sep2, last=last, trunc=trunc)
    return "" if collapsed is None else collapsed


def _process_plural(quantity, code: str) -> str:
    body = code[1:]
    parts = body.split("/")
    qty_value = make_quantity(quantity)
    finite_one = _finite_number(qty_value) and qty_value == 1
    finite_zero = _finite_number(qty_value) and qty_value == 0
    if len(parts) == 1:
        return "" if finite_one else parts[0]
    if len(parts) == 2:
        return parts[0] if finite_one else parts[1]
    if len(parts) == 3:
        if finite_zero:
            return parts[0]
        if finite_one:
            return parts[1]
        return parts[2]
    raise ValueError(f"Invalid pluralization directive: `{code}`")


_ids = 0


def _random_id() -> str:
    global _ids
    _ids += 1
    return f"FCkNXbE-{_ids}"


def pluralize(*parts, envir: dict | None = None, transformer=None):
    """Glue a string, with ``{?}`` plural markers and vector collapse."""

    if envir is None:
        frame = inspect.currentframe()
        caller = frame.f_back if frame is not None else None
        envir = {}
        if caller is not None:
            envir.update({key: value for key, value in caller.f_globals.items() if not key.startswith("__")})
            envir.update(caller.f_locals)
    else:
        envir = dict(envir)
    envir.setdefault("no", no)
    envir.setdefault("qty", qty)

    empty = object()
    state = {"qty": empty, "num_subst": 0, "postprocess": False, "pmarkers": {}}
    base = identity_transformer if transformer is None else transformer

    def transform(text: str, scope: dict):
        if text[:1] == "?":
            if state["qty"] is empty:
                state["postprocess"] = True
                marker = _random_id()
                state["pmarkers"][marker] = text
                return marker
            return _process_plural(state["qty"], text)
        state["num_subst"] += 1
        evaluated = base(text, scope)
        state["qty"] = evaluated
        return inline_collapse(evaluated)

    raw = glue(*parts, envir=envir, transformer=transform, comment="")
    text = raw.values[0] if len(raw.values) == 1 else str(raw)
    if not state["postprocess"]:
        return text
    if state["num_subst"] == 0:
        raise ValueError("Cannot pluralize without a quantity")
    if state["num_subst"] != 1:
        raise ValueError("Multiple quantities for pluralization")
    for marker, code in state["pmarkers"].items():
        text = text.replace(marker, _process_plural(state["qty"], code), 1)
    return text
