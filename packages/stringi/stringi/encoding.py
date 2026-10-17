"""Character encoding conversion, detection, and defaults.

These follow stringi 1.8.9 on ICU 76. A missing character is
``stringi._na.NA``. The string ``"NA"`` is text. A ``bytes`` object is an
R raw vector. A list of byte strings, or of lists of integers 0..255, is a
list of raw vectors. ``from_`` is R's ``from``.

``stri_conv`` is the same function object as ``stri_encode``.
"""

from __future__ import annotations

import ctypes
import math
import sys
import warnings
from ctypes import POINTER, byref, c_char_p, c_int32, c_uint16, c_void_p

import icu

from stringi._na import NA, is_na
from stringi.length import _prepare

_ICU_MAJOR = icu.ICU_VERSION.split(".", 1)[0]
_LIB = ctypes.CDLL(f"libicuuc.so.{_ICU_MAJOR}")
_U_FAILURE = 0
_U_BUFFER_OVERFLOW = 15
_U_FILE_ACCESS = 4
_NA_INTEGER = -2147483648
_UTF8_NAMES = {"UTF-8", "UTF-16", "UTF-16BE", "UTF-16LE", "UTF-32", "UTF-32BE", "UTF-32LE"}
_FILE_ACCESS = "The requested ICU resource file cannot be found. (U_FILE_ACCESS_ERROR)"
_UTF8_LOCKED_WARNING = (
    "system ICU assumes that the default character set is always UTF-8, "
    "and hence this function has no effect"
)
_DETECT2_WARNING = (
    "stri_enc_detect2 is deprecated and will be removed in a future release of 'stringi'."
)
_UNCONVERTIBLE = "the Unicode code point \\U%08x cannot be converted to destination encoding"
_BAD_INPUT = "input data \\x%s in the current source encoding could not be converted to Unicode"
_BAD_CODE = "invalid Unicode code point \\U%08x"

_catalog_cache = None
_info_cache: dict = {}
_profile_cache: dict = {}
_utf8_lock = None
_default_name = None


def _warn(message: str) -> None:
    warnings.warn(message, UserWarning, stacklevel=3)


def _bind(name: str, restype, *argtypes) -> ctypes._FuncPtr:
    fn = getattr(_LIB, f"{name}_{_ICU_MAJOR}")
    fn.restype = restype
    fn.argtypes = list(argtypes)
    return fn


_ucnv_open = _bind("ucnv_open", c_void_p, c_char_p, POINTER(c_int32))
_ucnv_close = _bind("ucnv_close", None, c_void_p)
_ucnv_reset = _bind("ucnv_reset", None, c_void_p)
_ucnv_get_name = _bind("ucnv_getName", c_char_p, c_void_p, POINTER(c_int32))
_ucnv_get_min = _bind("ucnv_getMinCharSize", ctypes.c_int8, c_void_p)
_ucnv_get_max = _bind("ucnv_getMaxCharSize", ctypes.c_int8, c_void_p)
_ucnv_count_available = _bind("ucnv_countAvailable", c_int32)
_ucnv_available_name = _bind("ucnv_getAvailableName", c_char_p, c_int32)
_ucnv_count_aliases = _bind("ucnv_countAliases", c_int32, c_char_p, POINTER(c_int32))
_ucnv_get_alias = _bind("ucnv_getAlias", c_char_p, c_char_p, ctypes.c_uint16, POINTER(c_int32))
_ucnv_get_default = _bind("ucnv_getDefaultName", c_char_p)
_ucnv_set_default = _bind("ucnv_setDefaultName", None, c_char_p)
_ucnv_to_uchars = _bind(
    "ucnv_toUChars", c_int32, c_void_p, POINTER(c_uint16), c_int32, c_char_p, c_int32, POINTER(c_int32)
)
_ucnv_from_uchars = _bind(
    "ucnv_fromUChars", c_int32, c_void_p, c_char_p, c_int32, POINTER(c_uint16), c_int32, POINTER(c_int32)
)
_ucnv_next = _bind(
    "ucnv_getNextUChar", c_int32, c_void_p, POINTER(c_char_p), c_char_p, POINTER(c_int32)
)
_u_error_name = _bind("u_errorName", c_char_p, c_int32)


class _ICUError(ValueError):
    pass


def _fail_status(status: int) -> None:
    if status <= _U_FAILURE:
        return
    if status == _U_FILE_ACCESS:
        raise _ICUError(_FILE_ACCESS)
    err = _u_error_name(status)
    label = err.decode() if err else str(status)
    raise _ICUError(f"ICU conversion failed ({label})")


def _open(encoding: str | None):
    err = c_int32(0)
    token = None if encoding is None else encoding.encode("utf-8")
    converter = _ucnv_open(token, byref(err))
    if err.value > _U_FAILURE or not converter:
        _fail_status(err.value or _U_FILE_ACCESS)
    return converter


def _icu_name(encoding: str | None) -> str:
    converter = _open(encoding)
    try:
        err = c_int32(0)
        name = _ucnv_get_name(converter, byref(err))
        _fail_status(err.value)
        return name.decode()
    finally:
        _ucnv_close(converter)


def _limits(encoding: str | None) -> tuple[int, int, str]:
    converter = _open(encoding)
    try:
        err = c_int32(0)
        name = _ucnv_get_name(converter, byref(err))
        _fail_status(err.value)
        return int(_ucnv_get_min(converter)), int(_ucnv_get_max(converter)), name.decode()
    finally:
        _ucnv_close(converter)


