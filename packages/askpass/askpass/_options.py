"""R options() for the askpass callback and the rlib interactive flag."""

from __future__ import annotations

from typing import Any

_options: dict[str, Any] = {}


def get_option(name: str, default: Any = None) -> Any:
    if name in _options:
        return _options[name]
    return default


def set_option(name: str, value: Any) -> None:
    """Set one option. None removes it, matching options(name = NULL)."""
    if value is None:
        _options.pop(name, None)
    else:
        _options[name] = value
