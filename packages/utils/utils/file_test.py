"""Shell-style file tests from utils 4.5.0 ``file_test``."""

from __future__ import annotations

import math
import os
import stat


class UtilsError(Exception):
    """An error raised with R's stop message."""



def file_test(op, x, y=None):
    """R ``file_test(op, x, y)``."""
    if isinstance(op, (list, tuple)):
        if len(op) != 1:
            raise UtilsError("EXPR must be a length 1 vector")
        op = op[0]
    if not isinstance(op, str) or op == "":
        raise UtilsError("op must be a character string of length 1")

    paths_x = _as_paths(x)
    paths_y = _as_paths(y) if y is not None else None

    if op == "-f":
        return _wrap(x, [_test_f(path) for path in paths_x])
    if op == "-d":
        return _wrap(x, [_test_d(path) for path in paths_x])
    if op in ("-h", "-L"):
        return _wrap(x, [_test_link(path) for path in paths_x])
    if op in ("-nt", "-ot"):
        if paths_y is None:
            raise TypeError("file_test() missing 1 required positional argument: 'y'")
        length = max(len(paths_x), len(paths_y))
        flags = []
        for index in range(length):
            left = paths_x[index % len(paths_x)]
            right = paths_y[index % len(paths_y)]
            if op == "-nt":
                flags.append(_test_nt(left, right))
            else:
                flags.append(_test_ot(left, right))
        return _wrap_binary(x, y, flags)
    if op == "-x":
        return _wrap(x, [_test_access(path, os.X_OK) for path in paths_x])
    if op == "-w":
        return _wrap(x, [_test_access(path, os.W_OK) for path in paths_x])
    if op == "-r":
        return _wrap(x, [_test_access(path, os.R_OK) for path in paths_x])
    raise UtilsError(f"test '{op}' is not available")


def _wrap(original, flags: list[bool]):
    if isinstance(original, (list, tuple)):
        return flags
    if not flags:
        return False
    return flags[0]


def _wrap_binary(x, y, flags: list[bool]):
    if isinstance(x, (list, tuple)) or isinstance(y, (list, tuple)):
        return flags
    if not flags:
        return False
    return flags[0]


def _as_paths(value) -> list[str | None]:
    if value is None:
        return [None]
    if isinstance(value, float) and math.isnan(value):
        return [None]
    if isinstance(value, (list, tuple)):
        if not value:
            return []
        return [_one_path(item) for item in value]
    return [_one_path(value)]


def _one_path(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    return os.fspath(value)


def _expand(path: str | None) -> str | None:
    if path is None:
        return None
    return os.path.expanduser(path)


def _test_f(path: str | None) -> bool:
    text = _expand(path)
    if text is None:
        return False
    try:
        info = os.stat(text)
    except OSError:
        return False
    return not stat.S_ISDIR(info.st_mode)


def _test_d(path: str | None) -> bool:
    text = _expand(path)
    if text is None:
        return False
    try:
        info = os.stat(text)
    except OSError:
        return False
    return stat.S_ISDIR(info.st_mode)


def _test_link(path: str | None) -> bool:
    target = _sys_readlink(path)
    return target is not None and bool(target)


def _sys_readlink(path: str | None) -> str | None:
    text = _expand(path)
    if text is None:
        return None
    try:
        return os.readlink(text)
    except OSError:
        if os.path.lexists(text):
            return ""
        return None


def _mtime(path: str | None) -> float | None:
    text = _expand(path)
    if text is None:
        return None
    try:
        return os.path.getmtime(text)
    except OSError:
        return None


def _test_nt(left: str | None, right: str | None) -> bool:
    mt_left = _mtime(left)
    mt_right = _mtime(right)
    if mt_left is None or mt_right is None:
        return False
    return mt_left > mt_right


def _test_ot(left: str | None, right: str | None) -> bool:
    mt_left = _mtime(left)
    mt_right = _mtime(right)
    if mt_left is None or mt_right is None:
        return False
    return mt_left < mt_right


def _test_access(path: str | None, mode: int) -> bool:
    text = _expand(path)
    if text is None:
        return False
    try:
        return os.access(text, mode)
    except OSError:
        return False