def _default_icu_name() -> str:
    global _default_name
    if _default_name is None:
        name = _ucnv_get_default()
        _default_name = name.decode() if name else "UTF-8"
    return _default_name


def _utf8_locked() -> bool:
    global _utf8_lock
    if _utf8_lock is None:
        current = _ucnv_get_default()
        _ucnv_set_default(b"ISO-8859-2")
        after = _ucnv_get_default()
        _ucnv_set_default(current)
        _utf8_lock = after == current
    return _utf8_lock


def _standards() -> list[str]:
    names = [item for item in icu.UnicodeString.getAvailableStandards() if item]
    # stringi drops the last ucnv_countStandards() entry. That entry is empty.
    return names


def _standard_name(canonical: str, standard: str):
    try:
        name = icu.UnicodeString.getStandardEncoding(canonical, standard)
    except icu.ICUError:
        return None
    return name or None


def _friendly(canonical: str) -> str:
    for standard in ("MIME", "JAVA"):
        name = _standard_name(canonical, standard)
        if name:
            return name
    return canonical


def _decode(raw: bytes, encoding: str | None) -> str:
    converter = _open(encoding)
    try:
        if not raw:
            return ""
        err = c_int32(0)
        needed = _ucnv_to_uchars(converter, None, 0, raw, len(raw), byref(err))
        _ucnv_reset(converter)
        dest = (c_uint16 * (needed + 1))()
        err = c_int32(0)
        count = _ucnv_to_uchars(converter, dest, needed + 1, raw, len(raw), byref(err))
        if err.value > _U_FAILURE and err.value != _U_BUFFER_OVERFLOW:
            _fail_status(err.value)
        return memoryview(dest)[:count].tobytes().decode("utf-16-le")
    finally:
        _ucnv_close(converter)


def _encode_unicode(text: str, encoding: str | None) -> bytes:
    if encoding is None:
        encoding = _default_icu_name()
    try:
        return bytes(icu.UnicodeString(text).encode(encoding))
    except icu.ICUError as exc:
        if getattr(exc, "code", None) == _U_FILE_ACCESS or "error code: 4" in str(exc):
            raise _ICUError(_FILE_ACCESS) from exc
        raise


def _signed_hex(byte: int) -> str:
    if byte >= 128:
        byte -= 256
    return f"{byte & 0xFFFFFFFF:02x}"


def _warn_bad_utf8(raw: bytes) -> None:
    index = 0
    while index < len(raw):
        try:
            raw[index:].decode("utf-8")
            return
        except UnicodeDecodeError as exc:
            start = index + exc.start
            end = index + exc.end
            if end <= start:
                end = start + 1
            for position in range(start, end):
                _warn(_BAD_INPUT % _signed_hex(raw[position]))
            index = end


def _warn_unconvertible(text: str, encoding: str | None) -> None:
    name = _icu_name(encoding)
    if name in _UTF8_NAMES or name == "US-ASCII" and all(ord(char) < 128 for char in text):
        if name in _UTF8_NAMES:
            return
    if name in _UTF8_NAMES:
        return
    for char in text:
        produced = _encode_unicode(char, encoding)
        if _decode(produced, encoding) != char:
            _warn(_UNCONVERTIBLE % ord(char))


def _output_mark(icu_name: str) -> str:
    if icu_name in ("US-ASCII", "UTF-8"):
        return "utf-8"
    if icu_name in ("ISO-8859-1", "latin1"):
        return "latin1"
    if icu_name == _default_icu_name():
        return "native"
    return "bytes"


def _present(raw: bytes, icu_name: str):
    mark = _output_mark(icu_name)
    if mark == "latin1":
        return raw.decode("latin-1")
    if mark in ("utf-8", "native"):
        return raw.decode("utf-8")
    return raw


def _one_string(value, name: str, *, allow_default: bool) -> str | None:
    if value is None:
        if allow_default:
            return None
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if isinstance(value, (bytes, bytearray)):
        texts = [f"{byte:02x}" for byte in value]
    else:
        texts, _ = _prepare(value)
    if not texts:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if len(texts) > 1:
        _warn(
            f"argument `{name}` should be a single character string; "
            "only the first element is used"
        )
    text = texts[0]
    if is_na(text):
        raise ValueError(f"missing values in argument `{name}` is not supported")
    if text == "":
        if allow_default:
            return None
        raise ValueError("incorrect character encoding identifier")
    return text


def _as_logical(value):
    if is_na(value) or value is None:
        return NA
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value != 0
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            _warn("NAs introduced by coercion")
            return NA
        return value != 0
    if isinstance(value, str):
        if value in ("TRUE", "T"):
            return True
        if value in ("FALSE", "F"):
            return False
        _warn("NAs introduced by coercion")
        return NA
    raise TypeError("argument should be a logical vector (or an object coercible to)")


def _one_logical(value, name: str, *, allow_na: bool):
    if value is None:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    items = list(value) if isinstance(value, (list, tuple)) else [value]
    if not items:
        raise ValueError(f"argument `{name}` should be a non-empty vector")
    if len(items) > 1:
        _warn(
            f"argument `{name}` should be a single logical value; "
            "only the first element is used"
        )
    flag = _as_logical(items[0])
    if is_na(flag) and not allow_na:
        raise ValueError(f"missing values in argument `{name}` is not supported")
    return flag


def _logical_vector(value, name: str) -> list:
    if value is None:
        return []
    items = list(value) if isinstance(value, (list, tuple)) else [value]
    return [_as_logical(item) for item in items]


