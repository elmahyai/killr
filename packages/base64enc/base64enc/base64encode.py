"""Encode bytes or a file into base64 text, as R's ``base64encode``.

A string is a file name, not the bytes of that string. ``linewidth`` is
rounded down to a multiple of four after values below 4 are raised to 4.
A positive linewidth with no newline returns one string per line. A
newline joins those lines into one string. An empty raw vector is an
empty result. An empty file is not: it is ``None`` when the lines stay
separate, and one empty string when they are pasted.
"""

from __future__ import annotations

import base64
import io
import math
import os
import warnings

_INT_MIN = -2147483648
_INT_MAX = 2147483647
_SLICE = 65535

_RANGE_WARN = "NAs introduced by coercion to integer range"
_RAW_WARN = "out-of-range values treated as 0 in coercion to raw"
_IMAG_WARN = "imaginary parts discarded in coercion"
_COLLAPSE = "invalid 'collapse' argument"
_DESCRIPTION = "invalid 'description' argument"
_BINARY = "can only read from a binary connection"
_OPEN = "cannot open the connection"


def base64encode(what, linewidth=None, newline=None):
    """Encode ``what`` as base64.

    ``what`` is a raw vector (bytes, or numbers coerced with ``as.raw``),
    a binary file object, or a file name. ``None`` is an empty raw vector.
    ``linewidth`` missing, non-numeric, empty, or missing is no limit.
    ``newline`` missing is ``None``: lines stay separate. A string, including
    ``""``, joins them. The first string is used. A missing string in that
    position is the letters ``NA`` for a raw vector.

    A length-1 result is a one-element list. ``character(0)`` is ``[]``.
    The empty-file paste is ``[""]``, and the empty-file line split is
    ``None``.
    """
    lwd, range_warn = _linewidth(linewidth)
    if range_warn:
        warnings.warn(_RANGE_WARN, UserWarning, stacklevel=2)
    if _is_character(what):
        path = _character_path(what)
        handle = _open_path(path)
        try:
            return _encode_connection(handle, lwd, newline)
        finally:
            handle.close()
    kind = _connection_kind(what)
    if kind == "text":
        raise ValueError(_BINARY)
    if kind == "binary":
        return _encode_connection(what, lwd, newline)
    data = _as_raw(what)
    return _encode_bytes(data, lwd, newline)


def _linewidth(linewidth):
    """R's linewidth expression, then the ``is.na`` replacement.

    The return is ``(value, integer_range_warning)``. Non-numeric and
    empty input become 0 with no warning. ``as.integer`` of the first
    value truncates toward zero.
    """
    if not _is_numeric(linewidth):
        return 0, False
    values = _numeric_values(linewidth)
    if len(values) < 1:
        return 0, False
    value, warn = _as_integer(values[0])
    if value is None:
        return 0, warn
    if value > 0 and value < 4:
        value = 4
    return value, warn


def _is_numeric(value) -> bool:
    """``is.numeric``: integer or double, not logical and not character."""
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, range):
        return True
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return True
        return all(_is_numeric_element(item) for item in value)
    return False


def _is_numeric_element(item) -> bool:
    if item is None or isinstance(item, bool):
        return False
    return isinstance(item, (int, float))


def _numeric_values(value):
    if isinstance(value, (list, tuple, range)):
        return list(value)
    return [value]


def _as_integer(value):
    """``as.integer`` of one number. ``None`` means ``NA``.

    ``NaN`` and a real ``NA`` become missing with no warning. ``Inf`` and
    a value outside the 32-bit range warn and become missing.
    """
    if value is None or isinstance(value, bool):
        return None, False
    if isinstance(value, int):
        if value < _INT_MIN or value > _INT_MAX:
            return None, True
        return value, False
    if isinstance(value, float):
        if math.isnan(value):
            return None, False
        if math.isinf(value) or value <= _INT_MIN or value > _INT_MAX:
            return None, True
        truncated = math.trunc(value)
        if truncated < _INT_MIN or truncated > _INT_MAX:
            return None, True
        return int(truncated), False
    return None, False


def _is_character(what) -> bool:
    if isinstance(what, str):
        return True
    if isinstance(what, (list, tuple)) and any(isinstance(item, str) for item in what):
        if all(isinstance(item, str) or item is None for item in what):
            return True
    return False


def _character_path(what) -> str:
    if isinstance(what, str):
        return what
    if len(what) != 1 or what[0] is None:
        raise ValueError(_DESCRIPTION)
    return what[0]


def _open_path(path: str):
    """``file(path, "rb")``. Messages match the installed connection."""
    if path == "":
        warnings.warn(
            'file("") only supports open = "w+" and open = "w+b": using the former',
            UserWarning,
            stacklevel=3,
        )
        raise ValueError(_BINARY)
    if os.path.isdir(path):
        warnings.warn(
            f"'raw = FALSE' but '{path}' is not a regular file",
            UserWarning,
            stacklevel=3,
        )
        warnings.warn(
            f"cannot open file '{path}': it is a directory",
            UserWarning,
            stacklevel=3,
        )
        raise ValueError(_OPEN)
    try:
        return open(path, "rb")
    except OSError as exc:
        detail = exc.strerror or "No such file or directory"
        warnings.warn(
            f"cannot open file '{path}': {detail}",
            UserWarning,
            stacklevel=3,
        )
        raise ValueError(_OPEN) from exc


