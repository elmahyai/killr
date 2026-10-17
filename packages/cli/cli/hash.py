"""MD5, SHA, and xxHash digests of text, bytes, and files.

hash_xxhash is XXH3-128 with seed 0, printed high64 then low64.
hash_xxhash64 is XXH3-64 with seed 0. Both come from the digest translation.
"""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

from digest.algos import xxh3_64, xxh3_128
from glue._text import r_character


def _as_text(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, float) and math.isnan(value):
        return "NaN"
    return r_character(value)


def _vector(x) -> list:
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _digest(algorithm: str, data: bytes) -> str:
    return hashlib.new(algorithm, data).hexdigest()


def _hash_text(algorithm: str, x):
    values = _vector(x)
    out = []
    scalar = not isinstance(x, (list, tuple))
    for value in values:
        text = _as_text(value)
        if text is None:
            out.append(None)
        else:
            out.append(_digest(algorithm, text.encode("utf-8")))
    if scalar and len(out) == 1:
        return out[0]
    return out


def _hash_file(algorithm: str, paths):
    values = _vector(paths)
    scalar = not isinstance(paths, (list, tuple))
    out = []
    for path in values:
        text = _as_text(path)
        if text is None:
            out.append(None)
            continue
        file = Path(text).expanduser()
        try:
            resolved = file.resolve(strict=False)
        except OSError:
            resolved = file
        try:
            data = resolved.read_bytes()
        except OSError:
            out.append(None)
            continue
        out.append(_digest(algorithm, data))
    if scalar and len(out) == 1:
        return out[0]
    return out


def hash_md5(x):
    """MD5 hex digest of each string. Missing values stay missing."""

    return _hash_text("md5", x)


def hash_sha1(x):
    """SHA-1 hex digest of each string. Missing values stay missing."""

    return _hash_text("sha1", x)


def hash_sha256(x):
    """SHA-256 hex digest of each string. Missing values stay missing."""

    return _hash_text("sha256", x)


def _raw_bytes(x) -> bytes:
    if isinstance(x, str):
        raise TypeError("hash_raw expects bytes, not a string")
    if isinstance(x, (bytes, bytearray)):
        return bytes(x)
    return bytes(x)


def hash_raw_md5(x) -> str:
    return _digest("md5", _raw_bytes(x))


def hash_raw_sha1(x) -> str:
    return _digest("sha1", _raw_bytes(x))


def hash_raw_sha256(x) -> str:
    return _digest("sha256", _raw_bytes(x))


def hash_file_md5(paths):
    return _hash_file("md5", paths)


def hash_file_sha1(paths):
    return _hash_file("sha1", paths)


def hash_file_sha256(paths):
    return _hash_file("sha256", paths)


def _xxh3_128_hex(data: bytes) -> str:
    high, low = xxh3_128(data)
    return f"{high:016x}{low:016x}"


def _xxh3_64_hex(data: bytes) -> str:
    return f"{xxh3_64(data):016x}"


def _hash_text_fn(fn, x):
    values = _vector(x)
    out = []
    for value in values:
        text = _as_text(value)
        if text is None:
            out.append(None)
        else:
            out.append(fn(text.encode("utf-8")))
    return _one(x, out)


def _hash_file_fn(fn, paths):
    values = _vector(paths)
    out = []
    for path in values:
        text = _as_text(path)
        if text is None:
            out.append(None)
            continue
        file = Path(text).expanduser()
        try:
            resolved = file.resolve(strict=False)
        except OSError:
            resolved = file
        try:
            data = resolved.read_bytes()
        except OSError:
            out.append(None)
            continue
        out.append(fn(data))
    return _one(paths, out)


def _one(x, out):
    if not isinstance(x, (list, tuple)) and len(out) == 1:
        return out[0]
    return out


def hash_xxhash(x):
    """XXH3-128 hex digest of each string. Missing values stay missing."""

    return _hash_text_fn(_xxh3_128_hex, x)


def hash_xxhash64(x):
    """XXH3-64 hex digest of each string. Missing values stay missing."""

    return _hash_text_fn(_xxh3_64_hex, x)


def hash_raw_xxhash(x) -> str:
    return _xxh3_128_hex(_raw_bytes(x))


def hash_raw_xxhash64(x) -> str:
    return _xxh3_64_hex(_raw_bytes(x))


def hash_file_xxhash(paths):
    return _hash_file_fn(_xxh3_128_hex, paths)


def hash_file_xxhash64(paths):
    return _hash_file_fn(_xxh3_64_hex, paths)


def _data_path(name: str) -> Path:
    return Path(__file__).parent / "data" / name


def _lines(name: str) -> list[str]:
    return _data_path(name).read_text(encoding="utf-8").splitlines()


_EMOJIS = None
_ANIMALS = None
_ADJECTIVES = None


def _emojis():
    global _EMOJIS
    if _EMOJIS is None:
        rows = []
        for line in _lines("emojis.tsv"):
            glyph, _, label = line.partition("\t")
            rows.append((glyph, label))
        _EMOJIS = rows
    return _EMOJIS


