"""with_file and local_file (R's file.R): files that delete themselves."""

from __future__ import annotations

import os
import shutil

from ._scope import current, force


def _paths(file) -> list[str]:
    """R's names2(): a string, a list of names, or a dict whose keys are the paths."""
    if isinstance(file, str):
        return [file]
    if isinstance(file, dict):
        return [str(key) for key in file]
    return [str(path) for path in file]


def _unlink(path: str) -> None:
    """unlink(path, recursive = TRUE): silent when the path is absent."""
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path, ignore_errors=True)
    elif os.path.lexists(path):
        os.remove(path)


def with_file(file, code):
    paths = _paths(file)
    try:
        force(code)
    finally:
        for path in paths:
            _unlink(path)
    return file


def local_file(file, *, _local_envir=None, **kwargs):
    paths = _paths(file) + [str(key) for key in kwargs]
    for path in paths:
        current(_local_envir).add(lambda path=path: _unlink(path))
    return file
