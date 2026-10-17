"""R options() for the crayon and cli settings this translation reads."""

from __future__ import annotations

from typing import Any

_options: dict[str, Any] = {}


def get_option(name: str, default: Any = None) -> Any:
    if name in _options:
        return _options[name]
    return default


def set_option(name: str, value: Any) -> None:
    if value is None:
        _options.pop(name, None)
    else:
        _options[name] = value


def options(**kwargs: Any) -> dict[str, Any]:
    """Set named options. A value of None removes that option.

    Names keep the R spelling, for example ``crayon.enabled``.
    """

    previous = {key: _options.get(key) for key in kwargs}
    for key, value in kwargs.items():
        set_option(key, value)
    return previous
