"""Write remote metadata into a source package DESCRIPTION."""

from __future__ import annotations

import gzip
import math
import os
import re
import struct
import sys
from typing import Any

# R read.dcf treats these bytes as space when it joins a field, and space or
# tab as the only characters that mark a continuation line.
_ASCII_SPACE = " \f\n\r\t\v"
_BLANK_LINE = re.compile(rf"^[{_ASCII_SPACE}]*$")
_ESCAPED_BLANK = re.compile(rf"^[{_ASCII_SPACE}]+\.[{_ASCII_SPACE}]*$")
_TAG_LINE = re.compile(r"^([^ \t][^:]*):(.*)$", re.DOTALL)
_LEADING_SPACE = re.compile(rf"^[{_ASCII_SPACE}]*")
_FOLD_WIDTH = int(0.9 * 80)


class _Missing:
    """R's NA: present in the list, omitted when the file is written."""


NA = _Missing()


def add_metadata(pkg_path: Any, meta: dict[str, Any]) -> None:
    """Merge meta into DESCRIPTION and return None.

    pkg_path is a source package directory. meta is a named list: a string
    overwrites that field, None drops it, and a nested dict updates element
    by element the way utils::modifyList does. The observable result is the
    DESCRIPTION file and, when Meta/package.rds exists, that same DESCRIPTION
    vector stored with saveRDS.
    """

    if not isinstance(meta, dict):
        raise TypeError("meta must be a named list")
    root = os.fspath(pkg_path)
    source_desc = os.path.join(root, "DESCRIPTION")
    binary_desc = os.path.join(root, "Meta", "package.rds")
    if os.path.exists(source_desc):
        desc = _read_dcf(source_desc)
        desc = _modify_list(desc, meta)
        _write_dcf(source_desc, desc)
    if os.path.exists(binary_desc):
        _update_package_rds(binary_desc, meta)
    return None


def _update_package_rds(path: str, meta: dict[str, Any]) -> None:
    """readRDS, modifyList the DESCRIPTION vector, and saveRDS it.

    R 4.5 writes serialization version 3 and gzip. The gzip header stores a
    time, so the check is readRDS()$DESCRIPTION. A version 2 gzip payload is
    written, which readRDS accepts.
    """

    ser = _load_serialize()
    obj = _read_rds(path, ser)
    if not isinstance(obj, ser.Obj) or obj.kind != "list":
        raise ValueError("package.rds is not a list")
    names = _attribute_strings(obj, "names", ser)
    if names is None or "DESCRIPTION" not in names:
        raise ValueError("package.rds has no DESCRIPTION")
    index = names.index("DESCRIPTION")
    desc = _description_dict(obj.data[index], ser)
    desc = _modify_list(desc, meta)
    obj.data[index] = _description_vector(desc, ser)
    _write_rds(path, obj, ser)


