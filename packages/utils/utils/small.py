"""Small utils 4.5.0 exports that do not need the R session."""

from __future__ import annotations

import math
import sys


class UtilsError(Exception):
    """An error raised with R's stop message."""


def hasName(x, name):
    """``name %in% names(x)``, one logical per name."""
    names = list(getattr(x, "names", None) or (list(x) if isinstance(x, dict) else []))
    if isinstance(x, dict):
        names = list(x)
    wanted = [name] if isinstance(name, str) else list(name)
    return [item in names for item in wanted]


def modifyList(x, val, keep_null: bool = False):
    """Merge ``val`` into ``x``. A missing value removes the name unless ``keep_null``."""
    if not isinstance(x, dict) or not isinstance(val, dict):
        raise UtilsError("is.list(x) & is.list(val) is not TRUE")
    out = dict(x)
    for key in val:
        if key == "":
            continue
        incoming = val[key]
        if key in out and isinstance(out[key], dict) and isinstance(incoming, dict):
            merged = modifyList(out[key], incoming, keep_null=keep_null)
            if keep_null:
                out[key] = merged
            else:
                out[key] = merged
            continue
        if incoming is None and not keep_null:
            out.pop(key, None)
        else:
            out[key] = incoming
    return out


def glob2rx(pattern, trim_head: bool = False, trim_tail: bool = True):
    """Turn a glob into the regular expression R's ``glob2rx`` builds."""
    patterns = [pattern] if isinstance(pattern, str) else list(pattern)
    if not patterns:
        return []
    converted = [_one_glob(item, trim_head, trim_tail) for item in patterns]
    if isinstance(pattern, str):
        return converted[0]
    return converted


def _one_glob(pattern: str, trim_head: bool, trim_tail: bool) -> str:
    text = "^" + pattern + "$"
    text = text.replace(".", r"\.")
    text = text.replace("*", ".*")
    text = text.replace("?", ".")
    text = _escape_group(text, "(")
    text = _escape_group(text, "[")
    text = _escape_group(text, "{")
    if trim_tail:
        text = text.replace(".*$", "", 1)
    if trim_head:
        text = text.replace("^.*", "", 1)
    return text


def _escape_group(text: str, mark: str) -> str:
    pieces = []
    index = 0
    while index < len(text):
        found = text.find(mark, index)
        if found < 0:
            pieces.append(text[index:])
            break
        if found > 0 and text[found - 1] != "\\":
            pieces.append(text[index:found])
            pieces.append("\\" + mark)
            index = found + 1
        else:
            pieces.append(text[index : found + 1])
            index = found + 1
    return "".join(pieces)


def compareVersion(a, b) -> int:
    """Compare two dotted versions. A missing ``a`` is -1 and a missing ``b`` is 1."""
    if a is None:
        return -1
    if b is None:
        return 1
    left = _version_parts(str(a))
    right = _version_parts(str(b))
    for index, part in enumerate(left):
        if index < len(right):
            if part > right[index]:
                return 1
            if part < right[index]:
                return -1
        else:
            return 1
    if len(right) > len(left):
        return -1
    return 0


def _version_parts(text: str) -> list[int]:
    parts = []
    for piece in text.replace("-", ".").split("."):
        if piece == "" or not _is_integer_token(piece):
            raise UtilsError("invalid version component")
        parts.append(int(piece))
    return parts


def _is_integer_token(text: str) -> bool:
    if text.startswith(("+", "-")):
        text = text[1:]
    return text.isdigit()


def URLencode(URL, reserved: bool = False, repeated: bool = False):
    """Percent-encode each character's UTF-8 bytes, matching ``URLencode``."""
    items = [URL] if isinstance(URL, str) else list(URL)
    safe = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789._~-"
    if not reserved:
        safe += "][!$&'()*+,;=:/?@#"
    encoded = [_encode_one(item, safe, repeated) for item in items]
    if isinstance(URL, str):
        return encoded[0]
    return encoded


def _encode_one(text: str, safe: str, repeated: bool) -> str:
    if not repeated and _already_encoded(text):
        return text
    pieces = []
    for char in text:
        if char in safe:
            pieces.append(char)
            continue
        raw = char.encode("utf-8")
        pieces.append("".join(f"%{byte:02X}" for byte in raw))
    return "".join(pieces)


def _already_encoded(text: str) -> bool:
    digits = set("0123456789abcdefABCDEF")
    index = 0
    while index < len(text) - 2:
        if text[index] == "%" and text[index + 1] in digits and text[index + 2] in digits:
            return True
        index += 1
    return False


def URLdecode(URL):
    """Undo percent-encoding one byte at a time."""
    items = [URL] if isinstance(URL, str) else list(URL)
    decoded = [_decode_one(item) for item in items]
    if isinstance(URL, str):
        return decoded[0]
    return decoded


def _decode_one(text: str) -> str:
    raw = text.encode("utf-8")
    out = bytearray()
    index = 0
    while index < len(raw):
        if raw[index] != 0x25:
            out.append(raw[index])
            index += 1
            continue
        pair = raw[index + 1 : index + 3]
        if len(pair) < 2:
            raise UtilsError("invalid percent escape")
        value = _hex_value(pair[0]) * 16 + _hex_value(pair[1])
        out.append(value)
        index += 3
    return out.decode("utf-8")


def _hex_value(byte: int) -> int:
    if 97 <= byte <= 102:
        byte -= 32
    if byte > 57:
        byte -= 7
    return byte - 48


def alarm(file=None) -> None:
    """Ring the console bell and flush it."""
    stream = sys.stdout if file is None else file
    stream.write("\a")
    flush_console(stream)


def flush_console(file=None) -> None:
    """Flush the console, which is stdout unless a stream is given."""
    stream = sys.stdout if file is None else file
    flush = getattr(stream, "flush", None)
    if flush is not None:
        flush()


def combn(x, m, FUN=None, simplify: bool = True):
    """All combinations of ``x`` taken ``m`` at a time, in R's column order."""
    if isinstance(m, (list, tuple)) or not isinstance(m, (int, float)) or isinstance(m, bool):
        raise UtilsError("length(m) == 1 is not TRUE")
    if m < 0:
        raise UtilsError("m < 0")
    if isinstance(x, (int, float)) and not isinstance(x, bool) and not isinstance(x, list):
        if x > 0 and math.trunc(x) == x:
            values = list(range(1, int(x) + 1))
        else:
            values = [x]
    else:
        values = list(x)
    count_n = len(values)
    width = int(m)
    if count_n < width:
        raise UtilsError("n < m")
    columns = _combinations(values, width)
    if FUN is not None:
        if not callable(FUN):
            raise UtilsError("'FUN' must be a function or NULL")
        columns = [FUN(column) for column in columns]
    if not simplify:
        return columns
    return columns


def _combinations(values: list, width: int) -> list:
    """R's combn index walk. Column ``i`` is ``values`` at those positions."""
    count_n = len(values)
    if width == 0:
        return [[]]
    chosen = list(range(1, width + 1))
    columns = [values[index - 1] for index in chosen]
    out = [list(columns)]
    end = count_n - width + 1
    edge = 0
    span = width
    while chosen[0] != end:
        if edge < count_n - span:
            span = 1
            edge = chosen[width - 1]
            slots = [1]
        else:
            edge = chosen[width - span - 1]
            span += 1
            slots = list(range(1, span + 1))
        for slot in slots:
            chosen[width - span + slot - 1] = edge + slot
        out.append([values[index - 1] for index in chosen])
    return out
