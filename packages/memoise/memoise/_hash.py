"""Cache keys for memoised calls.

The key is a hash of a canonical form of the bound arguments. It is not
``rlang::hash``. Two calls that bind the same values share a key, including
named arguments in either order.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Any


def canonical_bytes(obj: Any) -> bytes:
    return json.dumps(_plain(obj), separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def hash_object(obj: Any, algo: str = "sha256") -> str:
    blob = canonical_bytes(obj)
    if algo in {"md5", "sha1", "sha256", "sha384", "sha512"}:
        return hashlib.new(algo, blob).hexdigest()
    if algo == "xxhash64":
        from digest.algos import xxh64

        return f"{xxh64(blob):016x}"
    if algo == "xxhash32":
        from digest.algos import xxh32

        return f"{xxh32(blob):08x}"
    raise ValueError(f"unknown algo {algo}")


def _plain(obj: Any) -> Any:
    if obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        if math.isnan(obj):
            return {"t": "nan"}
        if math.isinf(obj):
            return {"t": "inf", "s": 1 if obj > 0 else -1}
        return obj
    if isinstance(obj, bytes):
        return {"t": "raw", "v": obj.hex()}
    if isinstance(obj, dict):
        return {"t": "dict", "v": [[_plain(key), _plain(value)] for key, value in obj.items()]}
    if isinstance(obj, (list, tuple)):
        kind = "list" if isinstance(obj, list) else "tuple"
        return {"t": kind, "v": [_plain(item) for item in obj]}
    return {"t": "repr", "v": repr(obj)}