def _is_true(value) -> bool:
    if value is True:
        return True
    if isinstance(value, (list, tuple)) and len(value) == 1 and value[0] is True:
        return True
    return False


def _finish(items: list, scalar: bool):
    if scalar and len(items) == 1:
        return items[0]
    return items


def _text_bytes(text):
    if is_na(text):
        return NA
    return text.encode("utf-8")


def _raw_element(value) -> bytes | object:
    if value is None or is_na(value):
        return NA
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    return bytes(int(item) & 0xFF for item in value)


def _raw_shaped(value) -> bool:
    if isinstance(value, (bytes, bytearray)):
        return True
    if value is None or is_na(value):
        return True
    if isinstance(value, (list, tuple)) and not isinstance(value, (str, bytes, bytearray)):
        return all(isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255 for item in value)
    return False


def _classify(value):
    """Return kind, payload, scalar.

    kind is ``null``, ``raw``, ``raw-list``, or ``character``.
    Payload items are ``bytes`` or ``NA`` for raw kinds, and strings or
    ``NA`` for characters.
    """

    if value is None:
        return "null", [NA], True
    if isinstance(value, (bytes, bytearray)):
        return "raw", [bytes(value)], True
    if isinstance(value, (list, tuple)):
        if len(value) == 0:
            return "character", [], False
        if all(_raw_shaped(item) for item in value) and any(
            item is None or isinstance(item, (bytes, bytearray, list, tuple))
            for item in value
        ):
            if any(not _raw_shaped(item) for item in value):
                raise ValueError("all elements in `str` should be a raw vectors")
            return "raw-list", [_raw_element(item) for item in value], False
        if any(isinstance(item, (bytes, bytearray)) for item in value):
            raise ValueError("all elements in `str` should be a raw vectors")
        texts, _ = _prepare(list(value))
        return "character", texts, False
    texts, scalar = _prepare(value)
    return "character", texts, scalar


def _streams_from(kind: str, payload: list) -> list:
    if kind == "character":
        return [_text_bytes(item) for item in payload]
    return payload


def _characters(value):
    if isinstance(value, (bytes, bytearray)):
        texts = [f"{byte:02x}" for byte in value]
        return texts, len(texts) == 1
    texts, scalar = _prepare(value)
    return texts, scalar


def _strip_bom(text: str) -> str:
    if text.startswith("\ufeff"):
        return text[1:]
    return text


def _code_point(value) -> int:
    if is_na(value) or value is None:
        return _NA_INTEGER
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        if value < _NA_INTEGER or value > 2147483647:
            _warn("NAs introduced by coercion to integer range")
            return _NA_INTEGER
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            _warn("NAs introduced by coercion")
            return _NA_INTEGER
        truncated = math.trunc(value)
        if truncated < _NA_INTEGER or truncated > 2147483647:
            _warn("NAs introduced by coercion to integer range")
            return _NA_INTEGER
        return int(truncated)
    if isinstance(value, str):
        sign = 1
        body = value
        if body.startswith(("+", "-")):
            sign = -1 if body[0] == "-" else 1
            body = body[1:]
        if body.isdigit():
            return _code_point(sign * int(body))
        _warn("NAs introduced by coercion")
        return _NA_INTEGER
    raise TypeError(
        "argument `vec` should be a list of integer vectors or an integer vector "
        "(or an object coercible to)"
    )


def _valid_code_point(value: int) -> bool:
    return 0 < value <= 0x10FFFF and not 0xD800 <= value <= 0xDFFF


def _from_one(vector) -> str | object:
    if vector is None or (is_na(vector) and not isinstance(vector, (list, tuple))):
        if vector is None:
            return NA
    if isinstance(vector, (list, tuple)):
        points = [_code_point(item) for item in vector]
    else:
        points = [_code_point(vector)]
    chars = []
    for point in points:
        if not _valid_code_point(point):
            _warn(_BAD_CODE % (point & 0xFFFFFFFF))
            return NA
        chars.append(chr(point))
    return "".join(chars)


def _nested_vectors(value) -> bool:
    if not isinstance(value, (list, tuple)):
        return False
    if len(value) == 0:
        return True
    return any(isinstance(item, (list, tuple)) or item is None for item in value)


def _catalog():
    global _catalog_cache
    if _catalog_cache is not None:
        return _catalog_cache
    count = _ucnv_count_available()
    rows = []
    for index in range(count):
        canonical = _ucnv_available_name(index)
        if not canonical:
            continue
        name = canonical.decode()
        err = c_int32(0)
        alias_count = _ucnv_count_aliases(canonical, byref(err))
        aliases = []
        if err.value <= _U_FAILURE and alias_count > 0:
            for alias_index in range(alias_count):
                err = c_int32(0)
                alias = _ucnv_get_alias(canonical, alias_index, byref(err))
                if err.value <= _U_FAILURE and alias:
                    aliases.append(alias.decode())
                else:
                    aliases.append(NA)
        else:
            aliases = [NA]
        rows.append((name, aliases))
    _catalog_cache = rows
    return rows


def _collator():
    collator = icu.Collator.createInstance(icu.Locale("en_US"))
    collator.setStrength(icu.Collator.PRIMARY)
    collator.setAttribute(icu.UCollAttribute.NUMERIC_COLLATION, icu.UCollAttributeValue.ON)
    return collator


_collator_obj = None


def _sort_strings(items: list) -> list:
    global _collator_obj
    if _collator_obj is None:
        _collator_obj = _collator()
    return sorted(items, key=_collator_obj.getSortKey)


