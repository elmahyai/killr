"""with_options and local_options (R's options.R), over an in-process table.

The table starts with R's defaults for the options listed here. Other options
are unset until they are set, the same as R's getOption() for a name it does
not know.
"""

from __future__ import annotations

from .factory import local_, with_

_OPTIONS: dict[str, object] = {"digits": 7, "OutDec": ".", "scipen": 0, "warn": 0, "width": 80}


def get_option(name: str, default=None):
    """getOption(name): the current value, or ``default`` when unset."""
    return _OPTIONS.get(name, default)


def get_options(new_options, **_):
    return {name: _OPTIONS.get(name) for name in dict(new_options or {})}


def set_options(new_options):
    """options(...): set the values (None removes an option). Returns the old values."""
    new_options = dict(new_options or {})
    old = get_options(new_options)
    for name, value in new_options.items():
        if value is None:
            _OPTIONS.pop(name, None)
        else:
            _OPTIONS[name] = value
    return old


def reset_options(old_options):
    set_options(old_options)


with_options = with_(set_options, reset_options)
local_options = local_(set_options, reset_options, get_options, dots=True)
