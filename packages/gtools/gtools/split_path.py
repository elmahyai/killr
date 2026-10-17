"""Split a file path into components (gtools 3.9.5 ``split_path``)."""

from __future__ import annotations

import warnings
from collections.abc import Sequence

import numpy as np


def _is_na_char(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and np.isnan(value):
        return True
    if isinstance(value, np.floating) and np.isnan(value):
        return True
    return False


def _r_dirname(path: str | None) -> str | None:
    if _is_na_char(path):
        return None
    assert path is not None
    if path == "":
        return ""
    end = len(path)
    while end > 1 and path[end - 1] == "/":
        end -= 1
    trimmed = path[:end]
    slash = trimmed.rfind("/")
    if slash < 0:
        return "."
    start = slash
    while start > 0 and trimmed[start - 1] == "/":
        start -= 1
    return "/" if start == 0 else trimmed[:start]


def _r_basename(path: str | None) -> str | None:
    if _is_na_char(path):
        return None
    assert path is not None
    if path == "":
        return ""
    end = len(path)
    while end > 1 and path[end - 1] == "/":
        end -= 1
    trimmed = path[:end]
    slash = trimmed.rfind("/")
    if slash < 0:
        return trimmed
    return trimmed[slash + 1 :]


def _split_path_inner(path: str | None) -> list[str | None]:
    parent = _r_dirname(path)
    if parent in (".", path):
        return [_r_basename(path)]
    return [_r_basename(path), *_split_path_inner(parent)]


def _drop_empty(parts: list[str | None]) -> list[str | None]:
    kept: list[str | None] = []
    for part in parts:
        if _is_na_char(part):
            kept.append(None)
        elif part > "":
            kept.append(part)
    return kept


def _coerce_scalar(x) -> str | None:
    if isinstance(x, (str, bytes)):
        if isinstance(x, bytes):
            return x.decode("utf-8")
        return x
    if isinstance(x, np.ndarray):
        flat = np.asarray(x).ravel(order="F")
        if flat.size == 0:
            raise ValueError("argument is of length zero")
        if flat.size > 1:
            warnings.warn(
                "This function is not vectorized."
                "Only processing the first element of x.",
                RuntimeWarning,
                stacklevel=3,
            )
        item = flat[0]
        if _is_na_char(item):
            return None
        return str(item)
    if isinstance(x, Sequence):
        if len(x) == 0:
            raise ValueError("argument is of length zero")
        if len(x) > 1:
            warnings.warn(
                "This function is not vectorized."
                "Only processing the first element of x.",
                RuntimeWarning,
                stacklevel=3,
            )
        item = x[0]
        if _is_na_char(item):
            return None
        return str(item)
    if _is_na_char(x):
        return None
    return str(x)


def split_path(x, depth_first: bool = True) -> list[str | None]:
    """Return path components; default order is depth-first (leaf to root)."""
    path = _coerce_scalar(x)
    parts = _split_path_inner(path)
    if not depth_first:
        parts = list(reversed(parts))
    return _drop_empty(parts)