def _unique(items: list) -> list:
    seen = set()
    kept = []
    for item in items:
        if item in seen or is_na(item):
            if is_na(item) and NA not in seen:
                seen.add(NA)
                kept.append(NA)
            continue
        seen.add(item)
        kept.append(item)
    return kept


def _u16(raw: bytes, index: int, little: bool) -> int:
    if little:
        return raw[index] | (raw[index + 1] << 8)
    return (raw[index] << 8) | raw[index + 1]


def _u32(raw: bytes, index: int, little: bool) -> int:
    if little:
        return raw[index] | (raw[index + 1] << 8) | (raw[index + 2] << 16) | (raw[index + 3] << 24)
    return (raw[index] << 24) | (raw[index + 1] << 16) | (raw[index + 2] << 8) | raw[index + 3]


def _bom16_le(raw: bytes) -> bool:
    return (
        len(raw) >= 2
        and raw[0] == 0xFF
        and raw[1] == 0xFE
        and (len(raw) < 4 or raw[2] != 0x00 or raw[3] != 0x00)
    )


def _bom16_be(raw: bytes) -> bool:
    return len(raw) >= 2 and raw[0] == 0xFE and raw[1] == 0xFF


def _bom32_le(raw: bytes) -> bool:
    return len(raw) >= 4 and _u32(raw, 0, True) == 0xFEFF


def _bom32_be(raw: bytes) -> bool:
    return len(raw) >= 4 and _u32(raw, 0, False) == 0xFEFF


def _check_ascii(raw: bytes, confidence: bool) -> float:
    warned = 0
    for byte in raw:
        if byte == 0 or byte > 127:
            return 0.0
        if confidence and (byte <= 31 or byte == 127) and byte not in (9, 10, 13, 26):
            warned += 1
    if not confidence:
        return 1.0
    if not raw:
        return 1.0
    return (len(raw) - warned) / len(raw)


def _check_utf8(raw: bytes, confidence: bool) -> float:
    if not confidence:
        if any(byte == 0 for byte in raw):
            return 0.0
        try:
            raw.decode("utf-8")
        except UnicodeDecodeError:
            return 0.0
        return 1.0
    has_bom = len(raw) >= 3 and raw[0] == 0xEF and raw[1] == 0xBB and raw[2] == 0xBF
    valid = 0
    invalid = 0
    index = 0
    size = len(raw)
    while index < size:
        byte = raw[index]
        if byte & 0x80 == 0:
            pass
        elif byte & 0xE0 == 0xC0:
            trail = 1
            while True:
                index += 1
                if index >= size:
                    break
                byte = raw[index]
                if byte & 0xC0 != 0x80:
                    invalid += 1
                    break
                trail -= 1
                if trail == 0:
                    valid += 1
                    break
        elif byte & 0xF0 == 0xE0:
            trail = 2
            while True:
                index += 1
                if index >= size:
                    break
                byte = raw[index]
                if byte & 0xC0 != 0x80:
                    invalid += 1
                    break
                trail -= 1
                if trail == 0:
                    valid += 1
                    break
        elif byte & 0xF8 == 0xF0:
            trail = 3
            while True:
                index += 1
                if index >= size:
                    break
                byte = raw[index]
                if byte & 0xC0 != 0x80:
                    invalid += 1
                    break
                trail -= 1
                if trail == 0:
                    valid += 1
                    break
        else:
            invalid += 1
            if invalid > 5:
                break
        index += 1
    if has_bom and invalid == 0:
        return 1.0
    if has_bom and valid > invalid * 10:
        return 0.75
    if valid > 3 and invalid == 0:
        return 1.0
    if valid > 0 and invalid == 0:
        return 0.50
    if valid == 0 and invalid == 0:
        return 0.50
    if valid > invalid * 10:
        return 0.25
    return 0.0


def _check_utf16(raw: bytes, confidence: bool, little: bool) -> float:
    if len(raw) % 2 != 0:
        return 0.0
    has_le = _bom16_le(raw)
    has_be = _bom16_be(raw)
    if (not little and has_le) or (little and has_be):
        return 0.0
    warned = 0
    index = 0
    while index < len(raw):
        unit = _u16(raw, index, little)
        if unit < 0xD800 or unit > 0xDFFF:
            if unit == 0:
                return 0.0
            if unit >= 0x0530:
                warned += 2
            index += 2
            continue
        if not 0xD800 <= unit <= 0xDBFF:
            return 0.0
        index += 2
        if index >= len(raw):
            return 0.0
        trail = _u16(raw, index, little)
        if not 0xDC00 <= trail <= 0xDFFF:
            return 0.0
        index += 2
    if not confidence:
        return 1.0
    if not raw:
        return 1.0
    return (len(raw) - warned) / len(raw)


def _check_utf32(raw: bytes, confidence: bool, little: bool) -> float:
    if len(raw) % 4 != 0:
        return 0.0
    has_le = _bom32_le(raw)
    has_be = _bom32_be(raw)
    if (not little and has_le) or (little and has_be):
        return 0.0
    valid = 0
    invalid = 0
    for index in range(0, len(raw), 4):
        value = _u32(raw, index, little)
        if value > 0x7FFFFFFF:
            value = value - 0x100000000
        if value < 0 or value > 0x10FFFF or 0xD800 <= value <= 0xDFFF:
            if not confidence:
                return 0.0
            invalid += 1
        else:
            valid += 1
    if not confidence:
        return 1.0
    if (has_le or has_be) and invalid == 0:
        return 1.0
    if (has_le or has_be) and valid > invalid * 10:
        return 0.80
    if valid > 3 and invalid == 0:
        return 1.0
    if valid > 0 and invalid == 0:
        return 0.80
    if valid > invalid * 10:
        return 0.25
    return 0.0


