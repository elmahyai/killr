"""Decode base64 text into bytes, as R's ``base64decode``.

A character vector decodes each element separately and concatenates the
bytes. A connection is read with ``readLines``. The ``file`` argument
opens a text file the same way. ``output`` writes bytes to a path or
binary connection and returns the length written.
"""

from __future__ import annotations

import base64
import io

_B64_CHARS = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/="
)

_MUTUAL = "'what' and 'file' are mutually exclusive"
_OUTPUT = "output must be a filename, connection or NULL"
_BINARY = "I can only decode base64 strings or raw vectors"


def base64decode(what=None, output=None, *, file=None, strict=False):
    """Decode base64 from ``what`` or ``file``.

    ``what`` is a string, a list of strings, bytes, or a text connection.
    ``None`` with no ``file`` is an error. ``output`` ``None`` returns
    bytes. A path or binary connection writes the bytes and returns the
    length. ``strict`` rejects invalid padding and non-alphabet bytes.
    """
    if file is not None:
        if what is not None:
            raise ValueError(_MUTUAL)
        handle = open(file, "r", encoding="utf-8", errors="surrogateescape")
        try:
            lines = handle.readlines()
        finally:
            handle.close()
        what = [line.rstrip("\n\r") for line in lines]
    data = _decode_input(what, strict)
    if output is None:
        return data
    if isinstance(output, str):
        handle = open(output, "wb")
        try:
            handle.write(data)
        finally:
            handle.close()
        return len(data)
    if isinstance(output, (io.BufferedIOBase, io.RawIOBase)):
        output.write(data)
        return len(data)
    raise ValueError(_OUTPUT)


def _decode_input(what, strict: bool) -> bytes:
    if what is None:
        raise ValueError(_BINARY)
    if isinstance(what, (bytes, bytearray, memoryview)):
        return _decode_one(bytes(what), strict)
    if isinstance(what, str):
        return _decode_one(what, strict)
    if isinstance(what, io.TextIOBase):
        lines = what.readlines()
        return _decode_lines(lines, strict)
    if isinstance(what, (list, tuple)):
        if len(what) == 0:
            return b""
        if all(isinstance(item, str) or item is None for item in what):
            parts = []
            for item in what:
                text = "NA" if item is None else item
                parts.append(_decode_one(text, strict))
            return b"".join(parts)
        if len(what) == 1:
            return _decode_input(what[0], strict)
    if isinstance(what, (io.BufferedIOBase, io.RawIOBase)):
        text = what.read()
        if isinstance(text, bytes):
            return _decode_one(text, strict)
        return _decode_one(text, strict)
    raise ValueError(_BINARY)


def _decode_lines(lines, strict: bool) -> bytes:
    strings = []
    for line in lines:
        if isinstance(line, bytes):
            strings.append(line.decode("utf-8", errors="surrogateescape"))
        else:
            strings.append(line.rstrip("\n\r"))
    return _decode_input(strings, strict)


def _decode_one(text: str | bytes, strict: bool) -> bytes:
    if isinstance(text, bytes):
        payload = bytes(b for b in text if chr(b) in _B64_CHARS)
    else:
        payload = "".join(c for c in text if c in _B64_CHARS).encode("ascii")
    if strict:
        return _decode_strict(payload)
    if not payload:
        return b""
    rem = len(payload) % 4
    if rem == 1:
        return b""
    if rem:
        payload += b"=" * (4 - rem)
    return base64.b64decode(payload, validate=False)


def _decode_strict(payload: bytes) -> bytes:
    """Match ``B64_decode`` strict checks (padding and alphabet)."""
    pad = 0
    idx = len(payload)
    while idx > 0 and payload[idx - 1] == ord("="):
        pad += 1
        idx -= 1
    body = payload[:idx]
    if pad > 2:
        raise ValueError(
            f"Padding is not allowed at position {idx} in base64 string "
            "(not allowed in strict mode)"
        )
    pos = 0
    for pos, byte in enumerate(body):
        if not _b64_byte(byte):
            char = chr(byte) if byte >= 32 and byte < 127 else byte
            raise ValueError(
                f"Invalid character ({char!r}) at position {pos + 1} in base64 "
                "string (not allowed in strict mode)"
            )
    if pad == 1:
        raise ValueError(
            f"Padding is not allowed at position {len(body)} in base64 string "
            "(not allowed in strict mode)"
        )
    tail = payload[idx + pad :]
    for pos, byte in enumerate(tail, start=idx + pad):
        if byte not in (ord("="), ord("\n"), ord("\r"), ord(" ")):
            char = chr(byte) if byte >= 32 and byte < 127 else byte
            raise ValueError(
                f"Invalid character ({char!r}) at position {pos + 1} in base64 "
                "string (not allowed in strict mode)"
            )
    return base64.b64decode(payload, validate=True)


def _b64_byte(byte: int) -> bool:
    if ord("A") <= byte <= ord("Z"):
        return True
    if ord("a") <= byte <= ord("z"):
        return True
    if ord("0") <= byte <= ord("9"):
        return True
    return byte in (ord("+"), ord("/"))
