"""getVDigest(): a function that hashes each element of an R vector."""

from __future__ import annotations

import math
import os

from digest.hashing import ALGOS, DigestError, _MISSING, _fail, digest, match_arg
from digest.serialize import (
    NA,
    Obj,
    character,
    integer,
    logical,
    raw,
    real,
)

_TYPE_MSG = (
    "Argument object must be of type character or raw vector if serialize is FALSE"
)
_FILE_MSG = "file=TRUE can only be used with a character object"
_VECTOR_KINDS = ("string", "integer", "real", "logical", "complex", "raw", "list")
_FACTOR_ATTRS = ("contrasts", "levels", "class")


def getVDigest(algo="md5", errormode="stop"):
    """Return a function that hashes each element.

    ``algo`` follows ``match.arg``: an exact name wins, and a prefix wins only
    when one algorithm starts with it. ``raw`` is not an argument of the
    returned function. ``errormode`` is read when a handled error happens:
    ``stop`` raises, ``warn`` warns and returns ``NA``, and ``silent`` returns
    ``None``.
    """
    algo = match_arg(algo, ALGOS, "arg")
    streaming = algo == "spookyhash"

    def vdigest(
        object=_MISSING,
        serialize=True,
        file=False,
        length=math.inf,
        skip="auto",
        ascii=False,
        seed=0,
        serializeVersion=None,
    ):
        if object is _MISSING and _looks_character(file):
            object = file
            file = True
        if object is _MISSING:
            raise DigestError('argument "object" is missing, with no default')
        file_mode = file is True

        def one(value, *, serialize_value: bool, file_value: bool, skip_value):
            return digest(
                value,
                algo=algo,
                serialize=serialize_value,
                file=file_value,
                length=length,
                skip=skip_value,
                ascii=ascii,
                raw=False,
                seed=0 if streaming else seed,
                errormode="stop",
                serializeVersion=serializeVersion,
            )

        if streaming:
            return _streaming(
                object,
                serialize=serialize,
                file_mode=file_mode,
                skip=skip,
                ascii=ascii,
                errormode=errormode,
                algo=algo,
                one=one,
            )
        return _non_streaming(
            object,
            serialize=serialize,
            file_mode=file_mode,
            skip=skip,
            ascii=ascii,
            errormode=errormode,
            one=one,
        )

    return vdigest


def _streaming(object, *, serialize, file_mode, skip, ascii, errormode, algo, one):
    # A stop aborts. warn and silent do not return: hashing continues, and
    # skip = "auto" is not converted because serialization was refused.
    if not serialize:
        _fail(f"{algo} algorithm is not available without serialization.", errormode)
    if file_mode:
        return _fail(f"{algo} algorithm can not be used with files.", errormode)
    skip_value = _resolve_skip(skip, serialize=bool(serialize), file_mode=False, ascii=ascii)
    return [
        one(element, serialize_value=True, file_value=False, skip_value=skip_value)
        for element in _elements(object)
    ]


def _non_streaming(object, *, serialize, file_mode, skip, ascii, errormode, one):
    if not (serialize and not file_mode):
        if not _looks_character(object) and not _is_raw(object):
            return _fail(_TYPE_MSG, errormode)
        if file_mode and not _looks_character(object):
            return _fail(_FILE_MSG, errormode)
        if file_mode:
            return _hash_files(
                object,
                skip=skip,
                ascii=ascii,
                serialize=serialize,
                errormode=errormode,
                one=one,
            )
        skip_value = _resolve_skip(skip, serialize=False, file_mode=False, ascii=ascii)
        if _is_raw(object):
            # The C wrapper hashes a RAWSXP once. It does not hash each byte.
            return [one(_raw_bytes(object), serialize_value=False, file_value=False, skip_value=skip_value)]
        return _hash_character(object, skip_value=skip_value, one=one)

    skip_value = _resolve_skip(skip, serialize=True, file_mode=False, ascii=ascii)
    if ascii and _pmatch_auto(skip):
        # set_skip looks at object[1:30]. After serialize_(), a positive length
        # is a list of raw vectors, and that comparison stops. Length zero is
        # one raw vector, so the header skip is the fourth newline.
        if _length(object) == 0:
            skip_value = "auto"
        else:
            raise DigestError("'list' object cannot be coerced to type 'raw'")
    if _length(object) == 0:
        return [one(object, serialize_value=True, file_value=False, skip_value=skip_value)]
    return [
        one(element, serialize_value=True, file_value=False, skip_value=skip_value)
        for element in _elements(object)
    ]