_CHECKERS = {
    "ascii": lambda raw: _check_ascii(raw, False) != 0.0,
    "utf8": lambda raw: _check_utf8(raw, False) != 0.0,
    "utf16be": lambda raw: _check_utf16(raw, False, False) != 0.0,
    "utf16le": lambda raw: _check_utf16(raw, False, True) != 0.0,
    "utf32be": lambda raw: _check_utf32(raw, False, False) != 0.0,
    "utf32le": lambda raw: _check_utf32(raw, False, True) != 0.0,
}


def _is_encoding(value, kind: str):
    kind_name, payload, scalar = _classify(value)
    streams = _streams_from(kind_name, payload)
    check = _CHECKERS[kind]
    result = [NA if item is NA else check(item) for item in streams]
    return _finish(result, scalar)


def _failure_frame() -> dict:
    return {"Encoding": [NA], "Language": [NA], "Confidence": [NA]}


def _detect_one(detector, raw: bytes, filter_markup: bool) -> dict:
    detector.setText(bytes(raw))
    detector.enableInputFilter(bool(filter_markup))
    try:
        matches = detector.detectAll()
    except icu.ICUError:
        return _failure_frame()
    if matches is None:
        return _failure_frame()
    if not isinstance(matches, (list, tuple)):
        matches = (matches,)
    if len(matches) == 0:
        return _failure_frame()
    encodings = []
    languages = []
    confidence = []
    for match in matches:
        try:
            name = match.getName()
        except icu.ICUError:
            name = None
        encodings.append(name if name else NA)
        try:
            language = match.getLanguage()
        except icu.ICUError:
            language = None
        languages.append(NA if language is None else language)
        try:
            score = match.getConfidence()
        except icu.ICUError:
            confidence.append(NA)
        else:
            confidence.append(score / 100.0)
    return {"Encoding": encodings, "Language": languages, "Confidence": confidence}


def _recycle(left: list, right: list) -> list[tuple]:
    if not left or not right:
        return []
    width = max(len(left), len(right))
    if width % len(left) != 0 or width % len(right) != 0:
        _warn("longer object length is not a multiple of shorter object length")
    return [
        (left[index % len(left)], right[index % len(right)])
        for index in range(width)
    ]


def _locale_id(value) -> str | None:
    if value is None:
        return None
    text = _one_string(value, "locale", allow_default=True)
    if text is None:
        return None
    stripped = text.strip()
    if stripped == "":
        return None
    if stripped in ("C", "c", "POSIX"):
        return "en_US_POSIX"
    try:
        name = icu.Locale.createCanonical(stripped).getName()
    except (icu.ICUError, AttributeError):
        name = icu.Locale(stripped).getName()
    if not name or name in ("C", "POSIX"):
        return "en_US_POSIX"
    return name


def _range_points(uset) -> list[int]:
    points = []
    for index in range(uset.getRangeCount()):
        start = uset.getRangeStart(index)
        end = uset.getRangeEnd(index)
        if isinstance(start, str):
            start = ord(start)
        if isinstance(end, str):
            end = ord(end)
        points.extend(range(start, end + 1))
    return points


def _converter_profile(available: str, exemplar: set[int], exemplar_set):
    minimum, maximum, icu_name = _limits(available)
    if maximum != 1:
        return None
    converter = _open(available)
    try:
        mapping = {}
        bad = [False] * 256
        count = [False] * 256
        owned = icu.UnicodeSet()
        buffer = ctypes.create_string_buffer(bytes(range(256)))
        source = c_char_p(ctypes.addressof(buffer) + 1)
        limit = c_char_p(ctypes.addressof(buffer) + 256)
        _ucnv_reset(converter)
        for byte in range(1, 256):
            err = c_int32(0)
            before = ctypes.cast(source, c_void_p).value
            code = _ucnv_next(converter, byref(source), limit, byref(err))
            after = ctypes.cast(source, c_void_p).value
            if err.value > _U_FAILURE or after != before + 1:
                return None
            if 32 <= byte <= 127 and code != byte:
                return None
            if code == 0xFFFD or code < 0:
                bad[byte] = True
                continue
            if not icu.Char.isdefined(code) or icu.Char.isalpha(code):
                bad[byte] = True
            mapping[code] = byte
            owned.add(chr(code))
        if not owned.containsAll(exemplar_set):
            return None
        for code in exemplar:
            if code in mapping:
                count[mapping[code]] = True
        return {
            "name": available,
            "friendly": _friendly(available),
            "bad": bad,
            "count": count,
        }
    finally:
        _ucnv_close(converter)


def _profiles(locale: str) -> list[dict]:
    cached = _profile_cache.get(locale)
    if cached is not None:
        return cached
    data = icu.LocaleData(locale)
    exemplar_set = data.getExemplarSet(
        icu.USET_ADD_CASE_MAPPINGS, icu.ULocaleDataExemplarSetType.ES_STANDARD
    )
    exemplar_set.removeAllStrings()
    points = set(_range_points(exemplar_set))
    built = []
    for available, _aliases in _catalog():
        profile = _converter_profile(available, points, exemplar_set)
        if profile is not None:
            built.append(profile)
    _profile_cache[locale] = built
    return built


