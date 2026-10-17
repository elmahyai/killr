"""R serialization version 2, as R 4.5 writes it.

Binary header is ``X\\n``, format 2, writer ``4.5.0``, reader ``2.3.0``.
``digest`` skips those 14 bytes when ``skip`` is ``"auto"``.

Ascii header is ``A`` and the same three integers, each on its own line.
``digest`` skips through the fourth newline. Integers are decimal lines and
``NA`` is the text ``NA``. Reals use the C library's ``%.16g``. Strings use
C escapes, and a byte outside printable ASCII is three octal digits. A raw
byte is two lowercase hex digits.
"""

from __future__ import annotations

import contextvars
import ctypes
import math
import struct
from typing import Iterable

# R's NA real is a NaN whose low 32 bits are 1954.
NA_REAL = bytes.fromhex("7ff00000000007a2")
NA_INT = 0x80000000

ASCII_MASK = 1 << 6
UTF8_MASK = 1 << 3

HAS_ATTR = 1 << 9
IS_OBJECT = 1 << 8
HAS_TAG = 1 << 10

TYPE = {
    "symbol": 1,
    "pairlist": 2,
    "lang": 6,
    "logical": 10,
    "integer": 13,
    "real": 14,
    "complex": 15,
    "string": 16,
    "list": 19,
    "raw": 24,
    "null": 254,
    "globalenv": 253,
    "emptyenv": 242,
    "baseenv": 241,
}

# Writer version packed the way R 4.5.0 packs R_VERSION, and the version-2 reader.
_WRITER = 0x00040500
_READER = 0x00020300
_HEADER = b"X\n" + struct.pack(">iii", 2, _WRITER, _READER)
_ASCII = contextvars.ContextVar("digest_ascii_serialize", default=False)
_libc = ctypes.CDLL(None)


class NAType:
    """R's missing value. Distinct from a plain NaN."""

    def __repr__(self) -> str:
        return "NA"

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NAType)

    def __hash__(self) -> int:
        return id(NAType)


NA = NAType()


class Obj:
    """One R object. ``attributes`` is the pairlist order R writes."""

    def __init__(
        self,
        kind: str,
        data=None,
        attributes: list | None = None,
        object_bit: bool = False,
        tag: str | None = None,
        car=None,
        cdr=None,
    ) -> None:
        self.kind = kind
        self.data = data
        self.attributes = attributes or []
        self.object_bit = object_bit
        self.tag = tag
        self.car = car
        self.cdr = cdr

    def __repr__(self) -> str:
        return f"Obj({self.kind!r})"


def character(values: Iterable) -> Obj:
    return Obj("string", [_as_string(value) for value in values])


def integer(values: Iterable) -> Obj:
    return Obj("integer", [_as_int(value) for value in values])


def real(values: Iterable) -> Obj:
    return Obj("real", [_as_real(value) for value in values])


def logical(values: Iterable) -> Obj:
    return Obj("logical", [_as_logical(value) for value in values])


def raw(values: Iterable) -> Obj:
    if isinstance(values, (bytes, bytearray)):
        return Obj("raw", bytes(values))
    out = bytearray()
    for value in values:
        if value is NA:
            out.append(0)
            continue
        out.append(int(value) & 0xFF)
    return Obj("raw", bytes(out))


def rlist(items: Iterable, names: Iterable[str] | None = None) -> Obj:
    data = [coerce(item) for item in items]
    attributes = []
    if names is not None:
        attributes.append(("names", character(list(names))))
    return Obj("list", data, attributes)


def integer_matrix(values: Iterable, ncol: int, nrow: int | None = None) -> Obj:
    data = [_as_int(value) for value in values]
    if nrow is None:
        if ncol <= 0:
            raise ValueError("ncol must be positive")
        nrow = len(data) // ncol
    body = Obj("integer", data, [("dim", integer([nrow, ncol]))])
    body.kind = "integer"
    return body


def real_matrix(values: Iterable, ncol: int, nrow: int | None = None) -> Obj:
    data = [_as_real(value) for value in values]
    if nrow is None:
        nrow = len(data) // ncol
    return Obj("real", data, [("dim", integer([nrow, ncol]))])


def data_frame(**columns) -> Obj:
    """Build a data.frame the way R expands a matrix argument."""
    fields: list[tuple[str, Obj]] = []
    nrow = 0
    for name, column in columns.items():
        column = coerce(column)
        if _is_matrix(column):
            dims = _dim(column)
            rows, cols = dims
            nrow = rows
            flat = column.data
            for index in range(cols):
                piece = flat[index * rows : (index + 1) * rows]
                if column.kind == "integer":
                    fields.append((f"{name}.{index + 1}", integer(piece)))
                else:
                    fields.append((f"{name}.{index + 1}", real(piece)))
            continue
        fields.append((name, column))
        nrow = _length(column)
    body = Obj(
        "list",
        [column for _, column in fields],
        [
            ("names", character([name for name, _ in fields])),
            ("class", character(["data.frame"])),
            ("row.names", integer([NA, -nrow if nrow else NA])),
        ],
        object_bit=True,
    )
    return body


