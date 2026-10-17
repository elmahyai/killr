"""Duplicate an R object (``duplicate``)."""

from __future__ import annotations

import types
from typing import Any

from rlang import Env, Named, RLangError
from rlang.as_box import Box
from rlang.as_label import Call, MissingArg, Quosure
from rlang.as_string import Symbol
from rlang.na_or import _Vector
from rlang.slot import S4, WithAttrs


def _uncopyable(x: Any) -> bool:
    return isinstance(x, (Symbol, MissingArg, Env, Quosure, Box, types.FunctionType))


def _vector_attrs(x: Any) -> dict[str, Any] | None:
    attrs = getattr(x, "attrs", None)
    if isinstance(attrs, dict) and attrs:
        return attrs
    return None


def _copy_vector(x: _Vector) -> _Vector:
    return type(x)(list(x.values))


def _duplicate(x: Any, shallow: bool) -> Any:
    if x is None or _uncopyable(x):
        return x

    if isinstance(x, WithAttrs):
        if shallow:
            return WithAttrs(x.data, x.attrs)
        return WithAttrs(_duplicate(x.data, False), {key: _duplicate(value, False) for key, value in x.attrs.items()})

    attrs = _vector_attrs(x)
    if isinstance(x, _Vector):
        out = _copy_vector(x)
        if attrs is not None:
            out.attrs = attrs if shallow else {key: _duplicate(value, False) for key, value in attrs.items()}
        return out

    if isinstance(x, (bytes, bytearray)):
        return bytes(x)

    if isinstance(x, Call):
        if shallow:
            return Call(*x._parts)
        return Call(*(_duplicate(part, False) for part in x._parts))

    if isinstance(x, Named):
        if shallow:
            return Named(list(x), x.names)
        return Named([_duplicate(item, False) for item in x], list(x.names))

    if isinstance(x, list):
        if shallow:
            return list(x)
        return [_duplicate(item, False) for item in x]

    if isinstance(x, S4):
        if shallow:
            return S4(x._class, **x.slots)
        return S4(x._class, **{key: _duplicate(value, False) for key, value in x.slots.items()})

    if isinstance(x, (bool, int, float, str, complex)):
        return x

    raise RLangError(f"Type `{type(x).__name__}` can't be duplicated.")


def duplicate(x: Any, shallow: bool = False) -> Any:
    """Return a deep or shallow copy of ``x``, mirroring ``Rf_duplicate`` / ``Rf_shallow_duplicate``."""
    return _duplicate(x, bool(shallow))
