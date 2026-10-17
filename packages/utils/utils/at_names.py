"""``.AtNames`` completion for S4 ``@`` extractors (utils 4.5.0)."""

from __future__ import annotations

import re
from typing import Any

_completion_settings: dict[str, Any] = {"fuzzy": False, "backtick": False}


class S4:
    """Minimal S4 stand-in: slot names match ``methods::slotNames`` order."""

    __slot_names__: tuple[str, ...]

    def __init__(self, class_name: str, /, **slots: Any) -> None:
        self.__class_name__ = class_name
        self.__slot_names__ = tuple(slots.keys())
        for key, value in slots.items():
            setattr(self, key, value)


def is_s4(x: object) -> bool:
    return isinstance(x, S4)


def slot_names(x: S4) -> list[str]:
    return list(x.__slot_names__)


def _find_exact_matches(pattern: str, values: list[str]) -> list[str]:
    if not values:
        return []
    return [value for value in values if re.search(pattern, value)]


def _find_fuzzy_matches(pattern: str, values: list[str]) -> list[str]:
    exact = _find_exact_matches(pattern, values)
    if exact:
        return exact
    normalized_pattern = re.sub(r"(?<!^)(?<=.)(\\\.|_)(?!$)", "", pattern)
    normalized_pattern = re.sub(r"(\\\.|_)$", ".", normalized_pattern)
    normalized_values = [re.sub(r"(?<=.)[._]", "", value) for value in values]
    out: list[str] = []
    for index, normalized in enumerate(normalized_values):
        if re.search(normalized_pattern, normalized, re.IGNORECASE):
            out.append(values[index])
    return out


def _find_matches(
    pattern: str,
    values: list[str],
    fuzzy: bool | None = None,
    backtick: bool | None = None,
) -> list[str]:
    if fuzzy is None:
        fuzzy = _completion_settings.get("fuzzy") is True
    if backtick is None:
        backtick = _completion_settings.get("backtick") is True
    comps = _find_fuzzy_matches(pattern, values) if fuzzy else _find_exact_matches(pattern, values)
    if backtick and comps and all(comps):
        raise NotImplementedError("backtick completion needs deparse1")
    return comps


def AtNames(x: object, pattern: str = "") -> list[str]:
    """Default ``.AtNames`` method: slot names for S4 objects, else empty."""
    if is_s4(x):
        return _find_matches(pattern, slot_names(x))
    return []
