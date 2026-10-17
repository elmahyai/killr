"""Read and write text the way ``stri_read_raw``, ``stri_read_lines``, and
``stri_write_lines`` do.

A raw vector is a list of integers in ``0..255``. Lines are split on
CR, LF, CRLF, VT, FF, NEL, line separator, and paragraph separator. A
trailing break does not add an empty line. The string ``"NA"`` is text.
A missing character is ``stringi._na.NA``.
"""

from __future__ import annotations

import warnings
from pathlib import Path

from stringi._na import NA
from stringi.join import stri_join

_TEXT = str

_NOT_GIVEN = object()
_CHUNK = 4194304
_BREAKS = {0x0A, 0x0B, 0x0C, 0x0D, 0x85, 0x2028, 0x2029}

_ALIASES = {
    "utf8": "utf-8",
    "utf-8": "utf-8",
    "latin1": "latin-1",
    "latin-1": "latin-1",
    "iso-8859-1": "latin-1",
    "latin2": "iso8859-2",
    "iso-8859-2": "iso8859-2",
    "ascii": "ascii",
    "utf-16": "utf-16",
    "utf-16le": "utf-16-le",
    "utf-16be": "utf-16-be",
    "utf-32": "utf-32",
    "native": "utf-8",
}


def _warn_alias(name: str) -> None:
    warnings.warn(
        f"The 'fname' argument in {name} is a deprecated alias of 'con' "
        "and will be removed in a future release of 'stringi'.",
        UserWarning,
        stacklevel=3,
    )


def _resolve_con(con, fname, name: str):
    if fname is not _NOT_GIVEN and con is _NOT_GIVEN:
        _warn_alias(name)
        con = fname
    if con is _NOT_GIVEN:
        raise TypeError(f"argument `con` is missing, with no default")
    return con


def _encoding_name(encoding, default: str) -> str:
    if encoding is None or encoding == "":
        return default
    if isinstance(encoding, (list, tuple)):
        if len(encoding) == 0:
            raise ValueError("argument `encoding` should be a non-empty vector")
        if len(encoding) > 1:
            warnings.warn(
                "argument `encoding` should be a single character string; "
                "only the first element is used",
                UserWarning,
                stacklevel=3,
            )
        encoding = encoding[0]
    if encoding is NA:
        raise ValueError("missing values in argument `encoding` is not supported")
    if not isinstance(encoding, str):
        raise TypeError("encoding should be NULL or a character string")
    if encoding == "":
        return default
    if encoding == "auto":
        raise ValueError("encoding `auto` is no longer supported")
    key = encoding.lower().replace("_", "-")
    if key in _ALIASES:
        return _ALIASES[key]
    return encoding


def _read_bytes(con) -> bytes:
    if hasattr(con, "read"):
        chunks = []
        while True:
            block = con.read(_CHUNK)
            if not block:
                break
            if isinstance(block, str):
                block = block.encode("utf-8")
            chunks.append(block)
            if len(block) < _CHUNK:
                break
        return b"".join(chunks)
    path = Path(con)
    data = bytearray()
    with path.open("rb") as handle:
        while True:
            block = handle.read(_CHUNK)
            if not block:
                break
            data.extend(block)
            if len(block) < _CHUNK:
                break
    return bytes(data)


def _split_lines(text: str) -> list:
    if text is NA:
        return [NA]
    parts = []
    start = 0
    index = 0
    size = len(text)
    while index < size:
        code = ord(text[index])
        if code not in _BREAKS:
            index += 1
            continue
        parts.append(text[start:index])
        index += 1
        if code == 0x0D and index < size and text[index] == "\n":
            index += 1
        start = index
    if start < size or not parts:
        parts.append(text[start:])
    return parts


def stri_read_raw(con=_NOT_GIVEN, fname=_NOT_GIVEN):
    """Read a file as a raw vector, with no decoding and no line split."""

    source = _resolve_con(con, fname, "stri_read_raw")
    return list(_read_bytes(source))


def stri_read_lines(con=_NOT_GIVEN, encoding=None, fname=_NOT_GIVEN):
    """Read a file, decode it, and split it into lines.

    ``encoding=None`` or ``""`` uses UTF-8, which is the default converter
    while ``U_CHARSET_IS_UTF8`` is set. ``"auto"`` is an error. The result
    is a list of strings.
    """

    if encoding is not None and not isinstance(encoding, (str, list, tuple)) and encoding is not NA:
        raise TypeError("is.null(encoding) || is.character(encoding) is not TRUE")
    source = _resolve_con(con, fname, "stri_read_lines")
    chosen = _encoding_name(encoding, "utf-8")
    raw = _read_bytes(source)
    try:
        text = raw.decode(chosen)
    except LookupError as exc:
        raise ValueError(f"incorrect character encoding identifier: '{encoding}'") from exc
    except UnicodeDecodeError as exc:
        raise ValueError("invalid byte sequence detected") from exc
    return _split_lines(text)


def stri_write_lines(
    str,
    con=_NOT_GIVEN,
    encoding="UTF-8",
    sep=None,
    fname=_NOT_GIVEN,
):
    """Write each string as a line, encoded for the requested charset.

    The separator defaults to ``\\n``. A missing string makes the joined
    text missing, and writing that raises the same error as R's
    ``writeBin``. Returns ``None``.
    """

    if sep is None:
        sep = "\n"
    if isinstance(sep, (list, tuple)):
        if len(sep) != 1:
            raise ValueError("length(sep) == 1 is not TRUE")
        sep = sep[0]
    if sep is not NA and not isinstance(sep, _TEXT):
        raise ValueError("is.character(sep) is not TRUE")
    destination = _resolve_con(con, fname, "stri_write_lines")
    separator = sep
    joined = stri_join(str, separator, collapse="")
    if len(joined) != 1 or joined[0] is NA:
        raise ValueError("can only write vector objects")
    chosen = _encoding_name(encoding, "utf-8")
    try:
        payload = joined[0].encode(chosen)
    except LookupError as exc:
        raise ValueError(f"incorrect character encoding identifier: '{encoding}'") from exc
    except UnicodeEncodeError as exc:
        raise ValueError("invalid byte sequence detected") from exc
    if hasattr(destination, "write"):
        destination.write(payload)
        return None
    Path(destination).write_bytes(payload)
    return None
