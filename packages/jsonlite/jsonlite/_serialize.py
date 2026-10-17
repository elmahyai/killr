"""Type-tagged JSON from serializeJSON, and the reverse unpack."""

from __future__ import annotations

import json
from typing import Any

from jsonlite._encode import toJSON
from jsonlite._values import Scalar


def serializeJSON(x: Any, *, digits: int = 8, pretty: bool = False) -> str:
    """Encode ``x`` by storage type so unserializeJSON can restore it."""

    return toJSON(_pack(x), digits=digits, pretty=pretty)


def unserializeJSON(txt: str) -> Any:
    """Restore an object written by serializeJSON."""

    return _unpack(json.loads(txt))


def _pack(obj: Any) -> Any:
    if obj is None:
        return {"type": Scalar("NULL")}
    if isinstance(obj, dict):
        names = list(obj)
        return {
            "type": Scalar("list"),
            "attributes": {"names": _pack_atomic(names, "character")},
            "value": [_pack(obj[name]) for name in names],
        }
    if isinstance(obj, list):
        if all(isinstance(item, str) for item in obj):
            return _pack_atomic(obj, "character")
        if all(isinstance(item, bool) for item in obj):
            return _pack_atomic(obj, "logical")
        if all(isinstance(item, int) and not isinstance(item, bool) for item in obj):
            return _pack_atomic(obj, "integer")
        if all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in obj):
            return _pack_atomic(obj, "double")
        return {
            "type": Scalar("list"),
            "attributes": {},
            "value": [_pack(item) for item in obj],
        }
    if isinstance(obj, bool):
        return _pack_atomic([obj], "logical")
    if isinstance(obj, int):
        return _pack_atomic([obj], "integer")
    if isinstance(obj, float):
        return _pack_atomic([obj], "double")
    if isinstance(obj, str):
        return _pack_atomic([obj], "character")
    if isinstance(obj, (bytes, bytearray)):
        from jsonlite._base64 import base64_enc

        return {
            "type": Scalar("raw"),
            "attributes": {},
            "value": Scalar(base64_enc(bytes(obj))),
        }
    raise TypeError(f"no serializeJSON mapping for {type(obj).__name__}")


def _pack_atomic(values: list, mode: str) -> dict:
    return {"type": Scalar(mode), "attributes": {}, "value": values}


def _unpack(obj: Any) -> Any:
    if not isinstance(obj, dict) or "type" not in obj:
        return obj
    mode = obj["type"]
    if mode == "NULL":
        return None
    if mode == "list":
        values = [_unpack(item) for item in obj.get("value") or []]
        attributes = obj.get("attributes") or {}
        names = attributes.get("names")
        if names:
            unpacked = _unpack(names)
            if isinstance(unpacked, str):
                unpacked = [unpacked]
            return dict(zip(unpacked, values))
        return values
    if mode in {"integer", "double", "logical", "character"}:
        values = obj.get("value") or []
        if len(values) == 1:
            return values[0]
        return values
    if mode == "raw":
        from jsonlite._base64 import base64_dec

        return base64_dec(obj["value"])
    raise TypeError(f"no unserializeJSON mapping for {mode}")