def _connection_kind(what):
    if isinstance(what, io.TextIOBase):
        return "text"
    if isinstance(what, (io.BufferedIOBase, io.RawIOBase)):
        return "binary"
    mode = getattr(what, "mode", None)
    if mode is None or not hasattr(what, "read"):
        return None
    if "b" in mode:
        return "binary"
    return "text"


def _encode_connection(handle, lwd: int, newline):
    """Read ``handle`` in slices and combine the chunk encodings.

    A positive linewidth rounds down to a multiple of 4, and the slice
    grows so it spans whole lines. ``65535`` is already a multiple of 3,
    so an unlimited encode pastes chunks with no padding in between.
    """
    slice_size = _SLICE
    used = lwd
    if lwd > 0:
        if lwd % 4 > 0:
            used = lwd - (lwd % 4)
        width = (used // 4) * 3
        if slice_size % width > 0:
            slice_size += width - (slice_size % width)
    parts = []
    while True:
        block = handle.read(slice_size)
        if not block:
            break
        parts.append(_encode_bytes(block, used, newline))
    if lwd > 0 and newline is None:
        if not parts:
            return None
        lines = []
        for part in parts:
            lines.extend(part)
        return lines
    collapse = _paste_collapse(newline)
    if not parts:
        return [""]
    pieces = []
    for part in parts:
        pieces.extend(part)
    if len(pieces) == 1:
        return pieces
    return [collapse.join(pieces)]


def _paste_collapse(newline) -> str:
    """``paste`` collapse. ``NULL`` is ``""``. Anything else must be text."""
    if newline is None:
        return ""
    if isinstance(newline, str):
        return newline
    if isinstance(newline, (list, tuple)) and len(newline) >= 1:
        first = newline[0]
        if isinstance(first, str):
            return first
    raise ValueError(_COLLAPSE)


def _encode_bytes(data: bytes, lwd: int, newline):
    """``B64_encode``. An empty buffer is ``character(0)``."""
    if len(data) == 0:
        return []
    limited = lwd
    if limited <= 0:
        limited = 0
    elif limited < 4:
        limited = 4
    limited -= limited & 3
    separator = _newline_chars(newline)
    if limited == 0 or separator is not None:
        step = (limited // 4) * 3 if limited else 0
        if limited == 0 or len(data) <= step:
            return [_b64(data)]
        chunks = [_b64(data[i : i + step]) for i in range(0, len(data), step)]
        return [separator.join(chunks)]
    step = (limited // 4) * 3
    return [_b64(data[i : i + step]) for i in range(0, len(data), step)]


def _newline_chars(newline):
    """The C newline pointer. ``None`` means there is no separator.

    A character vector uses its first string. A missing string is the
    bytes ``CHAR`` stores for ``NA``, which are the letters ``NA``.
    A non-character value leaves the pointer null, so lines stay separate.
    """
    if isinstance(newline, str):
        return newline
    if isinstance(newline, (list, tuple)) and len(newline) > 0:
        first = newline[0]
        if first is None:
            return "NA"
        if isinstance(first, str):
            return first
    return None


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _as_raw(what) -> bytes:
    """``as.raw``. ``None`` and an empty list are an empty raw vector."""
    if what is None:
        return b""
    if isinstance(what, memoryview):
        what = what.tobytes()
    if isinstance(what, (bytes, bytearray)):
        return bytes(what)
    if isinstance(what, (list, tuple, range)):
        elements = list(what)
    else:
        elements = [what]
    out = bytearray()
    imag = False
    integer_range = False
    out_of_range = False
    for item in elements:
        byte, flags = _one_raw(item)
        out.append(byte)
        imag = imag or flags[0]
        integer_range = integer_range or flags[1]
        out_of_range = out_of_range or flags[2]
    if imag:
        warnings.warn(_IMAG_WARN, UserWarning, stacklevel=3)
    if integer_range:
        warnings.warn(_RANGE_WARN, UserWarning, stacklevel=3)
    if out_of_range:
        warnings.warn(_RAW_WARN, UserWarning, stacklevel=3)
    return bytes(out)


def _one_raw(item):
    """One ``as.raw`` element and ``(imag, integer_range, out_of_range)``."""
    if isinstance(item, complex):
        imag = item.imag != 0
        byte, range_warn, raw_warn = _raw_from_float(item.real)
        return byte, (imag, range_warn, raw_warn)
    if isinstance(item, bool):
        return (1 if item else 0), (False, False, False)
    if item is None:
        return 0, (False, False, True)
    if isinstance(item, int):
        if item < 0 or item > 255:
            return 0, (False, False, True)
        return item, (False, False, False)
    if isinstance(item, float):
        byte, range_warn, raw_warn = _raw_from_float(item)
        return byte, (False, range_warn, raw_warn)
    if isinstance(item, (list, tuple)):
        return 0, (False, False, True)
    raise TypeError("cannot coerce to raw")


def _raw_from_float(value: float):
    """Truncate toward zero. ``(-1, 256)`` stays in range.

    A non-finite value other than ``NaN``, and a value outside the
    32-bit integer range, also warns that the integer coercion failed.
    ``-2147483648`` is that boundary: it is ``NA_integer_``.
    """
    if math.isnan(value):
        return 0, False, True
    if value <= _INT_MIN or value > _INT_MAX:
        return 0, True, True
    truncated = math.trunc(value)
    if truncated < 0 or truncated > 255:
        return 0, False, True
    return int(truncated), False, False
