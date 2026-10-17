"""Locate the text time zone database shipped in the tzdb tarball."""

from __future__ import annotations

import os
import sys
import tarfile
from pathlib import Path

_TARBALL = "tzdb_0.5.0.tar.gz"
_PREFIX = "tzdb/inst/tzdata/"
_MISSING = "no file found"


def _chr_reencode(path: str) -> str:
    """``enc2utf8`` on Windows and ``enc2native`` elsewhere."""
    if os.name == "nt":
        return path.encode("utf-8", errors="surrogateescape").decode("utf-8")
    encoding = sys.getfilesystemencoding() or "utf-8"
    return path.encode(encoding, errors="surrogateescape").decode(encoding)


def _tarball() -> Path | None:
    here = Path(__file__).resolve()
    for parent in (here, *here.parents):
        candidate = parent / "cran" / "contrib" / _TARBALL
        if candidate.is_file():
            return candidate
    return None


def _cache_dir() -> Path:
    return Path.home() / ".cache" / "killr" / "tzdb" / "0.5.0" / "tzdata"


def _extract(tarball: Path, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tarball, "r:gz") as archive:
        for member in archive.getmembers():
            name = member.name
            if not name.startswith(_PREFIX):
                continue
            relative = name[len(_PREFIX) :]
            if not relative or relative.endswith("/"):
                continue
            parts = Path(relative).parts
            if ".." in parts:
                continue
            target = dest.joinpath(*parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if not member.isfile():
                continue
            source = archive.extractfile(member)
            if source is None:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(source.read())


def text_database_dir() -> str:
    """Directory of the text database, as ``system.file("tzdata", package = "tzdb")``."""
    cache = _cache_dir()
    if (cache / "version").is_file() and (cache / "africa").is_file():
        return _chr_reencode(str(cache))
    tarball = _tarball()
    if tarball is None:
        raise FileNotFoundError(_MISSING)
    _extract(tarball, cache)
    if not (cache / "version").is_file():
        raise FileNotFoundError(_MISSING)
    return _chr_reencode(str(cache))
