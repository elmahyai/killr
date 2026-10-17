"""Tagged missing values. The payload is R's NA with one tag byte."""

from __future__ import annotations

import math
import struct

_NA_BITS = 0x7FF00000000007A2


def na_real() -> float:
    return struct.unpack("<d", struct.pack("<Q", _NA_BITS))[0]


def make_tagged_na(tag: str) -> float:
    if tag is None or tag == "":
        byte = 0
    else:
        byte = tag.encode("utf-8")[0]
    bits = _NA_BITS
    bits &= ~(0xFF << 32)
    bits |= byte << 32
    return struct.unpack("<d", struct.pack("<Q", bits))[0]


def tag_byte(value: float) -> int:
    bits = struct.unpack("<Q", struct.pack("<d", float(value)))[0]
    return (bits >> 32) & 0xFF


def is_na_double(value) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    return False


def tagged_na(*tags: str) -> list[float]:
    """Build one tagged missing value for each one-character tag."""
    if not tags:
        raise ValueError("`x` must be a character vector")
    out = []
    for tag in tags:
        if tag is None:
            out.append(make_tagged_na(""))
            continue
        if not isinstance(tag, str):
            raise ValueError("`x` must be a character vector")
        out.append(make_tagged_na(tag))
    return out


def na_tag(x) -> list:
    """The tag letter of each tagged missing value, or None."""
    values = _values(x)
    if _storage(x) not in (None, "double"):
        raise ValueError("`x` must be a double vector")
    out = []
    for value in values:
        if not isinstance(value, float) or not math.isnan(value):
            out.append(None)
            continue
        byte = tag_byte(value)
        out.append(None if byte == 0 else chr(byte))
    return out


def is_tagged_na(x, tag=None) -> list[bool]:
    """True where a value is a tagged missing value."""
    values = _values(x)
    if _storage(x) not in (None, "double"):
        return [False] * len(values)
    if tag is not None:
        if not isinstance(tag, str):
            raise ValueError("`tag` must be NULL or a character vector")
        if len(tag) == 0:
            wanted = 0
        else:
            wanted = tag.encode("utf-8")[0]
    else:
        wanted = None
    out = []
    for value in values:
        if not isinstance(value, float) or not math.isnan(value):
            out.append(False)
            continue
        byte = tag_byte(value)
        if byte == 0:
            out.append(False)
        elif wanted is None:
            out.append(True)
        else:
            out.append(byte == wanted)
    return out


def format_tagged_na(x, digits: int = 7) -> list[str]:
    """Format numbers, writing tagged missing values as NA(a)."""
    values = _values(x)
    tags = is_tagged_na(x)
    letters = na_tag(x)
    rendered = []
    for value, tagged, letter in zip(values, tags, letters):
        if tagged:
            rendered.append(f"NA({letter})")
        elif is_na_double(value):
            rendered.append("NA")
        else:
            rendered.append(_format_number(value, digits))
    width = max((len(item) for item in rendered), default=0)
    return [item.rjust(width) for item in rendered]


def print_tagged_na(x, digits: int = 7) -> None:
    """Print tagged missing values as NA(a)."""
    rendered = format_tagged_na(x, digits=digits)
    print("[1] " + " ".join(rendered))


def _format_number(value, digits: int) -> str:
    if isinstance(value, float) and value.is_integer() and abs(value) < 1e15:
        return str(int(value))
    text = format(value, f".{digits}g")
    return text


def _values(x):
    if hasattr(x, "values"):
        return list(x.values)
    if isinstance(x, (list, tuple)):
        return list(x)
    return [x]


def _storage(x):
    if hasattr(x, "storage"):
        return x.storage
    if isinstance(x, (list, tuple)) and x and isinstance(x[0], str):
        return "string"
    return "double"
