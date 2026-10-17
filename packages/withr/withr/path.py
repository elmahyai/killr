"""with_path and local_path (R's path.R): the PATH environment variable."""

from __future__ import annotations

import os

from .factory import local_, with_

_ACTIONS = ("prefix", "suffix", "replace")


def _entries() -> list[str]:
    value = os.environ.get("PATH", "")
    return value.split(os.pathsep) if value else []


def get_path(*_, **__) -> list[str]:
    return _entries()


def _normalize(entry: str) -> str:
    """normalizePath(mustWork = FALSE): resolve an existing path, keep a missing one."""
    entry = str(entry)
    return os.path.realpath(entry) if os.path.exists(entry) else entry


def set_path(path, action: str = "prefix") -> list[str]:
    if action not in _ACTIONS:
        raise ValueError('`action` must be "prefix", "suffix" or "replace"')
    if isinstance(path, str):
        path = [path]
    new = [_normalize(entry) for entry in path]
    old = _entries()
    if action == "replace":
        merged = new
    elif action == "suffix":
        merged = old + new
    else:
        merged = new + old
    os.environ["PATH"] = os.pathsep.join(merged)
    return old


def _restore(old) -> None:
    set_path(old, "replace")


with_path = with_(set_path, reset_fn=_restore, get_fn=get_path)
local_path = local_(set_path, reset_fn=_restore, get_fn=get_path)
