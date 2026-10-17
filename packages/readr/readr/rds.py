"""Read and write RDS the way readr 2.2.0 wraps saveRDS and readRDS.

The bytes are R serialization version 2. ``digest.serialize`` writes them,
and this module reads that same layout back. gzip, bzip2, and xz wrappers
use the Python standard library. A gzip header stores a timestamp, so a
compressed file is compared after it is opened.
"""

from __future__ import annotations

import bz2
import gzip
import lzma
import struct
from pathlib import Path

_COMPRESS = ("none", "gz", "bz2", "xz")
_NA_INT = 0x80000000
_NA_REAL = bytes.fromhex("7ff00000000007a2")
_HAS_ATTR = 1 << 9
_IS_OBJECT = 1 << 8
_HAS_TAG = 1 << 10
_ASCII_MASK = 1 << 6
_UTF8_MASK = 1 << 3


class _Node:
    def __init__(self, kind, data=None, attributes=None, object_bit=False, tag=None, car=None, cdr=None):
        self.kind = kind
        self.data = data
        self.attributes = attributes or []
        self.object_bit = object_bit
        self.tag = tag
        self.car = car
        self.cdr = cdr


class _Cursor:
    def __init__(self, blob: bytes):
        self.blob = blob
        self.at = 0

    def take(self, size: int) -> bytes:
        end = self.at + size
        if end > len(self.blob):
            raise ValueError("RDS ended early")
        chunk = self.blob[self.at:end]
        self.at = end
        return chunk

    def i32(self) -> int:
        return struct.unpack(">i", self.take(4))[0]

    def u32(self) -> int:
        return struct.unpack(">I", self.take(4))[0]


def read_rds(file, refhook=None):
    """Read an RDS file written by saveRDS or write_rds."""
    if refhook is not None:
        raise ValueError("refhook is not supported")
    blob = _decompress(Path(file).read_bytes())
    return _to_python(_parse(blob))


def parse_rds(blob: bytes):
    """Read one serialization from bytes that are already uncompressed."""
    return _to_python(_parse(blob))


def write_rds(x, file, compress="none", version=2, refhook=None, text=False, compression=None):
    """Write `x` as RDS and return `x`.

    `compress` is ``none``, ``gz``, ``bz2``, or ``xz``. `version` is 2.
    `text` writes the ascii form. `compression` is the level passed to the
    wrapper, and it is unused when `compress` is ``none``.
    """
    if refhook is not None:
        raise ValueError("refhook is not supported")
    if version != 2:
        raise ValueError("only serialization version 2 is supported")
    kind = _match_compress(compress)
    from digest.serialize import serialize

    payload = serialize(_as_obj(x), version=2, ascii=bool(text))
    Path(file).write_bytes(_compress(payload, kind, compression))
    return x


def _match_compress(value) -> str:
    if not isinstance(value, str) or value not in _COMPRESS and not any(
        item.startswith(value) for item in _COMPRESS
    ):
        raise ValueError("compress must be one of none, gz, bz2, xz")
    if value in _COMPRESS:
        return value
    hits = [item for item in _COMPRESS if item.startswith(value)]
    if len(hits) != 1:
        raise ValueError("compress must be one of none, gz, bz2, xz")
    return hits[0]


def _compress(payload: bytes, kind: str, level) -> bytes:
    if kind == "none":
        return payload
    if kind == "gz":
        return gzip.compress(payload, compresslevel=6 if level is None else int(level))
    if kind == "bz2":
        return bz2.compress(payload, compresslevel=9 if level is None else int(level))
    return lzma.compress(payload, format=lzma.FORMAT_XZ, preset=6 if level is None else int(level))


def _decompress(blob: bytes) -> bytes:
    if blob.startswith(b"\x1f\x8b"):
        return gzip.decompress(blob)
    if blob.startswith(b"BZh"):
        return bz2.decompress(blob)
    if blob.startswith(b"\xfd7zXZ\x00"):
        return lzma.decompress(blob)
    return blob


def _parse(blob: bytes) -> _Node:
    if blob.startswith(b"A\n"):
        raise ValueError("ascii RDS is not supported")
    if not blob.startswith(b"X\n"):
        raise ValueError("not an RDS file")
    cursor = _Cursor(blob)
    cursor.at = 2
    fmt = cursor.i32()
    cursor.i32()
    cursor.i32()
    if fmt == 3:
        # Version 3 stores the writer's native encoding name before the object.
        cursor.take(cursor.i32())
    elif fmt != 2:
        raise ValueError("only serialization versions 2 and 3 are supported")
    return _read_item(cursor, [])


