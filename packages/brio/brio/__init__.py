"""Fast, binary-mode file and line helpers modeled on brio."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable


def _path(path: str | Path) -> Path:
    return Path(path)


def file_line_endings(path: str | Path) -> str | None:
    """Return ``"\n"``, ``"\r\n"``, or ``None`` if no LF occurs."""
    previous = b"\0"
    with _path(path).open("rb") as stream:
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            for byte in chunk:
                if byte == 10:
                    return "\r\n" if previous == 13 else "\n"
                previous = byte
    return None


def read_file(path: str | Path) -> str:
    """Read the complete file as UTF-8 without newline translation."""
    return _path(path).read_bytes().decode("utf-8")


def read_file_raw(path: str | Path) -> bytes:
    """Read the complete file as bytes."""
    return _path(path).read_bytes()


def read_lines(path: str | Path, n: int = -1) -> list[str]:
    """Read LF-delimited UTF-8 lines, removing a preceding CR."""
    if n == 0:
        return []
    data = read_file_raw(path)
    lines: list[str] = []
    start = 0
    for position, byte in enumerate(data):
        if byte != 10:
            continue
        line = data[start:position]
        if line.endswith(b"\r"):
            line = line[:-1]
        lines.append(line.decode("utf-8"))
        if n > 0 and len(lines) >= n:
            return lines
        start = position + 1
    if start < len(data):
        lines.append(data[start:].decode("utf-8"))
    return lines


def write_file(text: str, path: str | Path) -> str:
    """Write one UTF-8 string exactly, returning the string."""
    if not isinstance(text, str):
        text = str(text)
    _path(path).write_bytes(text.encode("utf-8"))
    return text


def write_file_raw(raw: bytes | bytearray | memoryview, path: str | Path) -> bytes:
    """Write raw bytes exactly, returning immutable bytes."""
    value = bytes(raw)
    _path(path).write_bytes(value)
    return value


def write_lines(text: Iterable[str] | str, path: str | Path, eol: str = "\n") -> Iterable[str] | str:
    """Write each string with exactly one requested line ending."""
    values = [text] if isinstance(text, str) else list(text)
    with _path(path).open("wb") as stream:
        for value in values:
            value = str(value)
            encoded = value.encode("utf-8")
            # C brio treats embedded LF as a line boundary and drops CR only
            # when it directly precedes that LF.
            pieces = encoded.split(b"\n")
            for piece in pieces[:-1]:
                if piece.endswith(b"\r"):
                    piece = piece[:-1]
                stream.write(piece)
                stream.write(eol.encode("utf-8"))
            stream.write(pieces[-1])
            stream.write(eol.encode("utf-8"))
    return text


def readLines(con: str | Path, n: int = -1, **_ignored: object) -> list[str]:
    """brio's restricted base-R-compatible spelling of :func:`read_lines`."""
    if not isinstance(con, (str, Path)):
        raise TypeError("Only file paths are supported by brio::readLines()")
    return read_lines(con, n)


def writeLines(
    text: Iterable[str] | str,
    con: str | Path,
    sep: str = "\n",
    **_ignored: object,
) -> Iterable[str] | str:
    """brio's restricted base-R-compatible spelling of :func:`write_lines`."""
    if not isinstance(con, (str, Path)):
        raise TypeError("Only file paths are supported by brio::writeLines()")
    return write_lines(text, con, sep)


__all__ = [
    "file_line_endings", "readLines", "read_file", "read_file_raw",
    "read_lines", "writeLines", "write_file", "write_file_raw", "write_lines",
]
