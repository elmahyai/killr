"""Standardise a dependency specification the way install.packages does."""

from __future__ import annotations

_HARD = ("Depends", "Imports", "LinkingTo")
_SOFT = ("Depends", "Imports", "LinkingTo", "Suggests")
_KNOWN = frozenset((*_SOFT, "Enhances"))
_DEPENDENCY_ERROR = "Dependencies must be a boolean or a character vector"


class _LogicalNA:
    """R's length-1 logical NA.

    ``identical(x, NA)`` matches this object. A numeric missing value does not.
    """

    def __repr__(self) -> str:
        return "NA"

    def __bool__(self) -> bool:
        raise ValueError("missing value where TRUE/FALSE needed")


NA = _LogicalNA()


def standardise_dep(x: object) -> list[str]:
    """Return the dependency names selected by ``x``.

    A length-1 logical NA selects Depends, Imports, and LinkingTo.
    Exact True adds Suggests. Exact False selects nothing.
    In a character vector, any ``hard`` selects those three names, otherwise
    any ``soft`` selects the four, otherwise the known names are kept in
    ``x``'s order.
    """

    logical = _logical_values(x)
    if logical is not None:
        if len(logical) == 1 and logical[0] is NA:
            return list(_HARD)
        if len(logical) == 1 and logical[0] is True:
            return list(_SOFT)
        if len(logical) == 1 and logical[0] is False:
            return []
        raise ValueError(_DEPENDENCY_ERROR)

    values = _character_values(x)
    if values is None:
        raise ValueError(_DEPENDENCY_ERROR)
    if _any_equal(values, "hard"):
        return list(_HARD)
    if _any_equal(values, "soft"):
        return list(_SOFT)
    return _intersect_known(values)


def _logical_values(x: object) -> list[object] | None:
    if x is True or x is False or x is NA:
        return [x]
    if isinstance(x, (list, tuple)) and len(x) > 0:
        if all(item is True or item is False or item is NA for item in x):
            return list(x)
    return None


def _character_values(x: object) -> list[object] | None:
    if isinstance(x, str):
        return [x]
    if not isinstance(x, (list, tuple)):
        return None
    values: list[object] = []
    for item in x:
        if isinstance(item, str):
            values.append(item)
        elif item is None or item is NA:
            values.append(None)
        else:
            return None
    return values


def _any_equal(values: list[object], target: str) -> bool:
    missing = False
    for value in values:
        if value is None:
            missing = True
        elif value == target:
            return True
    if missing:
        raise ValueError("missing value where TRUE/FALSE needed")
    return False


def _intersect_known(values: list[object]) -> list[str]:
    seen: set[str] = set()
    kept: list[str] = []
    for value in values:
        if isinstance(value, str) and value in _KNOWN and value not in seen:
            seen.add(value)
            kept.append(value)
    return kept
