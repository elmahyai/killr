"""Validate a raw byte vector as UTF-8, as R's ``checkUTF8``."""

from __future__ import annotations

from base64enc.base64encode import _as_integer

_INVALID = "invalid input"


def checkUTF8(what, quiet=False, charlen=False, min_char=1):
    """Return whether ``what`` is valid UTF-8.

    ``what`` must be a raw vector (bytes). With ``quiet=False``, invalid
    input raises ``ValueError`` with the same message as R. With
    ``quiet=True``, invalid input returns ``False``. With ``charlen=True``,
    success returns ``0`` and failure returns the negated longest sequence
    length seen before the error, matching the C implementation.
    """
    buf = _as_raw(what)
    min_char, _ = _as_integer(min_char)
    maxcl_holder = [0]
    cause = [""]

    res = _utf8_check(buf, maxcl_holder, min_char, cause)

    if _quiet_raises(quiet) and res:
        raise ValueError(cause[0])
    if _charlen_mode(charlen):
        maxcl = maxcl_holder[0]
        return maxcl if res == 0 else -maxcl
    return res == 0


def _utf8_check(buf: bytes, maxcl_holder: list[int], min_char: int, cause: list[str]) -> int:
    i = 0
    bp = len(buf)
    line = 1
    maxcl = 1

    def report(reason: str) -> int:
        byte = buf[i]
        cause[0] = (
            f"INVALID byte 0x{byte:02x} at 0x{i:x} ({i}, line {line}): {reason}\n"
        )
        maxcl_holder[0] = maxcl
        return 1

    while i < bp:
        if min_char is not None and min_char > 0 and buf[i] < min_char:
            return report("disallowed control character")
        if buf[i] < 128:
            if buf[i] == 0x0A:
                line += 1
        elif buf[i] < 192:
            return report("2+ byte of a sequence found in first position")
        elif buf[i] < 194:
            return report("overlong encoding (<=127 encoded)")
        elif buf[i] < 224:
            if i + 1 < bp:
                i += 1
                if buf[i] < 0x80 or buf[i] > 0xBF:
                    return report("invalid second byte in 2-byte encoding")
                if maxcl < 2:
                    maxcl = 2
            else:
                break
        elif buf[i] < 240:
            if i + 2 < bp:
                i += 1
                if buf[i] < 0x80 or buf[i] > 0xBF:
                    return report("invalid second byte in 3-byte encoding")
                i += 1
                if buf[i] < 0x80 or buf[i] > 0xBF:
                    return report("invalid third byte in 3-byte encoding")
                if maxcl < 3:
                    maxcl = 3
            else:
                break
        elif buf[i] < 245:
            if i + 3 < bp:
                i += 1
                if buf[i] < 0x80 or buf[i] > 0xBF:
                    return report("invalid second byte in 4-byte encoding")
                i += 1
                if buf[i] < 0x80 or buf[i] > 0xBF:
                    return report("invalid third byte in 4-byte encoding")
                i += 1
                if buf[i] < 0x80 or buf[i] > 0xBF:
                    return report("invalid fourth byte in 4-byte encoding")
                if maxcl < 3:
                    maxcl = 3
            else:
                break
        elif buf[i] < 254:
            return report("invalid start of a codepoint above 0x10FFFF")
        else:
            return report("invalid start byte (FE/FF)")
        i += 1

    bp -= i
    if bp > 0:
        return report("unterminated multi-byte sequence at the end of file")
    return 0


def _as_raw(what) -> bytes:
    if isinstance(what, (bytes, bytearray, memoryview)):
        return bytes(what)
    raise ValueError(_INVALID)


def _as_r_integer(value):
    if isinstance(value, bool):
        return 1 if value else 0
    iv, _ = _as_integer(value)
    return iv


def _quiet_raises(quiet) -> bool:
    iv = _as_r_integer(quiet)
    if iv is None:
        return False
    return iv == 0


def _charlen_mode(charlen) -> bool:
    iv = _as_r_integer(charlen)
    if iv is None:
        return True
    return iv != 0
