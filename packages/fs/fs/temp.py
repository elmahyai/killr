"""Temporary path names. The stack makes example paths repeatable."""

from __future__ import annotations

import tempfile

from fs._error import assert_no_missing
from fs.path import FsPath, path, path_expand, path_tidy

_stack: list[str] = []


def file_temp_push(paths) -> FsPath:
    """Put paths at the end of the temporary-name stack."""
    incoming = list(path_tidy(paths))
    assert_no_missing(incoming, "path")
    expanded = [item for item in path_expand(incoming)]
    _stack.extend(expanded)
    return path_tidy(incoming)


def file_temp_pop():
    """Remove and return the next stacked name, or ``None`` when it is empty."""
    if not _stack:
        return None
    value = _stack.pop(0)
    return path_tidy(value)[0]


def _suffix(ext) -> str:
    text = "" if ext is None else str(ext)
    if text == "":
        return ""
    return "." + (text[1:] if text.startswith(".") else text)


def file_temp(pattern="file", tmp_dir=None, ext="") -> FsPath:
    """A temporary file name. A stacked name is used before a new one is made."""
    directory = tempfile.gettempdir() if tmp_dir is None else tmp_dir
    directories = list(path_tidy(directory))
    assert_no_missing(directories, "tmp_dir")
    stacked = file_temp_pop()
    if stacked is not None:
        return path_tidy(stacked)
    patterns = [pattern] if isinstance(pattern, str) else list(pattern)
    extensions = [ext] if isinstance(ext, str) else list(ext)
    count = max(len(directories), len(patterns), len(extensions))
    if len(directories) == 1:
        directories *= count
    if len(patterns) == 1:
        patterns *= count
    if len(extensions) == 1:
        extensions *= count
    values = [
        tempfile.mktemp(prefix=str(prefix), dir=folder, suffix=_suffix(suffix))
        for prefix, folder, suffix in zip(patterns, directories, extensions)
    ]
    return path_tidy(values)


def path_temp(*parts) -> FsPath:
    """A path inside the process temporary directory."""
    return path(tempfile.gettempdir(), *parts)