def _modify_list(base: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """utils::modifyList with keep.null FALSE.

    An empty name is skipped. None deletes a field. When both sides hold a
    dict, the nested dict is updated element by element and new names are
    appended. Otherwise the meta value replaces the field.
    """

    if not isinstance(base, dict):
        raise TypeError("is.list(x) is not TRUE")
    result = dict(base)
    for key, value in updates.items():
        if not isinstance(key, str) or key == "":
            continue
        current = result.get(key, _Missing)
        if current is not _Missing and isinstance(current, dict) and isinstance(value, dict):
            result[key] = _modify_list(current, value)
            continue
        if value is None:
            result.pop(key, None)
            continue
        result[key] = value
    return result


def _read_dcf(path: str) -> dict[str, str]:
    """remotes read_dcf: the first record, with every field kept white."""

    with open(path, "rb") as handle:
        text = handle.read().decode("utf-8", errors="surrogateescape")
    lines = _split_lines(text)
    records: list[list[str]] = []
    current: list[str] = []
    for line in lines:
        if _BLANK_LINE.fullmatch(line):
            if current:
                records.append(current)
                current = []
            continue
        current.append(line)
    if current:
        records.append(current)
    if not records:
        raise ValueError("subscript out of bounds")
    return _parse_record(records[0])


def _split_lines(text: str) -> list[str]:
    if text == "":
        return []
    lines = re.split(r"\r\n|\n|\r", text)
    if lines[-1] == "" and text[-1] in "\n\r":
        lines.pop()
    return lines


def _parse_record(lines: list[str]) -> dict[str, str]:
    if not _TAG_LINE.match(lines[0]):
        _bad_line(lines[0], start=True)
    order: list[str] = []
    values: dict[str, str] = {}
    index = 0
    total = len(lines)
    while index < total:
        match = _TAG_LINE.match(lines[index])
        if match is None:
            _bad_line(lines[index], start=True)
        assert match is not None
        tag = match.group(1)
        parts = [_LEADING_SPACE.sub("", match.group(2), count=1)]
        index += 1
        while index < total and _TAG_LINE.match(lines[index]) is None:
            continuation = lines[index]
            if continuation[:1] not in " \t":
                _bad_line(continuation, start=False)
            if _ESCAPED_BLANK.fullmatch(continuation):
                parts.append("")
            else:
                parts.append(continuation)
            index += 1
        if tag not in values:
            order.append(tag)
        values[tag] = "\n".join(parts)
    return {key: values[key] for key in order}


def _bad_line(line: str, start: bool) -> None:
    shown = line[:20]
    if start and line[:1] in " \t":
        raise ValueError(
            f"Found continuation line starting '{shown} ...' at begin of record."
        )
    raise ValueError(f"Line starting '{shown} ...' is malformed!")


def _write_dcf(path: str, desc: dict[str, Any]) -> None:
    """write.dcf(rbind(unlist(desc)), keep.white = names(desc), indent = 0)."""

    keep = set(desc)
    chunks: list[str] = []
    for name, value in _unlist(desc):
        text = _scalar_text(value)
        if text is None:
            continue
        if name in keep:
            chunks.append(_format_keep(name, text))
        else:
            chunks.append(_format_fold(name, text))
    payload = "".join(chunk + "\n" for chunk in chunks)
    with open(path, "wb") as handle:
        handle.write(payload.encode("utf-8", errors="surrogateescape"))


def _unlist(desc: dict[str, Any]) -> list[tuple[str, Any]]:
    items: list[tuple[str, Any]] = []

    def walk(value: Any, name: str | None) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str) or child is None:
                    continue
                child_name = key if name is None else f"{name}.{key}"
                walk(child, child_name)
            return
        if name is None or value is None:
            return
        items.append((name, value))

    walk(desc, None)
    return items


def _format_keep(tag: str, value: str) -> str:
    """keep.white path: indent a bare continuation, then escape paragraphs."""

    folded = re.sub(r"\n([^ \t])", r"\n \1", value)
    return _escape_paragraphs(f"{tag}: {folded}")


def _format_fold(tag: str, value: str) -> str:
    """formatDL list style at indent 0, then the same paragraph escape."""

    wrapped = _strwrap(f"{tag}: {value}", _FOLD_WIDTH)
    return _escape_paragraphs(wrapped)


def _escape_paragraphs(text: str) -> str:
    text = re.sub(r"\n[ \t]*\n", "\n .\n ", text)
    text = re.sub(r"\n \.([^\n])", r"\n  .\1", text)
    return text


def _strwrap(text: str, width: int) -> str:
    """R strwrap at indent 0. Each word reserves one trailing space in the fit."""

    paragraphs = re.split(r"\n[ \t\n]*\n", text)
    lines: list[str] = []
    for index, paragraph in enumerate(paragraphs):
        words = [word for word in re.split(r"[ \t\n]", paragraph) if word != ""]
        wrapped: list[str] = []
        while words:
            total = 0
            count = 0
            for word in words:
                total += len(word) + 1
                if total <= width:
                    count += 1
                else:
                    break
            count = max(count, 1)
            wrapped.append(" ".join(words[:count]))
            words = words[count:]
        if not wrapped:
            wrapped.append("")
        if index:
            lines.append("")
        lines.extend(wrapped)
    return "\n".join(lines)


def _scalar_text(value: Any) -> str | None:
    if value is None or value is NA or value is _Missing:
        return None
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return _r_character_double(value)
    if isinstance(value, str):
        return value
    raise TypeError("metadata values must be scalars or nested dicts")