def _read_item(cursor: _Cursor, refs: list):
    flags = cursor.i32()
    type_code = flags & 0xFF
    if type_code == 255:
        index = flags >> 8
        if index == 0:
            index = cursor.i32()
        if index < 1 or index > len(refs):
            raise ValueError(f"RDS reference {index} is missing")
        return refs[index - 1]
    if type_code == 254:
        return _Node("null")
    if type_code == 253:
        return _Node("globalenv")
    if type_code == 242:
        return _Node("emptyenv")
    if type_code == 241:
        return _Node("baseenv")
    if type_code == 1:
        node = _Node("symbol", _read_charsxp(cursor))
        refs.append(node)
        return node
    if type_code == 9:
        raise ValueError("a CHARSXP appeared where a full SEXP was expected")
    # R's reference table records symbols, environments, and a few other
    # singleton objects. Vectors and pairlists are written out in full.
    node = _Node("pending")
    if type_code in (2, 6):
        attributes = _read_item(cursor, refs) if flags & _HAS_ATTR else None
        tag = _read_item(cursor, refs) if flags & _HAS_TAG else None
        car = _read_item(cursor, refs)
        cdr = _read_item(cursor, refs)
        node.kind = "lang" if type_code == 6 else "pairlist"
        node.attributes = _attr_pairs(attributes)
        node.tag = None if tag is None else tag.data
        node.car = car
        node.cdr = cdr
        node.object_bit = bool(flags & _IS_OBJECT)
        return node
    length = _read_length(cursor)
    if type_code == 10:
        node.kind = "logical"
        node.data = [_logical(cursor.i32()) for _ in range(length)]
    elif type_code == 13:
        node.kind = "integer"
        node.data = [_integer(cursor.u32()) for _ in range(length)]
    elif type_code == 14:
        node.kind = "real"
        node.data = [_real(cursor.take(8)) for _ in range(length)]
    elif type_code == 15:
        node.kind = "complex"
        node.data = [(_real(cursor.take(8)), _real(cursor.take(8))) for _ in range(length)]
    elif type_code == 16:
        node.kind = "string"
        node.data = [_read_charsxp(cursor) for _ in range(length)]
    elif type_code == 19:
        node.kind = "list"
        node.data = [_read_item(cursor, refs) for _ in range(length)]
    elif type_code == 24:
        node.kind = "raw"
        node.data = cursor.take(length)
    else:
        raise ValueError(f"RDS type {type_code} is not supported")
    if flags & _HAS_ATTR:
        node.attributes = _attr_pairs(_read_item(cursor, refs))
    node.object_bit = bool(flags & _IS_OBJECT)
    return node


def _read_length(cursor: _Cursor) -> int:
    length = cursor.i32()
    if length == -1:
        return struct.unpack(">q", cursor.take(8))[0]
    if length < 0:
        raise ValueError("RDS length is negative")
    return length


def _read_charsxp(cursor: _Cursor):
    flags = cursor.i32()
    if (flags & 0xFF) != 9:
        raise ValueError("expected a CHARSXP")
    length = cursor.i32()
    if length == -1:
        return None
    if length < 0:
        raise ValueError("CHARSXP length is negative")
    blob = cursor.take(length)
    level = (flags >> 12) & 0xFF
    if level & _UTF8_MASK or level & _ASCII_MASK or level == 0:
        return blob.decode("utf-8")
    return blob.decode("latin-1")


def _logical(value: int):
    if value == _NA_INT or value == -2147483648:
        return None
    if value == 0:
        return False
    if value == 1:
        return True
    raise ValueError(f"logical value {value} is not 0, 1, or NA")


def _integer(value: int):
    if value == _NA_INT:
        return None
    if value >= 0x80000000:
        return value - 0x100000000
    return value


def _real(blob: bytes):
    if blob == _NA_REAL:
        return None
    return struct.unpack(">d", blob)[0]


def _attr_pairs(node):
    pairs = []
    while node is not None and node.kind != "null":
        if node.kind != "pairlist":
            raise ValueError("RDS attributes are not a pairlist")
        pairs.append((node.tag, node.car))
        node = node.cdr
    return pairs


def _to_python(node):
    if node is None or node.kind == "null":
        return None
    if node.kind == "symbol":
        return node.data
    attrs = {name: _to_python(value) for name, value in node.attributes}
    classes = attrs.get("class") or []
    if isinstance(classes, str):
        classes = [classes]
    if node.kind == "list" and "data.frame" in classes:
        from readr.read import Table

        names = list(attrs.get("names") or [])
        columns = [_to_python(column) for column in node.data]
        nrow = len(columns[0]) if columns else 0
        return Table(names, columns, nrow)
    if node.kind == "integer" and "factor" in classes:
        from readr.parse import Factor

        levels = list(attrs.get("levels") or [])
        values = []
        for code in node.data:
            values.append(None if code is None else levels[code - 1])
        return Factor(values, levels, ordered="ordered" in classes)
    if node.kind in ("logical", "integer", "real", "string"):
        return list(node.data)
    if node.kind == "list":
        values = [_to_python(item) for item in node.data]
        names = attrs.get("names")
        if names:
            return dict(zip(names, values))
        return values
    if node.kind == "raw":
        return bytes(node.data)
    if node.kind == "complex":
        return list(node.data)
    raise ValueError(f"cannot return an RDS {node.kind}")


def _as_obj(value):
    from digest.serialize import NA, Obj, character, integer
    from readr.parse import Factor
    from readr.read import Table

    if isinstance(value, Table):
        columns = [_column(column) for column in value.columns]
        nrow = value.nrow
        return Obj(
            "list",
            columns,
            [
                ("names", character(list(value.names))),
                ("class", character(["data.frame"])),
                ("row.names", integer([NA, -nrow if nrow else NA])),
            ],
            object_bit=True,
        )
    if isinstance(value, Factor):
        return _factor(value)
    return value


def _column(values):
    from digest.serialize import NA, character, integer, logical, real
    from readr.parse import Factor

    if isinstance(values, Factor):
        return _factor(values)
    items = list(values)
    if any(isinstance(item, float) for item in items):
        return real([NA if item is None else float(item) for item in items])
    if any(isinstance(item, str) for item in items):
        return character([NA if item is None else item for item in items])
    if any(isinstance(item, bool) for item in items):
        return logical([NA if item is None else bool(item) for item in items])
    if any(isinstance(item, int) for item in items):
        return integer([NA if item is None else int(item) for item in items])
    return logical([NA for _ in items])


def _factor(value):
    from digest.serialize import NA, Obj, character

    levels = list(value.levels)
    codes = []
    for item in value.values:
        if item is None:
            codes.append(NA)
        else:
            codes.append(levels.index(item) + 1)
    classes = ["ordered", "factor"] if value.ordered else ["factor"]
    return Obj(
        "integer",
        codes,
        [("levels", character(levels)), ("class", character(classes))],
        object_bit=True,
    )
