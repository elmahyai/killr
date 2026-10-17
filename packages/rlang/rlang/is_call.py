"""Test whether an object is an R language call."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from rlang import abort
from rlang.as_label import Call, Symbol

def _is_colon2(value: object) -> bool:
    return isinstance(value, Symbol) and value._name == "::"


def _call_is_namespaced(x: Call, ns: str | None) -> bool:
    head = x[1]
    if not isinstance(head, Call):
        return False
    if not _is_colon2(head[1]):
        return False
    if ns is not None:
        pkg = head[2]
        if not isinstance(pkg, Symbol) or pkg._name != ns:
            return False
    return True


def _call_unnamespace(x: Call) -> Call:
    if not _call_is_namespaced(x, None):
        return x
    inner = x[1]
    fn = inner[3]
    return Call(fn, *x._parts[1:])


def _symbol_name(value: Symbol) -> str:
    return value._name


def _name_items(name: Any) -> tuple[Any, ...]:
    if isinstance(name, (list, tuple)):
        return tuple(name)
    return (name,)


def _match_name(fn: Any, name: Any) -> bool:
    if not isinstance(fn, Symbol):
        return False

    if isinstance(name, Symbol):
        return fn._name == name._name

    if isinstance(name, (list, tuple)):
        if name and all(isinstance(item, Symbol) for item in name):
            return any(fn._name == item._name for item in name)
        if all(isinstance(item, str) for item in name):
            fn_name = _symbol_name(fn)
            return fn_name in name
        abort("`name` must be a character vector of names.")

    if isinstance(name, str):
        return _symbol_name(fn) == name

    if isinstance(name, Sequence) and not isinstance(name, (str, bytes)):
        items = list(name)
        if items and all(isinstance(item, str) for item in items):
            return _symbol_name(fn) in items

    abort("`name` must be a character vector of names.")


def _match_ns(x: Call, ns: Sequence[str] | str) -> bool:
    if isinstance(ns, str):
        namespaces = (ns,)
    else:
        namespaces = tuple(ns)
    if not namespaces:
        abort("`ns` must be a character vector of namespaces.")
    if not all(isinstance(item, str) for item in namespaces):
        abort("`ns` must be a character vector of namespaces.")

    for item in namespaces:
        if item == "":
            if not _call_is_namespaced(x, None):
                return True
        elif _call_is_namespaced(x, item):
            return True
    return False


def is_call(
    x: object,
    name: str | Symbol | Sequence[str | Symbol] | None = None,
    n: int | None = None,
    ns: Sequence[str] | str | None = None,
) -> bool:
    if not isinstance(x, Call):
        return False

    if ns is not None:
        if not _match_ns(x, ns):
            return False

    x = _call_unnamespace(x)

    if name is not None:
        fn = x[1]
        if not _match_name(fn, name):
            return False

    if n is not None:
        if len(x) - 1 != n:
            return False

    return True
