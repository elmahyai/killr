"""Update check for nlme model structures (nlme ``needUpdate``)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

__all__ = ["Attributed", "needUpdate"]


@dataclass(frozen=True, slots=True)
class Attributed:
    """A value carrying R-style attributes, for the ``needUpdate`` attribute check."""

    value: Any
    attributes: dict[str, Any] = field(default_factory=dict)


# R class vectors for Python stand-ins that do not define ``classes``.
_CLASS_BY_TYPE: dict[str, tuple[str, ...]] = {
    "CorAR1": ("corAR1", "corStruct"),
    "ReStruct": ("reStruct",),
    "VarIdent": ("varIdent", "varFunc"),
    "VarComb": ("varComb", "varFunc"),
}


def needUpdate(object: Any) -> bool:
    """Return whether a model plug-in needs to be updated after an estimation cycle.

    Dispatch follows the R methods: ``modelStruct`` and ``varComb`` ask their
    components, ``corStruct``, ``reStruct``, and ``varIdent`` answer FALSE, and
    any other object reads its ``needUpdate`` attribute.
    """
    classes = _r_classes(object)
    if "varComb" in classes or "modelStruct" in classes:
        return any(needUpdate(item) for item in _components(object))
    if "corStruct" in classes or "reStruct" in classes or "varIdent" in classes:
        return False
    return _attribute_flag(object)


def _r_classes(object: Any) -> tuple[str, ...]:
    classes = getattr(object, "classes", None)
    if classes is not None:
        return tuple(classes)
    return _CLASS_BY_TYPE.get(type(object).__name__, ())


def _components(object: Any) -> list[Any]:
    components = getattr(object, "components", None)
    if isinstance(components, dict):
        return list(components.values())
    if isinstance(components, list):
        return list(components)
    if hasattr(object, "blocks"):
        return [element for _, element in object.blocks]
    return list(object)


def _attribute_flag(object: Any) -> bool:
    if not isinstance(object, Attributed):
        return False
    value = object.attributes.get("needUpdate")
    return value is not None and bool(value)
