"""Code-point length, byte length, emptiness, and display width.

These follow stringi 1.8.9. A missing character is ``stringi._na.NA``.
The string ``"NA"`` is a real string. An empty string is empty.
"""

from __future__ import annotations

import math
import unicodedata
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext

from stringi._na import NA, is_na

_STRING = str
_DECIMAL = Context(prec=1000, rounding=ROUND_HALF_EVEN, Emin=-999999, Emax=999999)
_INT_MIN = -2147483647
_INT_MAX = 2147483647

# Hangul syllable type V (vowel jamo) and T (trailing jamo). Width 0.
_HANGUL_VOWEL = ((0x1160, 0x11A7), (0xD7B0, 0xD7C6))
_HANGUL_TRAIL = ((0x11A8, 0x11FF), (0xD7CB, 0xD7FB))
_EMOJI_MODIFIER = ((0x1F3FB, 0x1F3FF),)

# Unicode 16 assignments that Python 3.13 unicodedata (15.1) does not know.
# Checked against stringi 1.8.9 / ICU 76.
_U16_MN = (
    (0x897, 0x897),
    (0x10D69, 0x10D6D),
    (0x10EFC, 0x10EFC),
    (0x113BB, 0x113C0),
    (0x113CE, 0x113CE),
    (0x113D0, 0x113D0),
    (0x113D2, 0x113D2),
    (0x113E1, 0x113E2),
    (0x11F5A, 0x11F5A),
    (0x1611E, 0x16129),
    (0x1612D, 0x1612F),
    (0x1E5EE, 0x1E5EF),
)
_U16_SO = (
    (0x2427, 0x2429),
    (0x31E4, 0x31E5),
    (0x1CC00, 0x1CCEF),
    (0x1CD00, 0x1CEB3),
    (0x1F8B2, 0x1F8BB),
    (0x1F8C0, 0x1F8C1),
    (0x1FA89, 0x1FA89),
    (0x1FA8F, 0x1FA8F),
    (0x1FABE, 0x1FABE),
    (0x1FAC6, 0x1FAC6),
    (0x1FADC, 0x1FADC),
    (0x1FADF, 0x1FADF),
    (0x1FAE9, 0x1FAE9),
    (0x1FBCB, 0x1FBEF),
)
_U16_WIDE = (
    (0x31E4, 0x31E5),
    (0x18CFF, 0x18CFF),
    (0x1D360, 0x1D376),
    (0x1FA89, 0x1FA89),
    (0x1FA8F, 0x1FA8F),
    (0x1FABE, 0x1FABE),
    (0x1FAC6, 0x1FAC6),
    (0x1FADC, 0x1FADC),
    (0x1FADF, 0x1FADF),
    (0x1FAE9, 0x1FAE9),
)

# Emoji_Presentation, Unicode 15.1 plus the Unicode 16 additions ICU 76 uses.
_EMOJI_PRESENTATION = (
    (0x231A, 0x231B), (0x23E9, 0x23EC), (0x23F0, 0x23F0), (0x23F3, 0x23F3),
    (0x25FD, 0x25FE), (0x2614, 0x2615), (0x2648, 0x2653), (0x267F, 0x267F),
    (0x2693, 0x2693), (0x26A1, 0x26A1), (0x26AA, 0x26AB), (0x26BD, 0x26BE),
    (0x26C4, 0x26C5), (0x26CE, 0x26CE), (0x26D4, 0x26D4), (0x26EA, 0x26EA),
    (0x26F2, 0x26F3), (0x26F5, 0x26F5), (0x26FA, 0x26FA), (0x26FD, 0x26FD),
    (0x2705, 0x2705), (0x270A, 0x270B), (0x2728, 0x2728), (0x274C, 0x274C),
    (0x274E, 0x274E), (0x2753, 0x2755), (0x2757, 0x2757), (0x2795, 0x2797),
    (0x27B0, 0x27B0), (0x27BF, 0x27BF), (0x2B1B, 0x2B1C), (0x2B50, 0x2B50),
    (0x2B55, 0x2B55), (0x1F004, 0x1F004), (0x1F0CF, 0x1F0CF), (0x1F18E, 0x1F18E),
    (0x1F191, 0x1F19A), (0x1F1E6, 0x1F1FF), (0x1F201, 0x1F201), (0x1F21A, 0x1F21A),
    (0x1F22F, 0x1F22F), (0x1F232, 0x1F236), (0x1F238, 0x1F23A), (0x1F250, 0x1F251),
    (0x1F300, 0x1F320), (0x1F32D, 0x1F335), (0x1F337, 0x1F37C), (0x1F37E, 0x1F393),
    (0x1F3A0, 0x1F3CA), (0x1F3CF, 0x1F3D3), (0x1F3E0, 0x1F3F0), (0x1F3F4, 0x1F3F4),
    (0x1F3F8, 0x1F43E), (0x1F440, 0x1F440), (0x1F442, 0x1F4FC), (0x1F4FF, 0x1F53D),
    (0x1F54B, 0x1F54E), (0x1F550, 0x1F567), (0x1F57A, 0x1F57A), (0x1F595, 0x1F596),
    (0x1F5A4, 0x1F5A4), (0x1F5FB, 0x1F64F), (0x1F680, 0x1F6C5), (0x1F6CC, 0x1F6CC),
    (0x1F6D0, 0x1F6D2), (0x1F6D5, 0x1F6D7), (0x1F6DC, 0x1F6DF), (0x1F6EB, 0x1F6EC),
    (0x1F6F4, 0x1F6FC), (0x1F7E0, 0x1F7EB), (0x1F7F0, 0x1F7F0), (0x1F90C, 0x1F93A),
    (0x1F93C, 0x1F945), (0x1F947, 0x1F9FF), (0x1FA70, 0x1FA7C), (0x1FA80, 0x1FA89),
    (0x1FA8F, 0x1FAC6), (0x1FACE, 0x1FADC), (0x1FADF, 0x1FAE9), (0x1FAF0, 0x1FAF8),
)

