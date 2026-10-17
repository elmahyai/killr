"""Hash an arbitrary object with XXH128 (``hash``)."""

from __future__ import annotations

import math
import struct
import types
from typing import Any, Iterator

from rlang import Env, Named, RLangError
from rlang.as_label import Call, MissingArg, function_sym
from rlang.as_string import Symbol
from rlang.na_or import (
    NA,
    NA_REAL,
    Character,
    Complex,
    Double,
    Integer,
    Logical,
    _Vector,
    _is_na_double,
)
from rlang.slot import S4, WithAttrs

from rlang._xxh3 import xxh3_128

R_TYPE_null = 0
R_TYPE_symbol = 1
R_TYPE_pairlist = 2
R_TYPE_closure = 3
R_TYPE_environment = 4
R_TYPE_call = 6
R_TYPE_special = 7
R_TYPE_builtin = 8
R_TYPE_logical = 10
R_TYPE_integer = 13
R_TYPE_double = 14
R_TYPE_complex = 15
R_TYPE_character = 16
R_TYPE_list = 19
R_TYPE_expression = 20
R_TYPE_pointer = 22
R_TYPE_raw = 24
R_TYPE_s4 = 25

NA_INTEGER = -2147483648

_SRCREF_TAGS = frozenset({"srcref", "srcfile", "wholeSrcref"})


class _Hasher:
    __slots__ = ("_buf",)

    def __init__(self) -> None:
        self._buf = bytearray()

    def feed(self, data: bytes) -> None:
        self._buf.extend(data)

    def feed_int(self, value: int) -> None:
        self.feed(struct.pack("<i", int(value)))

    def feed_ssize(self, value: int) -> None:
        self.feed(struct.pack("<q", int(value)))

    def feed_ptr(self, value: object) -> None:
        self.feed(struct.pack("P", id(value)))

    def value(self) -> str:
        high, low = xxh3_128(bytes(self._buf), 0)
        return f"{high:016x}{low:016x}"


def _normalize_double(value: float) -> float:
    if _is_na_double(value):
        return NA_REAL
    if math.isnan(value):
        return float("nan")
    if value == 0.0:
        return 0.0
    return value


def _is_srcref_tag(tag: Any) -> bool:
    if isinstance(tag, Symbol):
        return tag._name in _SRCREF_TAGS
    if isinstance(tag, str):
        return tag in _SRCREF_TAGS
    return False


def _as_symbol(tag: Any) -> Any:
    if isinstance(tag, Symbol):
        return tag
    if isinstance(tag, str):
        return Symbol(tag)
    return tag


def _type_info(x: Any) -> tuple[int, bool]:
    if x is None:
        return R_TYPE_null, False
    if isinstance(x, Symbol) or x is MissingArg:
        return R_TYPE_symbol, False
    if isinstance(x, S4) and not isinstance(x, _Vector):
        return R_TYPE_s4, True
    if isinstance(x, Logical):
        return R_TYPE_logical, isinstance(x, S4)
    if isinstance(x, Integer):
        return R_TYPE_integer, isinstance(x, S4)
    if isinstance(x, Double):
        return R_TYPE_double, isinstance(x, S4)
    if isinstance(x, Complex):
        return R_TYPE_complex, isinstance(x, S4)
    if isinstance(x, Character):
        return R_TYPE_character, isinstance(x, S4)
    if isinstance(x, bool):
        return R_TYPE_logical, False
    if isinstance(x, int) and not isinstance(x, bool):
        return R_TYPE_integer, False
    if isinstance(x, float):
        return R_TYPE_double, False
    if isinstance(x, str):
        return R_TYPE_character, False
    if isinstance(x, complex):
        return R_TYPE_complex, False
    if isinstance(x, (bytes, bytearray)):
        return R_TYPE_raw, False
    if isinstance(x, Call):
        return R_TYPE_call, False
    if isinstance(x, types.FunctionType):
        return R_TYPE_closure, False
    if isinstance(x, Env):
        return R_TYPE_environment, False
    if isinstance(x, list) and not isinstance(x, Named):
        return R_TYPE_list, False
    if isinstance(x, Named):
        return R_TYPE_list, False
    if isinstance(x, WithAttrs):
        inner = x.data
        if inner is None:
            return R_TYPE_null, False
        return _type_info(inner)
    raise RLangError(f"Type `{type(x).__name__}` can't be hashed.")


def _unwrap(x: Any) -> Any:
    if isinstance(x, WithAttrs):
        return x.data
    return x


def _vector_values(x: Any) -> list[Any]:
    x = _unwrap(x)
    if isinstance(x, _Vector):
        return list(x.values)
    if isinstance(x, bool):
        return [x]
    if isinstance(x, int):
        return [x]
    if isinstance(x, float):
        return [x]
    if isinstance(x, str):
        return [x]
    if isinstance(x, complex):
        return [x]
    if isinstance(x, Named):
        return list(x)
    if isinstance(x, (bytes, bytearray)):
        return [bytes(x)]
    if isinstance(x, list):
        return list(x)
    raise RLangError(f"Type `{type(x).__name__}` can't be hashed.")


def _logical_bits(values: list[Any]) -> bytes:
    out = bytearray()
    for item in values:
        if item is NA:
            out.extend(struct.pack("<i", NA_INTEGER))
        else:
            out.extend(struct.pack("<i", 1 if item else 0))
    return bytes(out)


def _integer_bits(values: list[Any]) -> bytes:
    out = bytearray()
    for item in values:
        if item is NA:
            out.extend(struct.pack("<i", NA_INTEGER))
        else:
            out.extend(struct.pack("<i", int(item)))
    return bytes(out)


