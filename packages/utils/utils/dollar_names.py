"""``.DollarNames`` completion after ``$`` extractors (utils 4.5.0)."""

from __future__ import annotations

import re
from typing import Any

from utils.at_names import _find_matches, _completion_settings


class REnvironment:
    """Minimal R environment stand-in with optional hidden bindings."""

    def __init__(
        self,
        /,
        _hidden: dict[str, Any] | None = None,
        **public: Any,
    ) -> None:
        self._public = dict(public)
        self._hidden = dict(_hidden or {})

    def ls(self, *, all_names: bool = True, pattern: str = "") -> list[str]:
        names = list(self._public.keys())
        if all_names:
            names.extend(self._hidden.keys())
        if pattern:
            names = [name for name in names if re.search(pattern, name)]
        return names


def _is_atomic(x: object) -> bool:
    return isinstance(x, (bool, int, float, complex, str, bytes))


def _list_names(x: object) -> list[str]:
    if isinstance(x, dict):
        return [str(key) for key in x.keys()]
    if type(x) is list:
        return []
    names = getattr(x, "names", None)
    if callable(names):
        raw = names()
    else:
        raw = names
    if raw is None:
        return []
    if isinstance(raw, (list, tuple)):
        return [str(value) for value in raw if value is not None]
    return []


def _dollar_names_list(x: object, pattern: str = "") -> list[str]:
    return _find_matches(pattern, _list_names(x))


def _dollar_names_environment(x: REnvironment, pattern: str = "") -> list[str]:
    fuzzy = _completion_settings.get("fuzzy") is True
    if not fuzzy:
        return x.ls(all_names=True, pattern=pattern)
    return _find_matches(pattern, x.ls(all_names=True, pattern=""))


def _dollar_names_default(x: object, pattern: str = "") -> list[str]:
    if _is_atomic(x):
        return []
    return _find_matches(pattern, _list_names(x))


def DollarNames(x: object, pattern: str = "") -> list[str]:
    """Return names in ``x`` that match ``pattern`` for ``$`` completion."""
    if isinstance(x, REnvironment):
        return _dollar_names_environment(x, pattern)
    if isinstance(x, dict) or type(x) is list:
        return _dollar_names_list(x, pattern)
    return _dollar_names_default(x, pattern)
