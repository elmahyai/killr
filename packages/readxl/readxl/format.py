"""Decide whether a file is xls or xlsx."""

from __future__ import annotations

import os


_XLSX_EXT = {"xlsx": "xlsx", "xlsm": "xlsx", "xltx": "xlsx", "xltm": "xlsx"}
_XLSX_SIG = bytes((0x50, 0x4B, 0x03, 0x04))
_XLS_SIG = bytes((0xD0, 0xCF, 0x11, 0xE0, 0xA1, 0xB1, 0x1A, 0xE1))


def _one(path) -> str:
    if path is None:
        return ""
    return str(path)


def format_from_ext(path):
    """``xlsx`` or ``xls`` from the extension, or ``None`` when it is unknown."""

    paths = path if isinstance(path, (list, tuple)) else [path]
    out = []
    for item in paths:
        text = _one(item)
        extension = text.rsplit(".", 1)[-1].lower() if "." in text else ""
        if extension == "xls":
            out.append("xls")
        else:
            out.append(_XLSX_EXT.get(extension))
    return out[0] if not isinstance(path, (list, tuple)) else out


def _signature(path: str):
    try:
        with open(path, "rb") as handle:
            return handle.read(8)
    except OSError:
        return b""


def format_from_signature(path):
    """``xlsx`` or ``xls`` from the leading bytes, or ``None``."""

    paths = path if isinstance(path, (list, tuple)) else [path]
    out = []
    for item in paths:
        text = _one(item)
        if not os.path.exists(text):
            raise FileNotFoundError(text)
        blob = _signature(text)
        if blob[:4] == _XLSX_SIG:
            out.append("xlsx")
        elif blob[:8] == _XLS_SIG:
            out.append("xls")
        else:
            out.append(None)
    return out[0] if not isinstance(path, (list, tuple)) else out


def excel_format(path, guess=True):
    """Extension first, then the file signature when ``guess`` is true."""

    if not isinstance(guess, bool):
        raise ValueError("`guess` must be either TRUE or FALSE")
    many = isinstance(path, (list, tuple))
    paths = list(path) if many else [path]
    found = format_from_ext(paths)
    if guess:
        for index, item in enumerate(found):
            text = _one(paths[index])
            if item is None and os.path.exists(text):
                found[index] = format_from_signature(text)
    return found if many else found[0]


def check_format(path: str) -> str:
    found = excel_format(path)
    if found is None:
        raise ValueError("Can't establish that the input is either xls or xlsx.")
    return found
