"""Read the ASCII and binary serialization that writePNG stores in R.metadata.

The stream is R's serialize format, version 2 or 3. Version 3 writes the
native encoding name after the version integers. A repeated symbol is the
integer 255 with the 1-based index in the upper bits.
"""

from __future__ import annotations

import struct

_HAS_ATTR = 1 << 9
_HAS_TAG = 1 << 10
_NA_INT = -2147483648
_NA_REAL = bytes.fromhex("7ff00000000007a2")
_UTF8 = 1 << 3
_ASCII = 1 << 6
_LATIN1 = 1 << 2
_BYTES = 1 << 1


class NA:
    """R's missing value inside a vector."""

    def __repr__(self) -> str:
        return "NA"

    def __str__(self) -> str:
        return "NA"

    def __eq__(self, other) -> bool:
        return isinstance(other, NA)

    def __hash__(self) -> int:
        return 0


NA = NA()


class Annotated:
    """A value that still carries attributes other than names."""

    def __init__(self, value, attributes: dict):
        self.value = value
        self.attributes = attributes

    def __repr__(self) -> str:
        return f"Annotated({self.value!r}, {self.attributes!r})"


class _Ascii:
    def __init__(self, blob: bytes):
        self.blob = blob
        self.at = 0

    def line(self) -> str:
        end = self.blob.find(b"\n", self.at)
        if end < 0:
            raise ValueError("unknown input format")
        text = self.blob[self.at:end].decode("ascii")
        self.at = end + 1
        return text

    def i32(self) -> int:
        return int(self.line())

    def real(self):
        token = self.line()
        if token == "NA":
            return NA
        if token == "NaN":
            return float("nan")
        if token == "-0":
            return -0.0
        return float(token)

    def bytes_line(self, length: int) -> bytes:
        if length == 0:
            self.line()
            return b""
        raw = self.line().encode("ascii")
        out = bytearray()
        i = 0
        while i < len(raw) and len(out) < length:
            char = raw[i]
            if char != 92:
                out.append(char)
                i += 1
                continue
            i += 1
            if i >= len(raw):
                break
            mark = chr(raw[i])
            named = {"n": 10, "t": 9, "r": 13, "b": 8, "f": 12, "v": 11, "a": 7, "\\": 92, "'": 39, '"': 34, "?": 63}
            if mark in named:
                out.append(named[mark])
                i += 1
                continue
            if mark in "01234567":
                digits = raw[i:i + 3]
                out.append(int(digits.decode("ascii"), 8) & 0xFF)
                i += len(digits)
                continue
            out.append(raw[i])
            i += 1
        if len(out) != length:
            raise ValueError("unknown input format")
        return bytes(out)


class _Binary:
    def __init__(self, blob: bytes):
        self.blob = blob
        self.at = 0

    def take(self, size: int) -> bytes:
        end = self.at + size
        if end > len(self.blob):
            raise ValueError("unknown input format")
        chunk = self.blob[self.at:end]
        self.at = end
        return chunk

    def i32(self) -> int:
        return struct.unpack(">i", self.take(4))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]

    def real(self):
        blob = self.take(8)
        if blob == _NA_REAL:
            return NA
        return struct.unpack(">d", blob)[0]


def unserialize(blob: bytes | str):
    """Unserialize one R object from ASCII or binary serialization bytes."""

    if isinstance(blob, str):
        blob = blob.encode("utf-8", "surrogateescape")
    if blob.startswith(b"A\n"):
        cursor = _Ascii(blob)
        cursor.at = 2
        return _read_stream(cursor, ascii=True)
    if blob.startswith(b"X\n"):
        cursor = _Binary(blob)
        cursor.at = 2
        return _read_stream(cursor, ascii=False)
    raise ValueError("unknown input format")


def _read_stream(cursor, ascii: bool):
    version = cursor.i32()
    cursor.i32()
    cursor.i32()
    if version == 3:
        length = cursor.i32()
        if ascii:
            cursor.line()
        else:
            cursor.take(length)
    elif version != 2:
        raise ValueError("unknown input format")
    return _convert(_read_item(cursor, ascii, [None]))


