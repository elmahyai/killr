"""digest(): hash an R object, a string, or a file."""

from __future__ import annotations

import math
import os
import warnings
from pathlib import Path

from digest.algos import (
    blake3,
    crc32,
    crc32c,
    md5,
    murmur32,
    sha1,
    sha256,
    sha512,
    spooky128,
    xxh32,
    xxh64,
    xxh3_64,
    xxh3_128,
)
from digest.serialize import NA, Obj, serialize as r_serialize

_MISSING = object()

ALGOS = (
    "md5",
    "sha1",
    "crc32",
    "sha256",
    "sha512",
    "xxhash32",
    "xxhash64",
    "murmur32",
    "spookyhash",
    "blake3",
    "crc32c",
    "xxh3_64",
    "xxh3_128",
)

_OPTIONS = {
    "serializeVersion": 2,
    "digestOldCRC32Format": False,
    "sha1PackageVersion": "0.6.39",
}


class DigestError(Exception):
    """An error digest reports, with the R message."""


def get_option(name: str):
    return _OPTIONS[name]


def set_option(name: str, value) -> None:
    _OPTIONS[name] = value


def match_arg(value, choices: tuple[str, ...], name: str = "arg") -> str:
    """R's match.arg: the default vector selects the first choice, and a unique prefix matches."""
    if isinstance(value, (list, tuple)):
        if list(value) == list(choices):
            return choices[0]
        if len(value) != 1:
            raise DigestError(f"'{name}' must be of length 1")
        value = value[0]
    if not isinstance(value, str):
        raise DigestError(f"'{name}' must be NULL or a character vector")
    if value in choices:
        return value
    matches = [choice for choice in choices if choice.startswith(value)]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        listed = ", ".join(repr(choice) for choice in choices)
        raise DigestError(f"'{name}' should be one of {listed}")
    raise DigestError(f"'{name}' matched more than one choice: {', '.join(matches)}")


def digest(
    object=_MISSING,
    algo="md5",
    serialize=True,
    file=False,
    length=math.inf,
    skip="auto",
    ascii=False,
    raw=False,
    seed=0,
    errormode="stop",
    serializeVersion=None,
):
    """Hash ``object``. Argument names follow the R function."""
    try:
        return _digest(
            object,
            algo=algo,
            serialize_object=serialize,
            file=file,
            length=length,
            skip=skip,
            ascii=ascii,
            raw=raw,
            seed=seed,
            serializeVersion=serializeVersion,
        )
    except DigestError as exc:
        return _fail(str(exc), errormode)


def _fail(message: str, errormode: str):
    mode = match_arg(errormode, ("stop", "warn", "silent"), "errormode")
    if mode == "stop":
        raise DigestError(message)
    if mode == "warn":
        warnings.warn(message, stacklevel=3)
        return NA
    return None


def _digest(
    object,
    algo,
    serialize_object,
    file,
    length,
    skip,
    ascii,
    raw,
    seed,
    serializeVersion,
):
    algo = match_arg(algo, ALGOS, "algo")
    if isinstance(file, str) and object is _MISSING:
        object = file
        file = True
    if object is _MISSING:
        raise DigestError("argument \"object\" is missing, with no default")
    if math.isinf(length):
        length = -1
    length = int(length)
    streaming = algo == "spookyhash"
    if streaming and not serialize_object:
        raise DigestError(f"{algo} algorithm is not available without serialization.")
    version = _OPTIONS["serializeVersion"] if serializeVersion is None else int(serializeVersion)
    payload = None
    if serialize_object and not file:
        if not streaming:
            payload = r_serialize(object, version=version, ascii=ascii)
        if isinstance(skip, str) and skip == "auto":
            skip = 14 if not ascii else _ascii_skip(payload)
    elif not _is_character(object) and not _is_raw(object) and not streaming:
        raise DigestError(
            "Argument object must be of type character or raw vector if serialize is FALSE"
        )
    if file and not _is_character(object):
        raise DigestError("file=TRUE can only be used with a character object")
    if file and streaming:
        raise DigestError(f"{algo} algorithm can not be used with files.")
    if isinstance(skip, str):
        skip = 0
    skip = int(skip)
    seed32, seed64 = _seeds(seed)
    if file:
        payload = _read_file(object, errormode="stop")
        if skip < 0:
            skip = 0
        blob = _slice(payload, skip, length)
        digest_bytes = _hash_bytes(algo, blob, seed32, seed64)
    elif streaming:
        blob = _spooky_message(object, skip, version, ascii, serialize_object)
        digest_bytes = spooky128(blob)
    else:
        if payload is None:
            payload = _plain_bytes(object)
        if skip < 0:
            skip = 0
        blob = _slice(payload, skip, length)
        digest_bytes = _hash_bytes(algo, blob, seed32, seed64)
    if algo == "crc32" and _OPTIONS["digestOldCRC32Format"] and not raw:
        text = digest_bytes.hex()
        return text.lstrip("0")
    if raw:
        return digest_bytes
    return digest_bytes.hex()