class _Guess:
    def __init__(self, friendly: str, confidence: float):
        self.friendly = friendly
        self.confidence = confidence

    def __lt__(self, other: "_Guess") -> bool:
        return self.confidence > other.confidence


def _guess_utf32(raw: bytes, guesses: list[_Guess]) -> None:
    little = _check_utf32(raw, True, True)
    big = _check_utf32(raw, True, False)
    if little >= 0.25 and big >= 0.25:
        guesses.append(_Guess("UTF-32LE", little))
        guesses.append(_Guess("UTF-32BE", big))
    elif little >= 0.25:
        guesses.append(_Guess("UTF-32" if _bom32_le(raw) else "UTF-32LE", little))
    elif big >= 0.25:
        guesses.append(_Guess("UTF-32" if _bom32_be(raw) else "UTF-32BE", big))


def _guess_utf16(raw: bytes, guesses: list[_Guess]) -> None:
    little = _check_utf16(raw, True, True)
    big = _check_utf16(raw, True, False)
    if little >= 0.25 and big >= 0.25:
        guesses.append(_Guess("UTF-16LE", little))
        guesses.append(_Guess("UTF-16BE", big))
    elif little >= 0.25:
        guesses.append(_Guess("UTF-16" if _bom16_le(raw) else "UTF-16LE", little))
    elif big >= 0.25:
        guesses.append(_Guess("UTF-16" if _bom16_be(raw) else "UTF-16BE", big))


def _guess_locale(raw: bytes, locale: str, guesses: list[_Guess]) -> None:
    counts = [0] * 256
    above = 0
    for byte in raw:
        if byte >= 128:
            counts[byte] += 1
            above += 1
    if above <= 0:
        return
    profiles = _profiles(locale)
    if not profiles:
        return
    bad_counts = []
    desired = []
    best = 0
    for profile in profiles:
        bad_total = 0
        wanted = 0
        for byte in range(128, 256):
            if profile["bad"][byte] and not profile["count"][byte]:
                bad_total += counts[byte]
            if profile["count"][byte]:
                wanted += counts[byte]
        bad_counts.append(bad_total)
        desired.append(wanted)
        if wanted > best:
            best = wanted
    for index, profile in enumerate(profiles):
        score = (above - 0.5 * bad_counts[index] - best + desired[index]) / above
        if score < 0.0:
            score = 0.0
        elif score > 1.0:
            score = 1.0
        if score > 0.25:
            guesses.append(_Guess(profile["friendly"], score))


def _guess_8bit(raw: bytes, locale: str | None, guesses: list[_Guess]) -> None:
    if _check_ascii(raw, False) == 0.0 and any(byte == 0 for byte in raw):
        return
    if any(byte == 0 for byte in raw):
        return
    ascii_score = _check_ascii(raw, True)
    if ascii_score >= 0.25:
        guesses.append(_Guess("US-ASCII", ascii_score))
        return
    utf8_score = _check_utf8(raw, True)
    if utf8_score >= 0.25:
        guesses.append(_Guess("UTF-8", utf8_score))
    if utf8_score < 1.0 and locale:
        _guess_locale(raw, locale, guesses)


def _guesses_for(raw: bytes, locale: str | None) -> dict:
    guesses: list[_Guess] = []
    _guess_utf32(raw, guesses)
    _guess_utf16(raw, guesses)
    _guess_8bit(raw, locale, guesses)
    if not guesses:
        return _failure_frame()
    guesses.sort()
    return {
        "Encoding": [guess.friendly for guess in guesses],
        "Language": [NA for _guess in guesses],
        "Confidence": [guess.confidence for guess in guesses],
    }


def _ascii_subset(encoding: str | None, minimum: int) -> bool:
    if minimum != 1:
        return False
    converter = _open(encoding)
    try:
        buffer = ctypes.create_string_buffer(bytes(range(128)))
        source = c_char_p(ctypes.addressof(buffer) + 1)
        limit = c_char_p(ctypes.addressof(buffer) + 128)
        _ucnv_reset(converter)
        for byte in range(1, 128):
            err = c_int32(0)
            before = ctypes.cast(source, c_void_p).value
            code = _ucnv_next(converter, byref(source), limit, byref(err))
            after = ctypes.cast(source, c_void_p).value
            if err.value > _U_FAILURE or after != before + 1 or code != byte or code > 127:
                return False
        return True
    finally:
        _ucnv_close(converter)


def _one_to_one(encoding: str | None) -> bool:
    converter = _open(encoding)
    try:
        buffer = ctypes.create_string_buffer(bytes(range(32, 256)))
        source = c_char_p(ctypes.addressof(buffer))
        limit = c_char_p(ctypes.addressof(buffer) + 224)
        _ucnv_reset(converter)
        for byte in range(32, 256):
            err = c_int32(0)
            before = ctypes.cast(source, c_void_p).value
            code = _ucnv_next(converter, byref(source), limit, byref(err))
            after = ctypes.cast(source, c_void_p).value
            if err.value > _U_FAILURE or after != before + 1:
                return False
            if code < 0 or code > 0xFFFF or 0xD800 <= code <= 0xDFFF:
                return False
            if code == 0xFFFD:
                continue
            unit = c_uint16(code)
            out = ctypes.create_string_buffer(32)
            err = c_int32(0)
            written = _ucnv_from_uchars(converter, out, 32, byref(unit), 1, byref(err))
            if err.value > _U_FAILURE or written != 1 or out.raw[0] != byte:
                return False
        return True
    finally:
        _ucnv_close(converter)


