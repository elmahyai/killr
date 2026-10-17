"""Scoped library-search-path state for withr's libpath helpers."""

from __future__ import annotations

import os
import sys
import tempfile
from contextlib import contextmanager


_LIBPATHS = list(sys.path)


def libpaths() -> list[str]:
    """Return the current process-local library search path."""
    return list(_LIBPATHS)


def _paths(new) -> list[str]:
    if isinstance(new, (str, os.PathLike)):
        new = [new]
    return [os.path.abspath(os.fspath(path)) for path in new]


def _set_libpaths(new, action: str = "replace") -> list[str]:
    if action not in {"replace", "prefix", "suffix"}:
        raise ValueError('`action` must be "replace", "prefix" or "suffix"')
    old = list(_LIBPATHS)
    fresh = _paths(new)
    if action == "prefix":
        fresh += old
    elif action == "suffix":
        fresh = old + fresh
    _LIBPATHS[:] = fresh
    return old


@contextmanager
def _libpath_context(new, action: str = "replace"):
    old = _set_libpaths(new, action)
    try:
        yield
    finally:
        _LIBPATHS[:] = old


def with_libpaths(new, code=None, *, action: str = "replace"):
    """Run ``code`` with a temporarily modified library path list."""
    context = _libpath_context(new, action)
    if code is None:
        return context
    with context:
        return code()


def local_libpaths(new=None, *, _local_envir=None, action: str = "replace"):
    """Return a context manager restoring library paths on exit."""
    return _libpath_context([] if new is None else new, action)


def with_temp_libpaths(code=None):
    """Run ``code`` with a fresh temporary path prefixed."""
    path = tempfile.mkdtemp(prefix="withr-lib-")
    context = _libpath_context(path, "prefix")
    if code is None:
        return _temporary_context(path, context)
    with _temporary_context(path, context):
        return code()


def local_temp_libpaths(*, _local_envir=None):
    """Return a context manager with a fresh temporary path prefixed."""
    path = tempfile.mkdtemp(prefix="withr-lib-")
    return _temporary_context(path, _libpath_context(path, "prefix"))


@contextmanager
def _temporary_context(path, context):
    try:
        with context:
            yield
    finally:
        try:
            os.rmdir(path)
        except OSError:
            pass
