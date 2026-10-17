"""Build a ``data:`` URI from bytes or a file, as R's ``dataURI``."""

from __future__ import annotations

import base64
import io

from base64enc.base64encode import _connection_kind, _open_path

_ENCODING = 'encoding must be either NULL or "base64"'
_MUTUAL = "data and file are mutually exclusive"
_BINARY = "can only read from a binary connection"
_CHUNK = 1048576
_UNRESERVED = frozenset(
    b"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~"
)


def dataURI(data=None, mime="", encoding="base64", *, file=None):
    """Return ``data:[mime][;base64],<payload>``.

    ``data`` is bytes, numbers, a text or binary connection, or strings to
    collapse with a newline. ``file`` is a path read as binary; it cannot
    be combined with ``data``. ``encoding`` is ``"base64"`` or ``None`` for
    percent-encoding. An empty ``mime`` omits the type from the prefix.
    """
    if encoding is not None and encoding != "base64":
        raise ValueError(_ENCODING)
    payload = data
    handle = None
    if file is not None:
        if data is not None:
            raise ValueError(_MUTUAL)
        handle = _open_path(file)
        payload = handle
    try:
        body = _payload_bytes(payload)
        if not isinstance(body, bytes):
            body = _collapse_text(body)
        prefix = _prefix(mime, encoding)
        if not isinstance(body, bytes):
            raise ValueError("RAW() can only be applied to a 'raw', not a 'character'")
        if encoding is None:
            encoded = _uri_encode(body)
        else:
            encoded = base64.b64encode(body).decode("ascii")
        return prefix + encoded
    finally:
        if handle is not None:
            handle.close()


def _prefix(mime, encoding):
    """``paste("data:", mime[1], optional ";base64", ",", sep="")``."""
    if isinstance(mime, (list, tuple)):
        mime_text = "NA" if len(mime) == 0 or mime[0] is None else str(mime[0])
    elif mime is None:
        mime_text = "NA"
    else:
        mime_text = str(mime)
    middle = ";base64" if encoding is not None else ""
    return f"data:{mime_text}{middle},"


def _payload_bytes(payload):
    """Read connections; leave raw bytes and other values for later."""
    kind = _connection_kind(payload)
    if kind == "text":
        if isinstance(payload, io.TextIOBase):
            return payload.readlines()
        text = payload.read()
        if isinstance(text, bytes):
            raise ValueError(_BINARY)
        return text.splitlines(keepends=False) if isinstance(text, str) else text
    if kind == "binary":
        parts = bytearray()
        while True:
            block = payload.read(_CHUNK)
            if not block:
                break
            parts.extend(block)
        return bytes(parts)
    if isinstance(payload, (bytes, bytearray, memoryview)):
        return bytes(payload)
    if payload is None:
        return b""
    if isinstance(payload, str):
        return payload
    if isinstance(payload, (list, tuple, range)):
        return payload
    return payload


def _collapse_text(data):
    """``paste(as.character(data), collapse="\\n")``."""
    if isinstance(data, str):
        return data
    if isinstance(data, (list, tuple)):
        return "\n".join("NA" if item is None else str(item) for item in data)
    return str(data)


def _uri_encode(data: bytes) -> str:
    """Percent-encode bytes; unreserved octets stay literal."""
    parts = []
    for byte in data:
        if byte in _UNRESERVED:
            parts.append(chr(byte))
        else:
            parts.append(f"%{byte:02X}")
    return "".join(parts)
