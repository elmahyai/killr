"""HMAC from digest 0.6.39.

Block size is read from the algo text before ``digest`` resolves a prefix.
A crc32 key longer than that block keeps the first byte of the raw digest.
"""

from __future__ import annotations

import warnings

from digest.hashing import digest
from digest.makeraw import makeRaw, make_raw_digest

_LENGTH = "the condition has length > 1"
_ZERO = "argument is of length zero"
_MISSING = "missing value where TRUE/FALSE needed"
_NOT_LOGICAL = "argument is not interpretable as logical"
_TIMES = "invalid 'times' argument"
_RECYCLE = "longer object length is not a multiple of shorter object length"


def hmac(key, object, algo="md5", serialize=False, raw=False, **kwargs):
    """Hash-based message authentication code.

    ``algo`` is ``"md5"``, ``"sha1"``, ``"crc32"``, ``"sha256"``, or
    ``"sha512"``. A unique prefix is resolved by ``digest``, not here.
    ``serialize`` defaults to false. ``raw`` returns the digest bytes.
    Extra keywords are passed to both message hashes.
    """
    padded_key = _pad_with_zeros(key, algo)
    inner_key = _xor_raw(padded_key, makeRaw(0x36))
    character_digest = digest(
        inner_key + makeRaw(object),
        algo=algo,
        serialize=serialize,
        **kwargs,
    )
    raw_digest = make_raw_digest(character_digest)
    outer_key = _xor_raw(padded_key, makeRaw(0x5C))
    result = digest(
        outer_key + raw_digest,
        algo=algo,
        serialize=serialize,
        **kwargs,
    )
    if _is_true(raw):
        result = make_raw_digest(result)
    return result


def _pad_with_zeros(key, algo) -> bytes:
    """Pad ``key`` to the block size, hashing it first when it is longer."""
    blocksize = 64
    if _algo_is(algo, "crc32"):
        blocksize = 4
    if _algo_is(algo, "sha512"):
        blocksize = 128
    material = makeRaw(key)
    if len(material) > blocksize:
        # The key hash does not take serialize or the extra keywords.
        material = digest(material, algo=algo, serialize=False, raw=True)
        if _algo_is(algo, "crc32"):
            material = _crc32_substring_key(material)
    extra = blocksize - len(material)
    if extra < 0:
        raise ValueError(_TIMES)
    return makeRaw(list(material) + [0] * extra)


def _crc32_substring_key(raw_digest: bytes) -> bytes:
    """``substring(k, seq(1, 7, 2), seq(2, 8, 2))`` then ``makeRaw(strtoi(k, 16))``.

    ``as.character`` of the four raw bytes is four hex pairs. The starts
    land past the first pair, so the other three strings are empty.
    ``strtoi("", 16)`` is missing, and ``as.raw`` of that missing value is 0.
    """
    parts = [f"{byte:02x}" for byte in raw_digest]
    starts = (1, 3, 5, 7)
    ends = (2, 4, 6, 8)
    if len(parts) == 0:
        raise ValueError(_ZERO)
    width = max(len(parts), len(starts))
    parsed: list[int | float] = []
    for index in range(width):
        piece = _substring(
            parts[index % len(parts)],
            starts[index % len(starts)],
            ends[index % len(ends)],
        )
        value = _strtoi_hex(piece)
        parsed.append(float("nan") if value is None else value)
    return makeRaw(parsed)


def _substring(text: str, first: int, last: int) -> str:
    """One element of R's ``substring``. Indexes are 1-based and inclusive."""
    if first > len(text) or last < 1 or last < first:
        return ""
    start = 0 if first < 1 else first - 1
    return text[start:last]


def _strtoi_hex(text: str) -> int | None:
    """``strtoi(text, 16)`` for a hex pair or the empty string. ``None`` is NA."""
    if text == "":
        return None
    try:
        value = int(text, 16)
    except ValueError:
        return None
    if value > 0x7FFFFFFF:
        return None
    return value


def _algo_is(algo, name: str) -> bool:
    """``algo == name`` as R 4.5 ``if()`` sees it. A long vector is an error."""
    return _one(algo) == name


def _one(value):
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            raise ValueError(_ZERO)
        if len(value) > 1:
            raise ValueError(_LENGTH)
        value = value[0]
    if value is None:
        raise ValueError(_ZERO)
    if isinstance(value, float) and value != value:
        raise ValueError(_MISSING)
    return value


def _is_true(value) -> bool:
    """R's ``if (raw)``."""
    value = _one(value)
    if isinstance(value, str):
        raise ValueError(_NOT_LOGICAL)
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, float):
        return value != 0.0
    raise ValueError(_NOT_LOGICAL)


def _xor_raw(left: bytes, right: bytes) -> bytes:
    """Raw ``xor``. The one-byte pad is recycled across the key."""
    if len(left) == 0 or len(right) == 0:
        return b""
    width = max(len(left), len(right))
    short = min(len(left), len(right))
    if width % short != 0:
        warnings.warn(_RECYCLE, UserWarning, stacklevel=2)
    mixed = bytearray(width)
    for index in range(width):
        mixed[index] = left[index % len(left)] ^ right[index % len(right)]
    return bytes(mixed)