def _r_character_double(value: float) -> str:
    """R as.character for a double: fifteen digits, shorter scientific form."""

    if math.isinf(value):
        return "Inf" if value > 0 else "-Inf"
    if value == 0.0:
        return "0"
    negative = value < 0
    scientific = format(abs(value), ".14e")
    mantissa, exponent_text = scientific.split("e")
    exponent = int(exponent_text)
    whole, frac = mantissa.split(".")
    frac = frac.rstrip("0")
    mant = whole if frac == "" else f"{whole}.{frac}"
    digits = whole + frac
    sci = f"{mant}e{exponent:+03d}"
    if exponent >= 0:
        point = len(whole) + exponent
        if point >= len(digits):
            fixed = digits + ("0" * (point - len(digits)))
        else:
            fixed = digits[:point] + "." + digits[point:]
    else:
        zeros = -exponent - len(whole)
        if zeros >= 0:
            fixed = "0." + ("0" * zeros) + digits
        else:
            point = len(digits) + zeros
            fixed = digits[:point] + "." + digits[point:]
    if negative:
        sci = "-" + sci
        fixed = "-" + fixed
    if len(sci) < len(fixed):
        return sci
    return fixed


_HAS_ATTR = 1 << 9
_IS_OBJECT = 1 << 8
_HAS_TAG = 1 << 10
_REFSXP = 255
_NILVALUE = 254
_SYMSXP = 1
_LISTSXP = 2
_LANGSXP = 6
_CHARSXP = 9
_LGLSXP = 10
_INTSXP = 13
_REALSXP = 14
_STRSXP = 16
_VECSXP = 19
_RAWSXP = 24
_BASEENV = 241
_EMPTYENV = 242
_GLOBALENV = 253
_NA_INT = -2147483648
_NA_REAL = bytes.fromhex("7ff00000000007a2")
_LATIN1 = 1 << 2
_UTF8 = 1 << 3
_BYTES = 1 << 1


def _load_serialize():
    """Import digest's version-2 serializer. The DESCRIPTION path does not."""

    module = getattr(_load_serialize, "module", None)
    if module is not None:
        return module
    root = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "digest"))
    if root not in sys.path:
        sys.path.insert(0, root)
    import digest.serialize as module

    _load_serialize.module = module
    return module


def _read_rds(path: str, ser: Any) -> Any:
    with open(path, "rb") as handle:
        blob = handle.read()
    if blob[:2] == b"\x1f\x8b":
        blob = gzip.decompress(blob)
    if blob[:2] != b"X\n":
        raise ValueError("package.rds is not a binary RDS file")
    version = struct.unpack_from(">i", blob, 2)[0]
    offset = 14
    if version >= 3:
        length = struct.unpack_from(">i", blob, offset)[0]
        offset += 4 + length
    if version < 2:
        raise ValueError(f"package.rds serialization version {version} is not supported")
    return _Reader(blob, offset, ser).read_item()


def _write_rds(path: str, obj: Any, ser: Any) -> None:
    payload = gzip.compress(ser.serialize(obj, version=2))
    with open(path, "wb") as handle:
        handle.write(payload)


def _attribute_strings(obj: Any, name: str, ser: Any) -> list[Any] | None:
    for attr_name, value in obj.attributes:
        if attr_name == name and isinstance(value, ser.Obj) and value.kind == "string":
            return list(value.data)
    return None


def _description_dict(obj: Any, ser: Any) -> dict[str, Any]:
    if not isinstance(obj, ser.Obj) or obj.kind != "string":
        raise ValueError("DESCRIPTION is not a character vector")
    names = _attribute_strings(obj, "names", ser)
    if names is None:
        raise ValueError("DESCRIPTION has no names")
    if len(names) != len(obj.data):
        raise ValueError("DESCRIPTION names do not match its length")
    return dict(zip(names, obj.data))


def _description_vector(desc: dict[str, Any], ser: Any) -> Any:
    """setNames(as.character(desc), names(desc))."""

    names = list(desc)
    values = [_rds_text(value, ser) for value in desc.values()]
    vector = ser.character(values)
    vector.attributes = [("names", ser.character(names))]
    return vector


def _rds_text(value: Any, ser: Any) -> Any:
    if value is ser.NA:
        return ser.NA
    if isinstance(value, str):
        return value
    text = _scalar_text(value)
    if text is None:
        return ser.NA
    return text


