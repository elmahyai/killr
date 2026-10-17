"""The operator %|%."""

from __future__ import annotations

import math
import struct

from rlang import RLangError

NA_REAL = struct.unpack("d", struct.pack("Q", 0x7FF00000000007A2))[0]


class Missing:
    """R's NA for logical, integer, and character vectors."""

    def __repr__(self) -> str:
        return "NA"


NA = Missing()


class _Vector:
    def __init__(self, values):
        self.values = list(values)

    def __len__(self) -> int:
        return len(self.values)


class Logical(_Vector):
    pass


class Integer(_Vector):
    pass


class Character(_Vector):
    pass


class Double(_Vector):
    pass


class Complex(_Vector):
    pass


_ATOMIC = (Logical, Integer, Character, Double, Complex)


def _is_na_double(value: float) -> bool:
    return math.isnan(value) and struct.unpack("Q", struct.pack("d", value))[0] == 0x7FF00000000007A2


def _atomic_kind(value):
    if isinstance(value, _ATOMIC):
        return type(value)
    if isinstance(value, bool):
        return Logical
    if isinstance(value, int) and not isinstance(value, bool):
        return Integer
    if isinstance(value, float):
        return Double
    if isinstance(value, str):
        return Character
    if isinstance(value, complex):
        return Complex
    return None


def _vectorize(value, kind):
    if isinstance(value, kind):
        return list(value.values)
    if kind is Logical and isinstance(value, bool):
        return [value]
    if kind is Integer and isinstance(value, int) and not isinstance(value, bool):
        return [value]
    if kind is Double and isinstance(value, float):
        return [value]
    if kind is Character and isinstance(value, str):
        return [value]
    if kind is Complex and isinstance(value, complex):
        return [value]
    raise RLangError(f"Cannot replace missing values in an object of type {type(value).__name__}")


def _type_label(kind) -> str:
    return {
        Logical: "logical",
        Integer: "integer",
        Character: "character",
        Double: "double",
        Complex: "complex",
    }[kind]


def _is_na(value, kind) -> bool:
    if kind is Logical:
        return value is NA
    if kind is Integer:
        return value is NA
    if kind is Character:
        return value is NA
    if kind is Double:
        return _is_na_double(value)
    if kind is Complex:
        return isinstance(value, complex) and _is_na_double(value.real)
    return False


def na_or(x, y):
    """Replace missing elements of an atomic vector."""
    kind = _atomic_kind(x)
    if kind is None:
        raise RLangError(f"Cannot replace missing values in an object of type {type(x).__name__}")

    repl_kind = _atomic_kind(y)
    if repl_kind is None:
        raise RLangError(
            f"Replacement values must have type {_type_label(kind)}, not type {type(y).__name__}"
        )
    if repl_kind is not kind:
        raise RLangError(
            f"Replacement values must have type {_type_label(kind)}, not type {_type_label(repl_kind)}"
        )

    values = _vectorize(x, kind)
    replacement = _vectorize(y, kind)
    n = len(values)
    n_replacement = len(replacement)

    if n_replacement != 1 and n_replacement != n:
        if n == 1:
            raise RLangError(
                f"The replacement values must have size 1, not {n_replacement}"
            )
        raise RLangError(
            f"The replacement values must have size 1 or {n}, not {n_replacement}"
        )

    first_na = None
    for index, value in enumerate(values):
        if _is_na(value, kind):
            first_na = index
            break

    if first_na is None:
        return x

    out = list(values)
    if n_replacement == 1:
        repl = replacement[0]
        for index in range(first_na, n):
            if _is_na(out[index], kind):
                out[index] = repl
    else:
        for index in range(first_na, n):
            if _is_na(out[index], kind):
                out[index] = replacement[index]

    return kind(out)