def _hash_files(object, *, skip, ascii, serialize, errormode, one):
    paths = ["NA" if item is NA else item for item in _string_items(object)]
    # file.exists() on a vector makes if() fail before any digest call.
    if len(paths) == 0:
        raise DigestError("argument is of length zero")
    if len(paths) > 1:
        raise DigestError("the condition has length > 1")
    path = os.path.expanduser(paths[0])
    if not os.path.exists(path):
        _fail(f"The file does not exist: {path}", errormode)
        raise DigestError(f"Cannot open input file: {path}")
    if os.path.isdir(path):
        _fail(f"The specified pathname is not a file: {path}", errormode)
        raise DigestError(f"Cannot open input file: {path}")
    if not os.access(path, os.R_OK):
        _fail(f"The specified file is not readable: {path}", errormode)
        raise DigestError(f"Cannot open input file: {path}")
    skip_value = _resolve_skip(skip, serialize=bool(serialize), file_mode=True, ascii=ascii)
    return [one(path, serialize_value=False, file_value=True, skip_value=skip_value)]


def _hash_character(object, *, skip_value, one):
    items = _string_items(object)
    if not items:
        # asChar(character(0)) is NA, and CHAR(NA_STRING) is the bytes of "NA".
        return [one("NA", serialize_value=False, file_value=False, skip_value=skip_value)]
    return [
        one("NA" if item is NA else item, serialize_value=False, file_value=False, skip_value=skip_value)
        for item in items
    ]


def _elements(object) -> list:
    """Values ``lapply`` / ``vapply`` would pass. An empty object contributes none."""
    if isinstance(object, Obj):
        if _obj_len(object) == 0:
            return []
        if object.kind == "string":
            return [_as_char(item) for item in object.data]
        if object.kind == "integer":
            return [_as_int_element(object, item) for item in object.data]
        if object.kind == "real":
            return [real([item]) for item in object.data]
        if object.kind == "logical":
            return [logical([item]) for item in object.data]
        if object.kind == "complex":
            return [Obj("complex", [item]) for item in object.data]
        if object.kind == "raw":
            return [raw(bytes([byte])) for byte in object.data]
        if object.kind == "list":
            return list(object.data)
        return [object]
    if isinstance(object, str):
        return [object]
    if isinstance(object, (bytes, bytearray)):
        return [raw(bytes([byte])) for byte in object]
    if isinstance(object, (list, tuple)):
        if _is_string_list(object):
            return [_as_char(item) for item in object]
        return list(object)
    if object is None:
        return []
    return [object]


def _as_char(item):
    if item is NA:
        return character([NA])
    return item


def _as_int_element(object: Obj, value):
    classes = _class_names(object)
    if "factor" in classes:
        kept = [(name, attr) for name, attr in object.attributes if name in _FACTOR_ATTRS]
        return Obj("integer", [value], kept, object_bit=True)
    return integer([value])


def _class_names(object: Obj) -> list:
    for name, value in object.attributes:
        if name == "class" and isinstance(value, Obj) and value.kind == "string":
            return list(value.data)
    return []


def _length(object) -> int:
    if object is None:
        return 0
    if isinstance(object, str):
        return 1
    if isinstance(object, Obj):
        return _obj_len(object)
    if isinstance(object, (list, tuple, bytes, bytearray)):
        return len(object)
    return 1


def _obj_len(object: Obj) -> int:
    if object.kind == "null":
        return 0
    if object.kind in _VECTOR_KINDS:
        return 0 if object.data is None else len(object.data)
    return 1


def _looks_character(object) -> bool:
    if isinstance(object, str):
        return True
    if isinstance(object, Obj) and object.kind == "string":
        return True
    return _is_string_list(object)


def _is_string_list(object) -> bool:
    if not isinstance(object, (list, tuple)) or len(object) == 0:
        return False
    saw_string = False
    for item in object:
        if isinstance(item, str):
            saw_string = True
        elif item is not NA:
            return False
    return saw_string


def _string_items(object) -> list:
    if isinstance(object, str):
        return [object]
    if isinstance(object, Obj) and object.kind == "string":
        return list(object.data)
    if isinstance(object, (list, tuple)):
        return list(object)
    return []


def _is_raw(object) -> bool:
    if isinstance(object, (bytes, bytearray)):
        return True
    return isinstance(object, Obj) and object.kind == "raw"


def _raw_bytes(object) -> bytes:
    if isinstance(object, Obj):
        return bytes(object.data)
    return bytes(object)


def _resolve_skip(skip, *, serialize: bool, file_mode: bool, ascii: bool):
    """``skip = "auto"`` becomes 14 only when the object is serialized."""
    if serialize and not file_mode and _pmatch_auto(skip) and not ascii:
        return 14
    if _is_character_skip(skip):
        return 0
    return skip


def _pmatch_auto(skip) -> bool:
    items = list(skip) if isinstance(skip, (list, tuple)) else [skip]
    for item in items:
        if isinstance(item, str) and item != "" and "auto".startswith(item):
            return True
    return False


def _is_character_skip(skip) -> bool:
    if isinstance(skip, str):
        return True
    if isinstance(skip, (list, tuple)) and skip:
        return all(isinstance(item, str) or item is NA for item in skip)
    return False