def _hash_bytes(algo: str, blob: bytes, seed32: int, seed64: int) -> bytes:
    if algo == "md5":
        return md5(blob)
    if algo == "sha1":
        return sha1(blob)
    if algo == "crc32":
        return crc32(blob).to_bytes(4, "big")
    if algo == "sha256":
        return sha256(blob)
    if algo == "sha512":
        return sha512(blob)
    if algo == "xxhash32":
        return xxh32(blob, seed32).to_bytes(4, "big")
    if algo == "xxhash64":
        return xxh64(blob, seed64).to_bytes(8, "big")
    if algo == "murmur32":
        return murmur32(blob, seed32).to_bytes(4, "big")
    if algo == "blake3":
        return blake3(blob)
    if algo == "crc32c":
        return crc32c(blob).to_bytes(4, "big")
    if algo == "xxh3_64":
        return xxh3_64(blob, seed64).to_bytes(8, "big")
    if algo == "xxh3_128":
        high, low = xxh3_128(blob, seed64)
        return high.to_bytes(8, "big") + low.to_bytes(8, "big")
    raise DigestError(f"unknown algo {algo}")


def _spooky_message(object, skip: int, version: int, ascii: bool, serialize_object: bool) -> bytes:
    """Spooky skips with an 8-bit counter, then hashes the rest of the serialization."""
    if not serialize_object:
        raise DigestError("spookyhash algorithm is not available without serialization.")
    payload = r_serialize(object, version=version, ascii=ascii)
    skip_u8 = skip & 0xFF
    if skip_u8 >= len(payload):
        return b""
    return payload[skip_u8:]


def _plain_bytes(object) -> bytes:
    if isinstance(object, (bytes, bytearray)):
        return bytes(object)
    if isinstance(object, Obj) and object.kind == "raw":
        return bytes(object.data)
    if isinstance(object, Obj) and object.kind == "string":
        return _string_bytes(object.data[0] if object.data else "")
    if isinstance(object, str):
        return _string_bytes(object)
    if isinstance(object, (list, tuple)) and object and isinstance(object[0], str):
        # R's asChar keeps the first element of a character vector.
        return _string_bytes(object[0])
    raise DigestError(
        "Argument object must be of type character or raw vector if serialize is FALSE"
    )


def _string_bytes(value) -> bytes:
    if value is NA or value is None:
        return b"NA"
    return str(value).encode("utf-8")


def _is_character(object) -> bool:
    if isinstance(object, str):
        return True
    if isinstance(object, Obj) and object.kind == "string":
        return True
    if isinstance(object, (list, tuple)) and all(isinstance(item, str) or item is NA for item in object):
        return bool(object) or True
    return False


def _is_raw(object) -> bool:
    if isinstance(object, (bytes, bytearray)):
        return True
    return isinstance(object, Obj) and object.kind == "raw"


def _slice(payload: bytes, skip: int, length: int) -> bytes:
    if skip > 0:
        if skip >= len(payload):
            payload = b""
        else:
            payload = payload[skip:]
    if length >= 0 and length < len(payload):
        payload = payload[:length]
    return payload


def _read_file(object, errormode: str) -> bytes:
    if isinstance(object, Obj) and object.kind == "string":
        path = "" if not object.data or object.data[0] is NA else object.data[0]
    elif isinstance(object, str):
        path = object
    else:
        raise DigestError("file=TRUE can only be used with a character object")
    path = os.path.expanduser(path)
    target = Path(path)
    if not target.exists():
        raise DigestError(f"The file does not exist: {path}")
    if target.is_dir():
        raise DigestError(f"The specified pathname is not a file: {path}")
    if not os.access(path, os.R_OK):
        raise DigestError(f"The specified file is not readable: {path}")
    return target.read_bytes()


def _seeds(seed) -> tuple[int, int]:
    """as.integer(seed). A negative value sign-extends when the C parameter is 64 bits."""
    if isinstance(seed, float) and math.isnan(seed):
        raise DigestError("seed is NA")
    value = int(seed)
    value &= 0xFFFFFFFF
    if value >= 0x80000000:
        signed = value - 0x100000000
    else:
        signed = value
    return value, signed & 0xFFFFFFFFFFFFFFFF


def _ascii_skip(payload: bytes | None) -> int:
    if payload is None:
        return 0
    count = 0
    for index, byte in enumerate(payload[:30]):
        if byte == 10:
            count += 1
            if count == 4:
                return index + 1
    return 0

