"""Number text from jsonlite's modp_dtoa2 and integer conversion."""

from __future__ import annotations

import math

_POW10 = (1, 10, 100, 1000, 10000, 100000, 1000000, 10000000, 100000000, 1000000000)


def format_integer(value: int) -> str:
    return str(value)


def format_double(value: float, digits: int, *, signif: bool = False, always_decimal: bool = False) -> str:
    if math.isnan(value):
        return "nan"
    if signif:
        precision = math.ceil(min(17, digits))
        return format(value, f".{precision}g")
    if digits == 0 or not (0 <= digits <= 9) or not (1e-5 < abs(value) < 2147483647):
        if math.isinf(value):
            return "inf" if value > 0 else "-inf"
        decimals = math.ceil(min(17, max(1, math.log10(abs(value)) if value else 0) + digits))
        text = format(value, f".{decimals}g")
    else:
        text = _modp_dtoa2(value, digits)
    if always_decimal and text.lstrip("-").isdigit():
        text += ".0"
    return text


def _modp_dtoa2(value: float, prec: int) -> str:
    if value != value:
        return "nan"
    if prec < 0:
        prec = 0
    elif prec > 9:
        prec = 9
    neg = value < 0
    if neg:
        value = -value
    whole = int(value)
    tmp = (value - whole) * _POW10[prec]
    frac = int(tmp)
    diff = tmp - frac
    if diff > 0.5 or (diff == 0.5 and prec > 0 and (frac & 1)) or (diff == 0.5 and prec == 0 and (whole & 1)):
        frac += 1
        if frac >= _POW10[prec]:
            frac = 0
            whole += 1
    if value > 0x7FFFFFFF:
        shown = -value if neg else value
        return format(shown, ".6e")[:12]
    count = prec
    if prec > 0:
        while count > 0 and frac % 10 == 0:
            count -= 1
            frac //= 10
    chars: list[str] = []
    has_decimal = False
    while count > 0:
        count -= 1
        chars.append(chr(48 + (frac % 10)))
        frac //= 10
        has_decimal = True
    if frac > 0:
        whole += 1
    if has_decimal:
        chars.append(".")
    if whole == 0:
        chars.append("0")
    else:
        while True:
            chars.append(chr(48 + (whole % 10)))
            whole //= 10
            if whole == 0:
                break
    if neg:
        chars.append("-")
    return "".join(reversed(chars))