def _read_item(cursor, ascii: bool, refs: list):
    flags = cursor.i32()
    type_code = flags & 0xFF
    if type_code == 255:
        index = flags >> 8
        if index == 0:
            index = cursor.i32()
        try:
            return refs[index]
        except IndexError as error:
            raise ValueError("unknown input format") from error
    if type_code == 254:
        return ("null",)
    if type_code == 1:
        name = _read_item(cursor, ascii, refs)
        symbol = ("sym", name[1] if name[0] == "chars" else name)
        refs.append(symbol)
        return symbol
    if type_code == 9:
        return ("chars", _read_chars(cursor, ascii, flags))
    if type_code in (2, 6):
        if flags & _HAS_ATTR:
            _read_item(cursor, ascii, refs)
        tag = _read_item(cursor, ascii, refs) if flags & _HAS_TAG else None
        car = _read_item(cursor, ascii, refs)
        cdr = _read_item(cursor, ascii, refs)
        return ("pair", tag, car, cdr)
    length = _read_length(cursor, ascii)
    if type_code == 10:
        node = ("logical", [_logical(_scalar_int(cursor, ascii)) for _ in range(length)])
    elif type_code == 13:
        node = ("integer", [_integer(_scalar_int(cursor, ascii)) for _ in range(length)])
    elif type_code == 14:
        node = ("real", [cursor.real() for _ in range(length)])
    elif type_code == 16:
        node = ("string", [_string_elt(cursor, ascii, refs) for _ in range(length)])
    elif type_code == 19:
        node = ("list", [_read_item(cursor, ascii, refs) for _ in range(length)])
    elif type_code == 24:
        if ascii:
            raw = bytes(int(cursor.line(), 16) for _ in range(length))
        else:
            raw = cursor.take(length)
        node = ("raw", raw)
    else:
        raise ValueError("unknown input format")
    attrs = _read_item(cursor, ascii, refs) if flags & _HAS_ATTR else None
    return (node[0], node[1], attrs)


def _read_length(cursor, ascii: bool) -> int:
    length = cursor.i32()
    if length == -1:
        if ascii:
            high = cursor.i32()
            low = cursor.i32()
            return high * 4294967296 + (low & 0xFFFFFFFF)
        return struct.unpack(">q", cursor.take(8))[0]
    if length < 0:
        raise ValueError("unknown input format")
    return length


def _read_chars(cursor, ascii: bool, flags: int):
    length = cursor.i32()
    if length < 0:
        return NA
    if ascii:
        blob = cursor.bytes_line(length)
    else:
        blob = cursor.take(length)
    level = flags >> 12
    if level & _BYTES or (level & _LATIN1 and not level & _UTF8 and not level & _ASCII):
        return blob.decode("latin-1")
    return blob.decode("utf-8", "surrogateescape")


def _string_elt(cursor, ascii: bool, refs: list):
    item = _read_item(cursor, ascii, refs)
    if item[0] != "chars":
        raise ValueError("unknown input format")
    return item[1]


def _scalar_int(cursor, ascii: bool) -> int:
    if ascii:
        token = cursor.line()
        if token == "NA":
            return _NA_INT
        return int(token)
    return cursor.i32()


def _logical(value: int):
    if value == _NA_INT:
        return NA
    if value == 0:
        return False
    if value == 1:
        return True
    raise ValueError("unknown input format")


def _integer(value: int):
    if value == _NA_INT:
        return NA
    return value


def _convert(node):
    if not isinstance(node, tuple):
        return node
    kind = node[0]
    if kind == "null":
        return None
    if kind == "sym":
        return node[1]
    if kind == "chars":
        return node[1]
    if kind == "pair":
        return node
    kind, data, attrs = node
    if kind == "list":
        values = [_convert(item) for item in data]
    elif kind == "raw":
        values = data
    else:
        values = list(data)
    names, extra = _split_attrs(attrs)
    if names is not None and _unique_names(names) and len(names) == len(values):
        base = dict(zip(names, values))
    elif kind not in ("list", "raw") and names is None and isinstance(values, list) and len(values) == 1:
        base = values[0]
    else:
        base = values
        if names is not None:
            extra = {"names": names, **extra}
    if extra:
        return Annotated(base, extra)
    return base


def _split_attrs(attrs):
    names = None
    extra = {}
    for name, value in _attr_pairs(attrs):
        converted = _convert(value)
        if name == "names" and names is None:
            if converted is None:
                names = []
            elif isinstance(converted, list):
                names = converted
            else:
                names = [converted]
        else:
            extra[name] = converted
    return names, extra


def _unique_names(names) -> bool:
    if not isinstance(names, list):
        return False
    if any(not isinstance(name, str) for name in names):
        return False
    return len(names) == len(set(names))


def _attr_pairs(node):
    pairs = []
    while isinstance(node, tuple) and node and node[0] == "pair":
        _kind, tag, car, cdr = node
        if isinstance(tag, tuple) and tag and tag[0] == "sym":
            name = tag[1]
        else:
            name = tag
        pairs.append((name, car))
        node = cdr
    return pairs