def factor(values: Iterable) -> Obj:
    labels = [_as_string(value) for value in values]
    levels = sorted({label for label in labels if label is not NA})
    codes = []
    for label in labels:
        if label is NA:
            codes.append(NA)
        else:
            codes.append(levels.index(label) + 1)
    return Obj(
        "integer",
        codes,
        [
            ("levels", character(levels)),
            ("class", character(["factor"])),
        ],
        object_bit=True,
    )


def symbol(name: str) -> Obj:
    return Obj("symbol", name)


def null() -> Obj:
    return Obj("null")


def coerce(value) -> Obj:
    """Map a Python value onto the R object ``digest`` serializes."""
    if isinstance(value, Obj):
        return value
    if value is None:
        return Obj("null")
    if value is NA:
        return Obj("logical", [NA])
    if isinstance(value, bool):
        return Obj("logical", [value])
    if isinstance(value, str):
        return character([value])
    if isinstance(value, int) and not isinstance(value, bool):
        return real([value])
    if isinstance(value, float):
        return real([value])
    if isinstance(value, (bytes, bytearray)):
        return Obj("raw", bytes(value))
    if isinstance(value, list):
        return rlist(value)
    raise TypeError(f"cannot serialize {type(value).__name__}")


def serialize(value, version: int = 2, ascii: bool = False) -> bytes:
    """Return the bytes R's ``serialize(version=2)`` writes, including the header."""
    if version != 2:
        raise ValueError("only serialization version 2 is implemented")
    token = _ASCII.set(bool(ascii))
    try:
        out = bytearray()
        if ascii:
            out.extend(b"A\n")
            _i32(out, 2)
            _i32(out, _WRITER)
            _i32(out, _READER)
        else:
            out.extend(_HEADER)
        _write_item(coerce(value), out)
        return bytes(out)
    finally:
        _ASCII.reset(token)


def _write_item(obj: Obj, out: bytearray) -> None:
    if obj.kind == "null":
        _i32(out, TYPE["null"])
        return
    if obj.kind in ("globalenv", "emptyenv", "baseenv"):
        _i32(out, TYPE[obj.kind])
        return
    if obj.kind == "symbol":
        _i32(out, TYPE["symbol"])
        _write_charsxp(obj.data, out)
        return
    flags = TYPE[obj.kind]
    if obj.object_bit:
        flags |= IS_OBJECT
    if obj.attributes:
        flags |= HAS_ATTR
    if obj.kind in ("pairlist", "lang") and obj.tag:
        flags |= HAS_TAG
    _i32(out, flags)
    # Pairlists and calls write attributes before the CAR. Vectors write them after the values.
    if obj.kind in ("pairlist", "lang") and obj.attributes:
        _write_attributes(obj.attributes, out)
    if obj.kind == "string":
        _i32(out, len(obj.data))
        for item in obj.data:
            _write_charsxp(item, out)
        _write_tail_attributes(obj, out)
        return
    if obj.kind == "integer":
        _i32(out, len(obj.data))
        for item in obj.data:
            if item is NA:
                _u32(out, NA_INT)
            else:
                _i32(out, int(item))
        _write_tail_attributes(obj, out)
        return
    if obj.kind == "logical":
        _i32(out, len(obj.data))
        for item in obj.data:
            if item is NA:
                _u32(out, NA_INT)
            else:
                _i32(out, 1 if item else 0)
        _write_tail_attributes(obj, out)
        return
    if obj.kind == "real":
        _i32(out, len(obj.data))
        for item in obj.data:
            _write_real(out, item)
        _write_tail_attributes(obj, out)
        return
    if obj.kind == "complex":
        _i32(out, len(obj.data))
        for real_part, imag_part in obj.data:
            _write_real(out, real_part)
            _write_real(out, imag_part)
        _write_tail_attributes(obj, out)
        return
    if obj.kind == "raw":
        blob = obj.data
        _i32(out, len(blob))
        if _ASCII.get():
            for byte in blob:
                _ascii_line(out, f"{byte:02x}")
        else:
            out.extend(blob)
        _write_tail_attributes(obj, out)
        return
    if obj.kind == "list":
        _i32(out, len(obj.data))
        for item in obj.data:
            _write_item(coerce(item), out)
        _write_tail_attributes(obj, out)
        return
    if obj.kind in ("pairlist", "lang"):
        if obj.tag:
            _write_item(symbol(obj.tag), out)
        _write_item(coerce(obj.car), out)
        _write_item(obj.cdr if obj.cdr is not None else Obj("null"), out)
        return
    raise TypeError(f"cannot write {obj.kind}")


