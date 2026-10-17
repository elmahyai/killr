"""Whole files and lines."""

from __future__ import annotations

from pathlib import Path

from readr.locale import default_locale
from readr.read import I, _source_text
from readr.write import write_file, write_lines


def read_lines(file, skip=0, skip_empty_rows=False, n_max=float("inf"), locale=None, na=(), lazy=None, num_threads=None, progress=None):
    """One string per line, without the line ending."""
    loc = locale or default_locale()
    text, _label, _many = _source_text(file, loc.encoding)
    lines = text.splitlines()
    if skip:
        lines = lines[int(skip):]
    if skip_empty_rows:
        lines = [line for line in lines if line != ""]
    if n_max is not None and n_max != float("inf") and int(n_max) >= 0:
        lines = lines[: int(n_max)]
    missing = tuple(na)
    return [None if line in missing else line for line in lines]


def read_lines_raw(file, skip=0, n_max=float("inf"), progress=None):
    """Each line as a list of byte values, without the line ending."""
    raw = _raw(file)
    lines = raw.splitlines()
    if skip:
        lines = lines[int(skip):]
    if n_max is not None and n_max != float("inf") and int(n_max) >= 0:
        lines = lines[: int(n_max)]
    return [list(line) for line in lines]


def read_lines_chunked(file, callback, chunk_size=10000, skip=0, progress=None):
    from readr.callback import run_chunks
    from readr.read import Table

    lines = read_lines(file, skip=skip)
    return run_chunks(Table(["line"], [lines], len(lines)), callback, chunk_size)


def read_lines_raw_chunked(file, callback, chunk_size=10000, skip=0, progress=None):
    from readr.callback import run_chunks
    from readr.read import Table

    lines = read_lines_raw(file, skip=skip)
    return run_chunks(Table(["raw"], [lines], len(lines)), callback, chunk_size)


def read_file(file, locale=None):
    """The whole file as one string."""
    loc = locale or default_locale()
    if isinstance(file, (bytes, bytearray)) and len(file) == 0:
        return ""
    if isinstance(file, str) and "\n" not in file and Path(file).is_file() and Path(file).stat().st_size == 0:
        return ""
    text, _label, _many = _source_text(file, loc.encoding)
    return text


def read_file_raw(file):
    """The whole file as a list of byte values."""
    raw = _raw(file)
    return list(raw)


def _raw(file) -> bytes:
    if isinstance(file, (bytes, bytearray)):
        return bytes(file)
    if isinstance(file, str) and "\n" not in file and Path(file).is_file():
        from readr.read import _load_bytes

        return _load_bytes(file)
    if isinstance(file, str):
        return file.encode("utf-8")
    raise TypeError("Unknown input to `file`")


__all__ = [
    "read_file",
    "read_file_raw",
    "read_lines",
    "read_lines_chunked",
    "read_lines_raw",
    "read_lines_raw_chunked",
    "write_file",
    "write_lines",
]
