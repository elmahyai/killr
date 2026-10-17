"""Scoped process-local analogue of withr's namespace helpers.

R exposes a mutable search path.  Python has no interpreter-wide equivalent,
so this module provides one for code that needs the same scoped lookup
semantics.  ``search()`` and ``lookup()`` are intentionally small and
deterministic; all mutating helpers restore their prior state on exit.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


_SEARCH_PATH: list[tuple[str, object]] = [
    (".GlobalEnv", {}),
    ("package:base", {}),
]


def search() -> list[str]:
    """Return attached names, in lookup order."""
    return [name for name, _ in _SEARCH_PATH]


def lookup(name: str):
    """Look up a name in the attached mappings, like R's ``get``."""
    for _, values in _SEARCH_PATH:
        if isinstance(values, dict) and name in values:
            return values[name]
    raise KeyError(name)


def _position(pos: int) -> int:
    if not isinstance(pos, int) or isinstance(pos, bool) or pos < 1:
        raise ValueError("pos must be a positive integer")
    return min(pos - 1, len(_SEARCH_PATH))


def _attach(name: str, values: object, pos: int = 2) -> None:
    _SEARCH_PATH.insert(_position(pos), (name, values))


def _detach_at(index: int) -> None:
    del _SEARCH_PATH[index]


def with_environment(env, code=None, *, pos: int = 2, name: str = "user:environment") -> Iterator:
    """Attach a mapping for ``code`` and detach it afterwards."""
    if code is None:
        return _environment_context(env, pos=pos, name=name)
    with _environment_context(env, pos=pos, name=name):
        return code()


@contextmanager
def _environment_context(env, *, pos: int, name: str):
    if not hasattr(env, "__contains__"):
        raise TypeError("env must be a mapping")
    index = _position(pos)
    _SEARCH_PATH.insert(index, (name, env))
    try:
        yield
    finally:
        _detach_at(index)


def local_environment(env=None, *, _local_envir=None, pos: int = 2,
                      name: str = "user:environment"):
    """Return a context manager that attaches an environment temporarily."""
    return _environment_context(env, pos=pos, name=name)


@contextmanager
def _named_context(name: str, values: object, *, pos: int = 2,
                   only_if_missing: bool = False):
    if only_if_missing and name in search():
        yield
        return
    index = _position(pos)
    _SEARCH_PATH.insert(index, (name, values))
    try:
        yield
    finally:
        _detach_at(index)


def with_package(package: str, code=None, *, pos: int = 2):
    """Attach ``package:<package>`` while running ``code``."""
    name = f"package:{package}"
    context = _named_context(name, {}, pos=pos, only_if_missing=True)
    if code is None:
        return context
    with context:
        return code()


def local_package(package: str, *, _local_envir=None, pos: int = 2):
    """Return a context manager that always attaches and then detaches a package."""
    return _named_context(f"package:{package}", {}, pos=pos)


def _namespace_name(package: str) -> str:
    return f"<environment: namespace:{package}>"


def with_namespace(package: str, code=None, *, warn_conflicts: bool = True):
    """Attach a package namespace while running ``code``."""
    context = _named_context(_namespace_name(package), {}, only_if_missing=True)
    if code is None:
        return context
    with context:
        return code()


def local_namespace(package: str, *, _local_envir=None, warn_conflicts: bool = True):
    """Return a context manager that always attaches a package namespace."""
    return _named_context(_namespace_name(package), {})
