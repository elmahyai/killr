"""with_locale and local_locale (R's locale.R): locale categories.

Each category is set with Python's locale.setlocale. Setting LC_COLLATE also
sets the LC_COLLATE variable, as R does, because R reads that variable first.
"""

from __future__ import annotations

import locale

from ._scope import current, force, private_scope
from .envvar import local_envvar

_CATEGORIES = (
    "LC_ALL",
    "LC_COLLATE",
    "LC_CTYPE",
    "LC_MONETARY",
    "LC_NUMERIC",
    "LC_TIME",
    "LC_MESSAGES",
    "LC_PAPER",
    "LC_NAME",
    "LC_ADDRESS",
    "LC_TELEPHONE",
    "LC_MEASUREMENT",
    "LC_IDENTIFICATION",
)


def _category(name: str) -> int:
    if name not in _CATEGORIES:
        raise ValueError(f"unknown locale category {name!r}")
    return getattr(locale, name)


def get_locale(cats) -> dict[str, str]:
    return {name: locale.setlocale(_category(name)) for name in cats}


def set_locale(cats) -> None:
    for name, value in cats.items():
        locale.setlocale(_category(name), value)


def _checked(cats: dict[str, str]) -> dict[str, str]:
    if "LC_ALL" in cats:
        raise ValueError("Setting LC_ALL category not implemented.")
    return {str(name): str(value) for name, value in cats.items()}


def local_locale(new=None, *, _local_envir=None, **kwargs):
    cats = dict(new or {})
    cats.update(kwargs)
    cats = _checked(cats)
    if "LC_COLLATE" in cats:
        local_envvar({"LC_COLLATE": cats["LC_COLLATE"]}, _local_envir=_local_envir)
    old = get_locale(cats)
    current(_local_envir).add(lambda: set_locale(old))
    set_locale(cats)
    return old


def with_locale(new, code):
    with private_scope() as frame:
        local_locale(new, _local_envir=frame)
        return force(code)