class _Reader:
    """Binary RDS reader for the SEXPs package.rds stores.

    Symbols are the only values in R 4.5's reference table for this file.
    Character strings are written out in full each time.
    """

    def __init__(self, data: bytes, offset: int, ser: Any) -> None:
        self.data = data
        self.i = offset
        self.ser = ser
        self.refs: list[Any] = [None]

    def read_item(self) -> Any:
        start = self.i
        flags = self._i32()
        type_code = flags & 0xFF
        if type_code == _REFSXP:
            index = self._i32() if flags >> 8 == 0 else flags >> 8
            try:
                return self.refs[index]
            except IndexError as error:
                raise ValueError(f"RDS reference {index} is out of range") from error
        if type_code == _NILVALUE:
            return None
        if type_code == _BASEENV:
            return self.ser.Obj("baseenv")
        if type_code == _EMPTYENV:
            return self.ser.Obj("emptyenv")
        if type_code == _GLOBALENV:
            return self.ser.Obj("globalenv")
        if type_code == _SYMSXP:
            name = self.read_item()
            symbol = ("sym", name)
            self.refs.append(symbol)
            return symbol
        if type_code == _CHARSXP:
            return self._read_charsxp(flags)
        if type_code in (_LISTSXP, _LANGSXP):
            if flags & _HAS_ATTR:
                self.read_item()
            tag = self.read_item() if flags & _HAS_TAG else None
            car = self.read_item()
            cdr = self.read_item()
            return ("pair", tag, car, cdr)
        if type_code in (_LGLSXP, _INTSXP):
            return self._read_ints(flags, "logical" if type_code == _LGLSXP else "integer")
        if type_code == _REALSXP:
            return self._read_reals(flags)
        if type_code == _STRSXP:
            return self._read_strings(flags)
        if type_code == _VECSXP:
            return self._read_list(flags)
        if type_code == _RAWSXP:
            return self._read_raw(flags)
        raise ValueError(f"RDS type {type_code} at offset {start} is not supported")

    def _read_charsxp(self, flags: int) -> Any:
        length = self._i32()
        if length < 0:
            return self.ser.NA
        blob = self.data[self.i : self.i + length]
        self.i += length
        levels = flags >> 12
        if levels & _BYTES or (levels & _LATIN1 and not levels & _UTF8):
            return blob.decode("latin-1")
        return blob.decode("utf-8")

    def _read_ints(self, flags: int, kind: str) -> Any:
        count = self._vec_length()
        values = []
        for _ in range(count):
            item = self._i32()
            if item == _NA_INT:
                values.append(self.ser.NA)
            elif kind == "logical":
                values.append(bool(item))
            else:
                values.append(item)
        return self._vector(kind, values, flags)

    def _read_reals(self, flags: int) -> Any:
        count = self._vec_length()
        values = []
        for _ in range(count):
            blob = self.data[self.i : self.i + 8]
            self.i += 8
            if blob == _NA_REAL:
                values.append(self.ser.NA)
            else:
                values.append(struct.unpack(">d", blob)[0])
        return self._vector("real", values, flags)

    def _read_strings(self, flags: int) -> Any:
        count = self._vec_length()
        values = [self.read_item() for _ in range(count)]
        return self._vector("string", values, flags)

    def _read_list(self, flags: int) -> Any:
        count = self._vec_length()
        values = []
        for _ in range(count):
            item = self.read_item()
            values.append(self.ser.Obj("null") if item is None else item)
        return self._vector("list", values, flags)

    def _read_raw(self, flags: int) -> Any:
        count = self._vec_length()
        blob = self.data[self.i : self.i + count]
        self.i += count
        return self._vector("raw", blob, flags)

    def _vector(self, kind: str, data: Any, flags: int) -> Any:
        attributes = self._read_attributes() if flags & _HAS_ATTR else []
        return self.ser.Obj(kind, data, attributes, object_bit=bool(flags & _IS_OBJECT))

    def _read_attributes(self) -> list[tuple[str, Any]]:
        chain = self.read_item()
        attributes = []
        while chain is not None:
            if not isinstance(chain, tuple) or chain[0] != "pair":
                raise ValueError("RDS attributes are not a pairlist")
            _, tag, car, cdr = chain
            if car is None:
                car = self.ser.Obj("null")
            attributes.append((self._symbol_name(tag), car))
            chain = cdr
        return attributes

    def _symbol_name(self, tag: Any) -> str:
        if isinstance(tag, tuple) and tag[0] == "sym" and isinstance(tag[1], str):
            return tag[1]
        raise ValueError("RDS attribute name is not a symbol")

    def _vec_length(self) -> int:
        length = self._i32()
        if length < 0:
            length = struct.unpack_from(">q", self.data, self.i)[0]
            self.i += 8
        return length

    def _i32(self) -> int:
        value = struct.unpack_from(">i", self.data, self.i)[0]
        self.i += 4
        return value