def _write_tail_attributes(obj: Obj, out: bytearray) -> None:
    if obj.attributes:
        _write_attributes(obj.attributes, out)


def _write_attributes(attributes: list, out: bytearray) -> None:
    for name, value in attributes:
        _i32(out, TYPE["pairlist"] | HAS_TAG)
        _write_item(symbol(name), out)
        _write_item(coerce(value), out)
    _i32(out, TYPE["null"])


def _write_charsxp(value, out: bytearray) -> None:
    if value is NA:
        _i32(out, 9)
        _i32(out, -1)
        return
    blob = value.encode("utf-8")
    levels = ASCII_MASK if blob.isascii() else UTF8_MASK
    _i32(out, 9 | (levels << 12))
    _i32(out, len(blob))
    if _ASCII.get():
        out.extend(_escape_ascii(blob))
        out.extend(b"\n")
    else:
        out.extend(blob)


def _escape_ascii(blob: bytes) -> bytes:
    """R's ascii ``OutString``: C escapes, then three-digit octal."""
    parts = []
    for byte in blob:
        if byte == 0x07:
            parts.append(b"\\a")
        elif byte == 0x08:
            parts.append(b"\\b")
        elif byte == 0x09:
            parts.append(b"\\t")
        elif byte == 0x0A:
            parts.append(b"\\n")
        elif byte == 0x0B:
            parts.append(b"\\v")
        elif byte == 0x0C:
            parts.append(b"\\f")
        elif byte == 0x0D:
            parts.append(b"\\r")
        elif byte == 0x22:
            parts.append(b'\\"')
        elif byte == 0x27:
            parts.append(b"\\'")
        elif byte == 0x3F:
            parts.append(b"\\?")
        elif byte == 0x5C:
            parts.append(b"\\\\")
        elif byte <= 0x20 or byte >= 0x7F:
            parts.append(b"\\%03o" % byte)
        else:
            parts.append(bytes((byte,)))
    return b"".join(parts)


def _write_real(out: bytearray, value) -> None:
    if _ASCII.get():
        _ascii_line(out, _real_ascii(value))
    else:
        out.extend(_real_bytes(value))


def _real_ascii(value) -> str:
    if value is NA:
        return "NA"
    number = float(value)
    if math.isnan(number):
        return "NaN"
    if math.isinf(number):
        return "Inf" if number > 0 else "-Inf"
    # R prints with snprintf("%.16g"). Python's format rounds 1e-20 to 1e-20.
    buf = ctypes.create_string_buffer(128)
    _libc.snprintf(buf, 128, b"%.16g", ctypes.c_double(number))
    return buf.value.decode("ascii")


def _ascii_line(out: bytearray, text: str) -> None:
    out.extend(text.encode("ascii"))
    out.extend(b"\n")


def _real_bytes(value) -> bytes:
    if value is NA:
        return NA_REAL
    if isinstance(value, float) and math.isnan(value):
        return struct.pack(">d", value)
    return struct.pack(">d", float(value))


def _i32(out: bytearray, value: int) -> None:
    if _ASCII.get():
        _ascii_line(out, str(int(value)))
        return
    out.extend(struct.pack(">i", int(value)))


def _u32(out: bytearray, value: int) -> None:
    if _ASCII.get():
        # NA_INTEGER is the text NA, not the signed decimal of the bit pattern.
        if (int(value) & 0xFFFFFFFF) == NA_INT:
            _ascii_line(out, "NA")
        else:
            _i32(out, int(value))
        return
    out.extend(struct.pack(">I", int(value) & 0xFFFFFFFF))


def _as_string(value):
    if value is NA or value is None:
        return NA
    return str(value)


def _as_int(value):
    if value is NA or value is None:
        return NA
    return int(value)


def _as_real(value):
    if value is NA or value is None:
        return NA
    return float(value)


def _as_logical(value):
    if value is NA or value is None:
        return NA
    return bool(value)


def _length(obj: Obj) -> int:
    if obj.kind == "null":
        return 0
    if obj.kind in ("string", "integer", "real", "logical", "complex", "raw", "list"):
        return len(obj.data)
    return 1


def _is_matrix(obj: Obj) -> bool:
    return any(name == "dim" for name, _ in obj.attributes)


def _dim(obj: Obj) -> tuple[int, int]:
    for name, value in obj.attributes:
        if name == "dim":
            return int(value.data[0]), int(value.data[1])
    raise ValueError("matrix has no dim")