def _animals() -> list[str]:
    global _ANIMALS
    if _ANIMALS is None:
        _ANIMALS = _lines("animals.txt")
    return _ANIMALS


def _adjectives() -> list[str]:
    global _ADJECTIVES
    if _ADJECTIVES is None:
        _ADJECTIVES = _lines("adjectives.txt")
    return _ADJECTIVES


def _md5_int(digest: str) -> int:
    return sum(int(char, 16) * 16**index for index, char in enumerate(digest[:13]))


def _collapse(values, sep: str):
    if any(value is None for value in values):
        return None
    return sep.join(values)


def _emoji_from_md5(digest: str, size: int) -> dict:
    if not 1 <= size <= 4:
        raise ValueError("size must be from 1 through 4")
    table = _emojis()
    base = len(table)
    ehash = _md5_int(digest) % (base**size)
    digits = []
    while ehash > 0:
        digits.append(ehash % base)
        ehash //= base
    digits.extend([0] * 10)
    digits = digits[:size]
    glyphs = [table[digit][0] for digit in digits]
    names = [table[digit][1] for digit in digits]
    return {"emoji": glyphs, "names": names}


def _animal_from_md5(digest: str, n_adj: int) -> list:
    if not 0 <= n_adj <= 3:
        raise ValueError("n_adj must be from 0 through 3")
    animals = _animals()
    adjectives = _adjectives()
    ehash = _md5_int(digest) % (len(adjectives) ** n_adj * len(animals))
    digits = [ehash % len(animals)]
    ehash //= len(animals)
    while ehash > 0:
        digits.append(ehash % len(adjectives))
        ehash //= len(adjectives)
    digits.extend([0] * 10)
    digits = list(reversed(digits[: n_adj + 1]))
    words = [adjectives[digit] for digit in digits[:-1]]
    words.append(animals[digits[-1]])
    return words


def hash_emoji(x, size: int = 3):
    """Emoji names from the first 13 hex digits of the MD5 digest."""

    values = _vector(x)
    rows = []
    for value in values:
        text = _as_text(value)
        if text is None:
            missing = [None] * size
            rows.append(
                {"hash": None, "emojis": missing, "text": None, "names": missing}
            )
            continue
        emo = _emoji_from_md5(hash_md5(text), size)
        rows.append(
            {
                "hash": _collapse(emo["emoji"], ""),
                "emojis": emo["emoji"],
                "text": _collapse(emo["names"], ", "),
                "names": emo["names"],
            }
        )
    if not isinstance(x, (list, tuple)) and len(rows) == 1:
        return rows[0]
    return rows


def hash_raw_emoji(x, size: int = 3) -> dict:
    emo = _emoji_from_md5(hash_raw_md5(x), size)
    return {
        "hash": _collapse(emo["emoji"], ""),
        "emojis": emo["emoji"],
        "text": _collapse(emo["emoji"], ", "),
        "names": emo["names"],
    }


def hash_animal(x, n_adj: int = 2):
    """Adjective-animal words from the first 13 hex digits of the MD5 digest."""

    values = _vector(x)
    rows = []
    for value in values:
        text = _as_text(value)
        if text is None:
            words = [None] * (n_adj + 1)
            rows.append({"hash": None, "words": words})
            continue
        words = _animal_from_md5(hash_md5(text), n_adj)
        rows.append({"hash": _collapse(words, " "), "words": words})
    if not isinstance(x, (list, tuple)) and len(rows) == 1:
        return rows[0]
    return rows


def hash_raw_animal(x, n_adj: int = 2) -> dict:
    words = _animal_from_md5(hash_raw_md5(x), n_adj)
    return {"hash": _collapse(words, ", "), "words": words}


def _serialized(x, serialize_version: int = 2) -> bytes:
    from digest.serialize import serialize

    if serialize_version != 2:
        raise ValueError("only serialization version 2 is implemented")
    return serialize(x, version=2)[14:]


def hash_obj_md5(x, serialize_version: int = 2) -> str:
    return hash_raw_md5(_serialized(x, serialize_version))


def hash_obj_sha1(x, serialize_version: int = 2) -> str:
    return hash_raw_sha1(_serialized(x, serialize_version))


def hash_obj_sha256(x, serialize_version: int = 2) -> str:
    return hash_raw_sha256(_serialized(x, serialize_version))


def hash_obj_xxhash(x, serialize_version: int = 2) -> str:
    return hash_raw_xxhash(_serialized(x, serialize_version))


def hash_obj_xxhash64(x, serialize_version: int = 2) -> str:
    return hash_raw_xxhash64(_serialized(x, serialize_version))


def hash_obj_emoji(x, size: int = 3, serialize_version: int = 2) -> dict:
    return hash_raw_emoji(_serialized(x, serialize_version), size)


def hash_obj_animal(x, n_adj: int = 2, serialize_version: int = 2) -> dict:
    return hash_raw_animal(_serialized(x, serialize_version), n_adj)
