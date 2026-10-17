"""Pillar options. These are the R options() entries pillar reads."""

from __future__ import annotations

from typing import Any

_options: dict[str, Any] = {}

_DEFAULTS: dict[str, Any] = {
    "pillar.bold": False,
    "pillar.subtle": True,
    "pillar.subtle_num": False,
    "pillar.neg": True,
    "pillar.sigfig": 3,
    "pillar.min_title_chars": 20,
    "pillar.min_chars": 3,
    "pillar.print_max": 20,
    "pillar.print_min": 10,
    "pillar.max_footer_lines": 7,
    "pillar.max_extra_cols": 100,
    "pillar.width": None,
    "width": 80,
    "OutDec": ".",
}


def get_option(name: str, default: Any = None) -> Any:
    if name in _options:
        return _options[name]
    if default is not None:
        return default
    return _DEFAULTS.get(name, default)


def set_option(name: str, value: Any) -> None:
    # options(name = NULL) removes the option. The getter then uses the default.
    if value is None:
        _options.pop(name, None)
    else:
        _options[name] = value


def options(**kwargs: Any) -> dict[str, Any]:
    """Set named options and return the previous values."""

    previous = {key: _options.get(key, _DEFAULTS.get(key)) for key in kwargs}
    for key, value in kwargs.items():
        set_option(key, value)
    return previous