def _info_for(encoding: str | None) -> dict:
    key = encoding if encoding is not None else ""
    cached = _info_cache.get(key)
    if cached is not None:
        return dict(cached)
    minimum, maximum, icu_name = _limits(encoding)
    eight_bit = minimum == 1 and maximum == 1
    info = {
        "Name.friendly": _friendly(icu_name),
        "Name.ICU": icu_name,
    }
    for standard in _standards():
        standard_name = _standard_name(icu_name, standard)
        info[f"Name.{standard}"] = standard_name if standard_name else NA
    info["ASCII.subset"] = _ascii_subset(encoding, minimum)
    info["Unicode.1to1"] = _one_to_one(encoding) if eight_bit else NA
    info["CharSize.8bit"] = eight_bit
    info["CharSize.min"] = minimum
    info["CharSize.max"] = maximum
    _info_cache[key] = dict(info)
    return info


def _short_settings() -> str:
    locale = icu.Locale.getDefault().getName()
    charset = stri_enc_get()
    flag = "#U_CHARSET_IS_UTF8" if _utf8_locked() else ""
    return (
        f"stringi_1.8.9 ({locale}.{charset}; ICU4C {icu.ICU_VERSION} "
        f"[system{flag}]; Unicode {icu.UNICODE_VERSION})"
    )


def _convert_text(text: str, target: str | None, to_raw: bool):
    if is_na(text):
        return None if to_raw else NA
    _warn_unconvertible(text, target)
    raw = _encode_unicode(text, target)
    if to_raw:
        return list(raw)
    if any(byte == 0 for byte in raw):
        raise ValueError("embedded nul in string: ''")
    name = _icu_name(target)
    return _present(raw, name)


def _convert_raw(raw, source: str | None, target: str | None, to_raw: bool):
    if raw is NA:
        return None if to_raw else NA
    source_name = _icu_name(source)
    if source_name == "UTF-8":
        _warn_bad_utf8(raw)
    text = _decode(raw, source)
    return _convert_text(text, target, to_raw)


def stri_enc_isascii(str):
    """Whether each byte string is ASCII. False means it is not."""

    return _is_encoding(str, "ascii")


def stri_enc_isutf8(str):
    """Whether each byte string can be UTF-8. False means it is not."""

    return _is_encoding(str, "utf8")


def stri_enc_isutf16be(str):
    """Whether each byte string can be UTF-16BE. False means it is not."""

    return _is_encoding(str, "utf16be")


def stri_enc_isutf16le(str):
    """Whether each byte string can be UTF-16LE. False means it is not."""

    return _is_encoding(str, "utf16le")


def stri_enc_isutf32be(str):
    """Whether each byte string can be UTF-32BE. False means it is not."""

    return _is_encoding(str, "utf32be")


def stri_enc_isutf32le(str):
    """Whether each byte string can be UTF-32LE. False means it is not."""

    return _is_encoding(str, "utf32le")


def stri_enc_detect(str, filter_angle_brackets=False):
    """Guess encodings with ICU's charset detector.

    The result is one frame per input. Each frame has ``Encoding``,
    ``Language``, and ``Confidence`` columns, most confident first.
    An empty language is ``""``. Failure is one missing row.
    """

    _kind, payload, scalar = _classify(str)
    streams = _streams_from(_kind, payload)
    filters = _logical_vector(filter_angle_brackets, "filter_angle_brackets")
    if not isinstance(filter_angle_brackets, (list, tuple)) and len(filters) == 1 and not streams:
        pairs = []
    else:
        pairs = _recycle(streams, filters)
    detector = icu.CharsetDetector()
    frames = []
    for raw, flag in pairs:
        if raw is NA or is_na(flag):
            frames.append(_failure_frame())
            continue
        frames.append(_detect_one(detector, raw, flag))
    if not isinstance(str, (list, tuple)) and len(frames) == 1:
        return frames[0]
    if scalar and len(frames) == 1 and not isinstance(filter_angle_brackets, (list, tuple)):
        return frames[0]
    return frames


def stri_enc_detect2(str, locale=None):
    """Guess an encoding when the language is known.

    Deprecated in stringi 1.8.9. ``locale=None`` and ``""`` skip the
    language-specific 8-bit scan: the installed function passes a null
    locale through. A non-empty locale checks exemplar letters.
    """

    _warn(_DETECT2_WARNING)
    locale_id = _locale_id(locale)
    _kind, payload, scalar = _classify(str)
    streams = _streams_from(_kind, payload)
    frames = []
    for raw in streams:
        if raw is NA or len(raw) == 0:
            frames.append(_failure_frame())
            continue
        frames.append(_guesses_for(raw, locale_id))
    if scalar and len(frames) == 1:
        return frames[0]
    return frames


def stri_enc_fromutf32(vec):
    """Convert UTF-32 code points to UTF-8 strings.

    A list of vectors returns one string per vector. ``None`` in that list
    is a missing string. A code point of 0, a surrogate, or a value outside
    Unicode becomes a missing string and warns. A flat list of integers is
    one vector.
    """

    if vec is None:
        return NA
    if _nested_vectors(vec):
        return [_from_one(item) for item in vec]
    return _from_one(vec)


def stri_enc_toutf32(str):
    """Convert strings to UTF-32 code points.

    A missing string becomes ``None``. A leading U+FEFF is removed.
    """

    texts, scalar = _characters(str)
    codes = []
    for text in texts:
        if is_na(text):
            codes.append(None)
        else:
            codes.append([ord(char) for char in _strip_bom(text)])
    return _finish(codes, scalar)


