"""Unicode normalization from stringi.

NFC, NFD, NFKC, and NFKD are the Unicode forms. NFKC_Casefold maps each
character with NFKC, full casefold, and default-ignorable removal, then
applies NFC to the whole string. That is the form ICU uses. Applying
NFKC and casefold to the whole string leaves a different result for
U+037A followed by a combining mark.
"""

from __future__ import annotations

import unicodedata

from stringi._na import NA, is_na

_STR = str

# Unicode 15.1 Default_Ignorable_Code_Point. Python 3.13 and the ICU
# build in stringi 1.8.9 both use Unicode 15.1, so these ranges match
# the installed normalizer.
_DEFAULT_IGNORABLE = (
    (0x00AD, 0x00AD),
    (0x034F, 0x034F),
    (0x061C, 0x061C),
    (0x115F, 0x1160),
    (0x17B4, 0x17B5),
    (0x180B, 0x180F),
    (0x200B, 0x200F),
    (0x202A, 0x202E),
    (0x2060, 0x206F),
    (0x3164, 0x3164),
    (0xFE00, 0xFE0F),
    (0xFEFF, 0xFEFF),
    (0xFFA0, 0xFFA0),
    (0xFFF0, 0xFFF8),
    (0x1BCA0, 0x1BCA3),
    (0x1D173, 0x1D17A),
    (0xE0000, 0xE0FFF),
)

_CF_CHAR: dict[str, str] = {}


def _default_ignorable(code: int) -> bool:
    for start, end in _DEFAULT_IGNORABLE:
        if start <= code <= end:
            return True
        if code < start:
            return False
    return False


def _strip_ignorables(text: str) -> str:
    return "".join(char for char in text if not _default_ignorable(ord(char)))


def _nfkc_cf_char(char: str) -> str:
    cached = _CF_CHAR.get(char)
    if cached is not None:
        return cached
    folded = _strip_ignorables(unicodedata.normalize("NFKC", char).casefold())
    cached = unicodedata.normalize("NFC", folded)
    _CF_CHAR[char] = cached
    return cached


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text)


def _nfd(text: str) -> str:
    return unicodedata.normalize("NFD", text)


def _nfkc(text: str) -> str:
    return unicodedata.normalize("NFKC", text)


def _nfkd(text: str) -> str:
    return unicodedata.normalize("NFKD", text)


def _nfkc_casefold(text: str) -> str:
    if text.isascii():
        return text.lower()
    mapped = "".join(_nfkc_cf_char(char) for char in text)
    return unicodedata.normalize("NFC", mapped)


def _is_nfc(text: str) -> bool:
    return unicodedata.is_normalized("NFC", text)


def _is_nfd(text: str) -> bool:
    return unicodedata.is_normalized("NFD", text)


def _is_nfkc(text: str) -> bool:
    return unicodedata.is_normalized("NFKC", text)


def _is_nfkd(text: str) -> bool:
    return unicodedata.is_normalized("NFKD", text)


def _is_nfkc_casefold(text: str) -> bool:
    return _nfkc_casefold(text) == text


def _one(value: object, func):
    if is_na(value):
        return NA
    if isinstance(value, _STR):
        return func(value)
    raise TypeError("str must be a string or NA")


def _map(value: object, func):
    if isinstance(value, (list, tuple)):
        return [_one(item, func) for item in value]
    return _one(value, func)


def stri_trans_nfc(str):
    """Convert each string to Unicode Normalization Form C."""
    return _map(str, _nfc)


def stri_trans_nfd(str):
    """Convert each string to Unicode Normalization Form D."""
    return _map(str, _nfd)


def stri_trans_nfkd(str):
    """Convert each string to Unicode Normalization Form KD."""
    return _map(str, _nfkd)


def stri_trans_nfkc(str):
    """Convert each string to Unicode Normalization Form KC."""
    return _map(str, _nfkc)


def stri_trans_nfkc_casefold(str):
    """Convert each string to NFKC_Casefold."""
    return _map(str, _nfkc_casefold)


def stri_trans_isnfc(str):
    """Report whether each string is already in NFC."""
    return _map(str, _is_nfc)


def stri_trans_isnfd(str):
    """Report whether each string is already in NFD."""
    return _map(str, _is_nfd)


def stri_trans_isnfkd(str):
    """Report whether each string is already in NFKD."""
    return _map(str, _is_nfkd)


def stri_trans_isnfkc(str):
    """Report whether each string is already in NFKC."""
    return _map(str, _is_nfkc)


def stri_trans_isnfkc_casefold(str):
    """Report whether each string is already in NFKC_Casefold."""
    return _map(str, _is_nfkc_casefold)
