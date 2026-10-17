"""md5sum and sha256sum. The digest is hashlib, which matches R's hex digest."""

from __future__ import annotations

import hashlib
import os
from typing import Any

from tools.file_ext import NA_character_

_MISSING = object()


def _digest(algorithm: str, files: Any = _MISSING, raw: Any = _MISSING) -> Any:
    if files is not _MISSING and raw is not _MISSING:
        raise ValueError("'files' and 'bytes' are mutually exclusive")
    if raw is not _MISSING:
        if not isinstance(raw, (bytes, bytearray)):
            raise ValueError("'bytes' must be a raw vector")
        return hashlib.new(algorithm, raw).hexdigest()
    if files is _MISSING:
        raise ValueError("argument \"files\" is missing, with no default")
    if isinstance(files, str):
        files = [files]
    result: dict[str, Any] = {}
    for item in files:
        path = os.path.expanduser(item)
        try:
            digest = hashlib.new(algorithm)
            with open(path, "rb") as handle:
                while True:
                    chunk = handle.read(1 << 20)
                    if not chunk:
                        break
                    digest.update(chunk)
            result[path] = digest.hexdigest()
        except OSError:
            result[path] = NA_character_
    return result


def md5sum(files: Any = _MISSING, bytes: Any = _MISSING) -> Any:
    """Hex MD5 of files, or of one raw vector. A missing file is NA."""
    return _digest("md5", files, bytes)


def sha256sum(files: Any = _MISSING, bytes: Any = _MISSING) -> Any:
    """Hex SHA-256 of files, or of one raw vector. A missing file is NA."""
    return _digest("sha256", files, bytes)
