"""The operator %@%."""

from __future__ import annotations

from typing import Any


class S4:
    """Minimal stand-in for an S4 object with named slots."""

    __slots__ = ("_class", "slots")

    def __init__(self, _class: str, **slots: Any):
        self._class = _class
        self.slots = dict(slots)


class WithAttrs:
    """Object with R-style attributes in ``attrs``."""

    __slots__ = ("data", "attrs")

    def __init__(self, data=None, attrs=None):
        self.data = data
        self.attrs = {} if attrs is None else dict(attrs)


def _name_string(name) -> str:
    if isinstance(name, str):
        return name
    return str(name)


def _is_s4(x) -> bool:
    return isinstance(x, S4)


def slot(x, name):
    """Extract an attribute (``exact = TRUE``) or an S4 slot."""
    key = _name_string(name)
    if _is_s4(x):
        if key not in x.slots:
            return None
        return x.slots[key]
    if isinstance(x, WithAttrs):
        return x.attrs.get(key)
    attrs = getattr(x, "attrs", None)
    if isinstance(attrs, dict):
        return attrs.get(key)
    return None


def slot_replace(x, name, value):
    """Replace an attribute (``exact = TRUE``) or an S4 slot; return ``x``."""
    key = _name_string(name)
    if _is_s4(x):
        x.slots[key] = value
        return x
    if isinstance(x, WithAttrs):
        if value is None:
            x.attrs.pop(key, None)
        else:
            x.attrs[key] = value
        return x
    attrs = getattr(x, "attrs", None)
    if isinstance(attrs, dict):
        if value is None:
            attrs.pop(key, None)
        else:
            attrs[key] = value
        return x
    if value is None:
        return x
    if not hasattr(x, "attrs") or not isinstance(x.attrs, dict):
        x.attrs = {}
    x.attrs[key] = value
    return x
