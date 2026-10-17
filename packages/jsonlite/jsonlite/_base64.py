"""Base64 and base64url, using the standard library."""

from __future__ import annotations

import base64


def base64_enc(input: bytes | str | None) -> str | None:
    """Encode bytes as base64. A string is encoded as UTF-8. None stays missing."""

    if input is None:
        return None
    return base64.b64encode(_as_bytes(input)).decode("ascii")


def base64_dec(input: bytes | str) -> bytes:
    """Decode base64 text or bytes to raw bytes."""

    return base64.b64decode(_as_bytes(input), validate=False)


def base64url_enc(input: bytes | str | None) -> str | None:
    """Encode as base64url: ``-`` and ``_`` replace ``+`` and ``/``, and padding is removed."""

    text = base64_enc(input)
    if text is None:
        return None
    return text.translate(str.maketrans("+/", "-_")).rstrip("=")


def base64url_dec(input: str) -> bytes:
    """Decode base64url text, restoring the padding."""

    text = "".join(input.split())
    text = text.translate(str.maketrans("-_", "+/"))
    text += "=" * ((-len(text)) % 4)
    return base64_dec(text)


def _as_bytes(value: bytes | str) -> bytes:
    if isinstance(value, str):
        return value.encode("utf-8")
    return bytes(value)
