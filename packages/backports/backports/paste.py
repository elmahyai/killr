"""paste and paste0, including recycle0 for a zero-length argument."""

from __future__ import annotations

from backports._values import NA, BackportError, as_character, is_na

__all__ = ["paste", "paste0"]


def paste(*args, sep=" ", collapse=None, recycle0=False):
    columns = [as_character(arg) for arg in args]
    if recycle0 and any(len(column) == 0 for column in columns):
        _check_separator(sep)
        _check_collapse(collapse)
        if collapse is None:
            return []
        return ""
    return _paste_columns(columns, sep, collapse)


def paste0(*args, collapse=None, recycle0=False):
    return paste(*args, sep="", collapse=collapse, recycle0=recycle0)


def _check_separator(sep) -> str:
    if sep is None or is_na(sep):
        raise BackportError("invalid separator")
    if isinstance(sep, (list, tuple)):
        if len(sep) != 1 or is_na(sep[0]):
            raise BackportError("invalid separator")
        sep = sep[0]
    if not isinstance(sep, str):
        raise BackportError("invalid separator")
    return sep


def _check_collapse(collapse):
    if collapse is None:
        return None
    if is_na(collapse):
        raise BackportError("invalid 'collapse' argument")
    if isinstance(collapse, (list, tuple)):
        if len(collapse) != 1 or is_na(collapse[0]):
            raise BackportError("invalid 'collapse' argument")
        collapse = collapse[0]
    if not isinstance(collapse, str):
        raise BackportError("invalid 'collapse' argument")
    return collapse


def _paste_columns(columns, sep, collapse):
    sep = _check_separator(sep)
    collapse = _check_collapse(collapse)
    if not columns:
        joined = [""]
    elif all(len(column) == 0 for column in columns):
        joined = []
    else:
        width = max((len(column) for column in columns), default=0)
        filled = [column if column else [""] for column in columns]
        joined = []
        for index in range(width):
            parts = []
            for column in filled:
                item = column[index % len(column)]
                parts.append("NA" if item is NA else item)
            joined.append(sep.join(parts))
    if collapse is None:
        return joined
    if not joined:
        return ""
    return collapse.join(joined)