# After U+200D these count as width 0 even when they are not emoji presentation.
_ZWJ_FOLLOW = frozenset({
    0x2640, 0x2642, 0x26A7, 0x2695, 0x2696,
    0x1F5E8, 0x1F32B, 0x2708, 0x2764, 0x2744, 0x2620,
})


def _in_ranges(cp: int, ranges: tuple[tuple[int, int], ...]) -> bool:
    lo = 0
    hi = len(ranges) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        start, end = ranges[mid]
        if cp < start:
            hi = mid - 1
        elif cp > end:
            lo = mid + 1
        else:
            return True
    return False


def _category(cp: int) -> _STRING:
    if _in_ranges(cp, _U16_MN):
        return "Mn"
    if cp == 0x1171E:
        return "Mc"
    if _in_ranges(cp, _U16_SO):
        return "So"
    return unicodedata.category(chr(cp))


def _east_asian_width(cp: int) -> _STRING:
    if _in_ranges(cp, _U16_WIDE):
        return "W"
    return unicodedata.east_asian_width(chr(cp))


def _width_char(cp: int) -> int:
    """Width of one code point, ignoring the previous character."""

    if cp == 0x00AD:
        return 1
    if cp == 0x200B:
        return 0
    category = _category(cp)
    if category in ("Me", "Mn", "Cf", "Cc"):
        return 0
    if _in_ranges(cp, _HANGUL_VOWEL) or _in_ranges(cp, _HANGUL_TRAIL):
        return 0
    if 0xFE00 <= cp <= 0xFE0F:
        return 0
    if _in_ranges(cp, _EMOJI_MODIFIER):
        return 0
    east = _east_asian_width(cp)
    if east in ("F", "W"):
        return 2
    if category == "So":
        return 2
    if east == "N" and _in_ranges(cp, _EMOJI_PRESENTATION):
        return 2
    return 1


def _width_string(text: _STRING) -> int:
    total = 0
    previous = 0
    reset = True
    for char in text:
        current = ord(char)
        if reset:
            previous = 0
            reset = False
        if previous == 0x200D and (
            _in_ranges(current, _EMOJI_MODIFIER)
            or _in_ranges(current, _EMOJI_PRESENTATION)
            or current in _ZWJ_FOLLOW
        ):
            width = 0
        elif 0x1F1E6 <= previous <= 0x1F1FF and 0x1F1E6 <= current <= 0x1F1FF:
            reset = True
            width = 0
        else:
            width = _width_char(current)
        total += width
        previous = current
    return total


def _round_sig(value: Decimal, digits: int) -> Decimal:
    if value == 0:
        return Decimal(0)
    adjusted = value.adjusted()
    quantum = Decimal("1e{}".format(adjusted - (digits - 1)))
    rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    if rounded != 0 and rounded.adjusted() > adjusted:
        adjusted = rounded.adjusted()
        quantum = Decimal("1e{}".format(adjusted - (digits - 1)))
        rounded = value.quantize(quantum, rounding=ROUND_HALF_EVEN)
    return rounded


def _fixed_and_sci(rounded: Decimal) -> tuple[_STRING, _STRING]:
    if rounded == 0:
        return "0", "0e+00"
    text = format(rounded, "f")
    if "." in text:
        whole, frac = text.split(".")
        digits = (whole + frac).lstrip("0").rstrip("0") or "0"
    else:
        digits = text.lstrip("0").rstrip("0") or "0"
    adjusted = rounded.adjusted()
    if adjusted >= 0:
        if adjusted + 1 >= len(digits):
            fixed = digits + ("0" * (adjusted + 1 - len(digits)))
        else:
            fixed = digits[: adjusted + 1] + "." + digits[adjusted + 1 :]
    else:
        fixed = "0." + ("0" * (-adjusted - 1)) + digits
    mantissa = digits if len(digits) == 1 else digits[0] + "." + digits[1:]
    return fixed, f"{mantissa}e{adjusted:+03d}"