def stri_enc_toutf8(str, is_unknown_8bit=False, validate=False):
    """Convert marked strings to UTF-8 and drop a leading BOM.

    Python text is already Unicode, so a true ``is_unknown_8bit`` does not
    rewrite it. ``validate=True`` replaces an ill-formed UTF-8 sequence with
    U+FFFD. ``validate=NA`` turns that string into NA.
    """

    unknown = _one_logical(is_unknown_8bit, "is_unknown_8bit", allow_na=False)
    check = _one_logical(validate, "validate", allow_na=True)
    texts, scalar = _characters(str)
    converted = []
    for text in texts:
        if is_na(text):
            converted.append(NA)
            continue
        text = _strip_bom(text)
        if unknown:
            # Python text is Unicode. Bytes above 127 are real characters.
            pass
        if check is False:
            converted.append(text)
            continue
        raw = text.encode("utf-8")
        try:
            raw.decode("utf-8")
            converted.append(text)
        except UnicodeDecodeError:
            if is_na(check):
                _warn(
                    "invalid UTF-8 code point definition; setting string to NA, "
                    "see also ?stri_enc_toutf8"
                )
                converted.append(NA)
            else:
                _warn("invalid UTF-8 code point definition; fixing")
                converted.append(raw.decode("utf-8", errors="replace"))
    return _finish(converted, scalar)


def stri_enc_toascii(str):
    """Replace every non-ASCII code point with U+001A."""

    texts, scalar = _characters(str)
    converted = []
    for text in texts:
        if is_na(text):
            converted.append(NA)
            continue
        converted.append("".join(char if ord(char) <= 127 else "\x1a" for char in text))
    return _finish(converted, scalar)


def stri_enc_tonative(str):
    """Re-encode marked strings in the default charset."""

    return stri_encode(str, None, None, False)


def stri_enc_mark(str):
    """Report ASCII or UTF-8 for Python text, and the hex form of a raw vector."""

    texts, scalar = _characters(str)
    marks = []
    for text in texts:
        if is_na(text):
            marks.append(NA)
        elif all(ord(char) <= 127 for char in text):
            marks.append("ASCII")
        else:
            marks.append("UTF-8")
    return _finish(marks, scalar)


def stri_enc_list(simplify=True):
    """List ICU converter names.

    ``simplify=True`` returns every alias, duplicates removed, sorted with
    the en_US primary collator and numeric order. Any other ``simplify``
    value returns a dict of canonical name to sorted aliases.
    """

    rows = _catalog()
    if _is_true(simplify):
        flat = []
        for _name, aliases in rows:
            flat.extend(alias for alias in aliases if not is_na(alias))
        seen = set()
        unique = []
        for alias in flat:
            if alias not in seen:
                seen.add(alias)
                unique.append(alias)
        return _sort_strings(unique)
    names = _sort_strings([name for name, _aliases in rows])
    by_name = {name: aliases for name, aliases in rows}
    return {
        name: _sort_strings([alias for alias in by_name[name] if not is_na(alias)])
        for name in names
    }


def stri_enc_info(enc=None):
    """Describe one ICU converter. ``None`` or ``""`` selects the default."""

    selected = _one_string(enc, "enc", allow_default=True)
    try:
        return _info_for(selected)
    except _ICUError as exc:
        raise ValueError(str(exc)) from exc


def stri_enc_get():
    """Return the friendly name of the default converter."""

    return stri_enc_info(None)["Name.friendly"]


def stri_enc_set(enc):
    """Set the default converter and return the previous friendly name.

    ICU built with ``U_CHARSET_IS_UTF8`` ignores the request. The previous
    name is still returned, and a warning says the call had no effect.
    The default is process-wide when the call does take effect, so a test
    that changes it restores the previous name before returning.
    """

    selected = _one_string(enc, "enc", allow_default=False)
    previous = stri_enc_get()
    if _utf8_locked():
        _warn(_UTF8_LOCKED_WARNING)
    else:
        try:
            official = _icu_name(selected)
        except _ICUError as exc:
            raise ValueError(str(exc)) from exc
        _ucnv_set_default(official.encode("utf-8"))
        global _default_name
        _default_name = official
        _info_cache.pop("", None)
    print(f"New settings: {_short_settings()}", file=sys.stderr)
    return previous


def stri_encode(str, from_=None, to=None, to_raw=False):
    """Convert between encodings.

    ``from_=None`` on text uses the Unicode string. On a raw vector it uses
    the default charset. An explicit ``from_`` ignores that distinction and
    reads the stored bytes. ``to=None`` is the default charset. ``to_raw``
    returns a list of integer byte values. A missing input is ``NA``, or
    ``None`` when ``to_raw`` is true.
    """

    source = _one_string(from_, "from", allow_default=True)
    target = _one_string(to, "to", allow_default=True)
    raw_out = _one_logical(to_raw, "to_raw", allow_na=False)
    kind, payload, scalar = _classify(str)
    try:
        if source is None and kind == "character":
            converted = [_convert_text(item, target, raw_out) for item in payload]
        else:
            streams = _streams_from(kind, payload)
            converted = [_convert_raw(item, source, target, raw_out) for item in streams]
    except _ICUError as exc:
        raise ValueError(str(exc)) from exc
    return _finish(converted, scalar)


stri_conv = stri_encode