def _double_bits(values: list[Any]) -> bytes:
    out = bytearray()
    for item in values:
        out.extend(struct.pack("<d", _normalize_double(float(item))))
    return bytes(out)


def _complex_bits(values: list[Any]) -> bytes:
    out = bytearray()
    for item in values:
        if isinstance(item, complex):
            re, im = item.real, item.imag
        else:
            re, im = 0.0, 0.0
        out.extend(struct.pack("<d", _normalize_double(re)))
        out.extend(struct.pack("<d", _normalize_double(im)))
    return bytes(out)


def _character_element(hasher: _Hasher, item: Any) -> None:
    if item is NA:
        hasher.feed_int(1)
        return
    hasher.feed_int(0)
    text = str(item)
    encoded = text.encode("utf-8")
    hasher.feed_int(1)  # CE_UTF8
    hasher.feed_int(len(encoded))
    hasher.feed(encoded)


def _feed_vector_data(hasher: _Hasher, rtype: int, values: list[Any]) -> None:
    if rtype in (R_TYPE_logical, R_TYPE_integer):
        hasher.feed(_logical_bits(values) if rtype == R_TYPE_logical else _integer_bits(values))
        return
    if rtype == R_TYPE_double:
        hasher.feed(_double_bits(values))
        return
    if rtype == R_TYPE_complex:
        hasher.feed(_complex_bits(values))
        return
    if rtype == R_TYPE_raw:
        if len(values) == 1 and isinstance(values[0], (bytes, bytearray)):
            hasher.feed(bytes(values[0]))
        else:
            hasher.feed(b"".join(bytes(v) for v in values))
        return
    if rtype == R_TYPE_character:
        for item in values:
            _character_element(hasher, item)
        return
    if rtype == R_TYPE_list:
        for item in values:
            _hash_object(hasher, item, True)
        return
    if rtype == R_TYPE_expression:
        for item in values:
            _hash_object(hasher, item, True)
        return
    raise RLangError(f"Type `{rtype}` can't be hashed.")


def _iter_attribs(x: Any) -> Iterator[tuple[Any, Any]]:
    if isinstance(x, S4):
        for key, value in x.slots.items():
            yield Symbol(key), value
        return
    if isinstance(x, WithAttrs):
        for key, value in x.attrs.items():
            yield _as_symbol(key), value
        return
    if isinstance(x, Named):
        yield Symbol("names"), Character(x.names)
    attrs = getattr(x, "attrs", None)
    if isinstance(attrs, dict):
        for key, value in attrs.items():
            yield _as_symbol(key), value


def _hash_attribs(hasher: _Hasher, x: Any, zap_srcref: bool) -> None:
    for tag, value in _iter_attribs(x):
        if zap_srcref and _is_srcref_tag(tag):
            continue
        _hash_object(hasher, tag, zap_srcref)
        _hash_object(hasher, value, zap_srcref)


def _hash_closure(hasher: _Hasher, fn: types.FunctionType, zap_srcref: bool) -> None:
    env = getattr(fn, "__rlang_env__", fn.__globals__)
    formals = getattr(fn, "__rlang_formals__", None)
    body = getattr(fn, "__rlang_body__", None)
    if formals is None:
        import inspect

        try:
            sig = inspect.signature(fn)
            formals = Call(
                *(
                    Symbol(name)
                    for name in sig.parameters
                )
            )
        except (TypeError, ValueError):
            formals = Call()
    if body is None:
        body = getattr(fn, "__rlang_expr__", None)
    _hash_object(hasher, formals, zap_srcref)
    _hash_object(hasher, body, zap_srcref)
    hasher.feed_ptr(env)


def _hash_object(hasher: _Hasher, x: Any, zap_srcref: bool) -> None:
    rtype, is_s4 = _type_info(x)
    hasher.feed_int(rtype)
    hasher.feed_int(1 if is_s4 else 0)

    if rtype == R_TYPE_null:
        pass
    elif rtype == R_TYPE_symbol:
        sym = x
        if sym is MissingArg:
            name = ""
        else:
            name = sym._name
        hasher.feed_int(len(name))
        hasher.feed(name.encode("utf-8"))
    elif rtype in (
        R_TYPE_logical,
        R_TYPE_integer,
        R_TYPE_double,
        R_TYPE_complex,
        R_TYPE_raw,
        R_TYPE_character,
        R_TYPE_list,
        R_TYPE_expression,
    ):
        values = _vector_values(x)
        hasher.feed_ssize(len(values))
        _feed_vector_data(hasher, rtype, values)
    elif rtype == R_TYPE_call:
        parts = x._parts
        n = len(parts)
        if zap_srcref and n > 3 and parts[0] is function_sym:
            n = 3
        hasher.feed_ssize(n)
        for index in range(n):
            _hash_object(hasher, None, zap_srcref)
            _hash_object(hasher, parts[index], zap_srcref)
    elif rtype == R_TYPE_closure:
        _hash_closure(hasher, x, zap_srcref)
    elif rtype in (R_TYPE_environment, R_TYPE_pointer, R_TYPE_builtin, R_TYPE_special):
        hasher.feed_ptr(x)
    elif rtype == R_TYPE_s4:
        pass
    else:
        raise RLangError(f"Type `{rtype}` can't be hashed.")

    _hash_attribs(hasher, x, zap_srcref)


def hash(x: Any, zap_srcref: bool = True) -> str:
    """Return a 128-bit XXHash digest of ``x`` as a 32-character hex string."""
    hasher = _Hasher()
    _hash_object(hasher, x, bool(zap_srcref))
    return hasher.value()
