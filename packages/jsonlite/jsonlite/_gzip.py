"""Gzipped JSON. The check is the text after gunzip, because the header stores a time."""

from __future__ import annotations

import gzip
from typing import Any

from jsonlite._base64 import base64_dec, base64_enc
from jsonlite._decode import fromJSON
from jsonlite._encode import toJSON


def as_gzjson_raw(x: Any, **options: Any) -> bytes:
    """JSON-encode ``x`` and gzip the text."""

    return gzip.compress(toJSON(x, **options).encode("utf-8"))


def as_gzjson_b64(x: Any, **options: Any) -> str:
    """JSON-encode ``x``, gzip it, and return base64 text."""

    encoded = base64_enc(as_gzjson_raw(x, **options))
    assert encoded is not None
    return encoded


def parse_gzjson_raw(buf: bytes, **options: Any) -> Any:
    """Gunzip raw bytes and parse the JSON."""

    return fromJSON(gzip.decompress(buf).decode("utf-8"), **options)


def parse_gzjson_b64(b64: str, **options: Any) -> Any:
    """Decode base64, gunzip, and parse the JSON."""

    return parse_gzjson_raw(base64_dec(b64), **options)
