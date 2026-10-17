"""Jenkins one-at-a-time hash of each string, as a signed 32-bit integer.

R stores the unsigned hash in an integer vector, so values at or above
``2^31`` come back negative. ``seed`` follows ``as.integer`` and is then
read as a ``uint32``. ``None`` in ``x`` is ``NA_character_``: ``CHAR`` of
that string is the bytes of ``"NA"``.
"""

from __future__ import annotations

import math
import numbers
import re
import warnings

_INT_MIN = -2147483648
_INT_MAX = 2147483647
_NA = _INT_MIN
_MASK = 0xFFFFFFFF

_HEX_RE = re.compile(
    r"^([+-]?)0[xX]((?:[0-9A-Fa-f]+\.?[0-9A-Fa-f]*|\.[0-9A-Fa-f]+))"
    r"(?:[pP]([+-]?\d+))?$"
)
_DEC_RE = re.compile(
    r"^[+-]?(?:(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|inf(?:inity)?|nan)$",
    re.IGNORECASE,
)


def digest2int(x, seed=0):
    """Hash each string in ``x`` with Jenkins's one-at-a-time hash.

    ``x`` is a string or a list of strings. Anything else raises
    ``ValueError`` with R's message. A length-1 input returns a
    one-element list. ``seed`` is ``as.integer(seed)``; only its first
    value is the starting ``uint32``.
    """
    texts = _character_bytes(x)
    start, flags = _integer_seed(seed)
    if flags["coercion"]:
        warnings.warn("NAs introduced by coercion", UserWarning, stacklevel=2)
    if flags["range"]:
        warnings.warn(
            "NAs introduced by coercion to integer range",
            UserWarning,
            stacklevel=2,
        )
    if flags["imag"]:
        warnings.warn(
            "imaginary parts discarded in coercion",
            UserWarning,
            stacklevel=2,
        )
    return [_jenkins(text, start) for text in texts]


def _character_bytes(x) -> list[bytes]:
    if isinstance(x, str):
        return [_utf8(x)]
    if isinstance(x, (list, tuple)):
        texts = []
        for item in x:
            if item is None:
                texts.append(b"NA")
            elif isinstance(item, str):
                texts.append(_utf8(item))
            else:
                raise ValueError("invalid input - should be character vector")
        return texts
    raise ValueError("invalid input - should be character vector")


def _utf8(text: str) -> bytes:
    return text.encode("utf-8")


def _jenkins(key: bytes, seed: int) -> int:
    """One-at-a-time hash. ``char`` is signed, and a zero byte ends the key."""
    hash_ = seed & _MASK
    for byte in key:
        if byte == 0:
            break
        signed = byte - 256 if byte > 127 else byte
        hash_ = (hash_ + signed) & _MASK
        hash_ = (hash_ + ((hash_ << 10) & _MASK)) & _MASK
        hash_ ^= hash_ >> 6
    hash_ = (hash_ + ((hash_ << 3) & _MASK)) & _MASK
    hash_ ^= hash_ >> 11
    hash_ = (hash_ + ((hash_ << 15) & _MASK)) & _MASK
    if hash_ >= 0x80000000:
        return hash_ - 0x100000000
    return hash_


def _integer_seed(seed) -> tuple[int, dict[str, bool]]:
    values: list[int] = []
    flags = {"coercion": False, "range": False, "imag": False}
    _append_integers(seed, values, flags, null_is_empty=True)
    if not values:
        return _NA & _MASK, flags
    return values[0] & _MASK, flags


def _append_integers(value, values: list[int], flags: dict[str, bool], null_is_empty: bool) -> None:
    if value is None:
        if not null_is_empty:
            values.append(_NA)
        return
    if isinstance(value, (list, tuple)):
        for item in value:
            _append_integers(item, values, flags, null_is_empty=False)
        return
    if isinstance(value, (bytes, bytearray)):
        values.extend(value)
        return
    if isinstance(value, bool):
        values.append(1 if value else 0)
        return
    if isinstance(value, str):
        values.append(_string_to_int(value, flags))
        return
    if isinstance(value, numbers.Integral):
        values.append(_int_to_int(int(value), flags))
        return
    if isinstance(value, numbers.Real):
        values.append(_float_to_int(float(value), flags))
        return
    if isinstance(value, numbers.Complex):
        values.append(_complex_to_int(value, flags))
        return
    raise ValueError(
        f"cannot coerce type '{type(value).__name__}' to vector of type 'integer'"
    )


def _int_to_int(value: int, flags: dict[str, bool]) -> int:
    if value < _INT_MIN or value > _INT_MAX:
        flags["range"] = True
        return _NA
    return value


def _float_to_int(value: float, flags: dict[str, bool]) -> int:
    if math.isnan(value):
        return _NA
    if math.isinf(value) or value >= 2147483648.0 or value <= -2147483648.0:
        flags["range"] = True
        return _NA
    return math.trunc(value)


def _complex_to_int(value: complex, flags: dict[str, bool]) -> int:
    real = float(value.real)
    imag = float(value.imag)
    if math.isnan(real) or math.isnan(imag):
        return _NA
    if math.isinf(real) or real > 2147483648.0 or real <= -2147483648.0:
        flags["range"] = True
        return _NA
    if imag != 0.0:
        flags["imag"] = True
    if real == 2147483648.0:
        return _NA
    return math.trunc(real)


def _string_to_int(text: str, flags: dict[str, bool]) -> int:
    stripped = text.strip()
    if stripped == "":
        return _NA
    if re.match(r"^[+-]?0[xX]", stripped):
        parsed = _hex_value(stripped)
        if parsed is None:
            flags["coercion"] = True
            return _NA
        return _float_to_int(parsed, flags)
    if _DEC_RE.fullmatch(stripped):
        return _float_to_int(float(stripped), flags)
    flags["coercion"] = True
    return _NA


def _hex_value(text: str) -> float | None:
    match = _HEX_RE.fullmatch(text)
    if match is None:
        return None
    sign, body, exponent = match.groups()
    if "." in body:
        whole, frac = body.split(".", 1)
        digits = whole + frac
        frac_len = len(frac)
    else:
        digits = body
        frac_len = 0
    if digits == "":
        return None
    value = int(digits, 16) / float(16**frac_len)
    if exponent is not None:
        power = int(exponent)
        if power > 1024:
            value = math.inf
        elif power < -1024:
            value = 0.0
        else:
            value *= 2.0**power
    if sign == "-":
        value = -value
    return value