def _character_double(value: float) -> _STRING:
    """R's as.character for a double: 15 significant digits, shorter scientific form."""

    if math.isnan(value):
        return "NaN"
    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = math.copysign(1.0, value) < 0
    magnitude = abs(value)
    digits = 16 if 1e15 <= magnitude < 1e16 else 15
    with localcontext(_DECIMAL):
        rounded = _round_sig(Decimal(magnitude), digits)
        fixed, scientific = _fixed_and_sci(rounded)
    if negative:
        fixed = "-" + fixed
        scientific = "-" + scientific
    if magnitude.is_integer():
        exact = str(int(magnitude))
        if negative:
            exact = "-" + exact
        if len(exact) <= len(scientific):
            return exact
    if len(scientific) < len(fixed):
        return scientific
    return fixed


def _character_integer(value: int) -> _STRING:
    if _INT_MIN <= value <= _INT_MAX:
        return _STRING(value)
    return _character_double(float(value))


def _character_complex(value: complex) -> _STRING:
    real = _character_double(float(value.real))
    imag = _character_double(float(value.imag))
    if imag.startswith("-"):
        return real + imag + "i"
    return real + "+" + imag + "i"


def _mode(items: list) -> _STRING:
    if any(is_na(item) or isinstance(item, _STRING) for item in items):
        return "character"
    if any(isinstance(item, complex) for item in items):
        return "complex"
    if any(isinstance(item, float) for item in items):
        return "double"
    if any(isinstance(item, int) and not isinstance(item, bool) for item in items):
        return "integer"
    return "logical"


def _coerce_one(value, mode: _STRING):
    if is_na(value):
        return NA
    if isinstance(value, _STRING):
        if mode != "character":
            raise TypeError("str must be a character vector or an object coercible to character")
        return value
    if isinstance(value, bool):
        if mode in ("character", "logical"):
            return "TRUE" if value else "FALSE"
        if mode == "integer":
            return _character_integer(int(value))
        if mode == "double":
            return _character_double(float(value))
        return _character_complex(complex(int(value)))
    if isinstance(value, int):
        if mode in ("character", "integer"):
            return _character_integer(value)
        if mode == "double":
            return _character_double(float(value))
        return _character_complex(complex(value))
    if isinstance(value, float):
        if mode in ("character", "double"):
            return _character_double(value)
        return _character_complex(complex(value))
    if isinstance(value, complex):
        return _character_complex(value)
    raise TypeError("str must be a character vector or an object coercible to character")


def _prepare(value):
    """Return character elements and whether the input was a single value.

    ``None`` is R's NULL, an empty vector. A list or tuple is one vector.
    R's ``c()`` promotes a mixed vector before coercion; a list does the same.
    """

    if value is None:
        return [], True
    if isinstance(value, (bytes, bytearray)):
        raise TypeError("str must be a character vector or an object coercible to character")
    if isinstance(value, (list, tuple)):
        items = list(value)
        scalar = False
    else:
        items = [value]
        scalar = True
    if any(item is None for item in items):
        raise TypeError("a missing character is stringi._na.NA, not None")
    mode = _mode(items) if items else "logical"
    return [_coerce_one(item, mode) for item in items], scalar


def _map(value, func):
    texts, scalar = _prepare(value)
    if value is None:
        return []
    result = [func(text) for text in texts]
    if scalar:
        return result[0]
    return result


def _length_one(text):
    if is_na(text):
        return NA
    return len(text)


def _bytes_one(text):
    if is_na(text):
        return NA
    try:
        return len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("invalid UTF-8 byte sequence detected") from exc


def _empty_one(text):
    if is_na(text):
        return NA
    return text == ""


def _width_one(text):
    if is_na(text):
        return NA
    return _width_string(text)


def stri_length(str):
    """Count Unicode code points in each string.

    Numbers, logicals, and complex values are coerced the way R's
    ``as.character`` coerces them. ``NA`` stays missing.
    """

    return _map(str, _length_one)


def stri_numbytes(str):
    """Count UTF-8 bytes in each string, not counting a trailing NUL.

    ``NA`` stays missing. ``stri_numbytes("\\u0105")`` is 2.
    """

    return _map(str, _bytes_one)


def stri_isempty(str):
    """True when a string is empty, missing when the string is missing."""

    return _map(str, _empty_one)


def stri_width(str):
    """Approximate the monospaced columns ``cat`` would use.

    Me, Mn, Cf, and Cc have width 0, as do Hangul medial vowels, Hangul
    final consonants, and U+200B. East Asian wide and fullwidth characters
    have width 2. Most emoji and general category So have width 2. U+00AD
    has width 1. A regional-indicator pair and a ZWJ emoji sequence add
    width only for the first visible character.
    """

    return _map(str, _width_one)
