"""Names that look like S3 methods and are not. The table is tools 4.5.0."""

from __future__ import annotations

import json
from pathlib import Path

_STOP = json.loads((Path(__file__).with_name("nons3.json")).read_text())


def non_s3_methods(package: str | None) -> list[str]:
    """The stop-list for one package, or every name when package is NULL."""
    if package is None:
        return [name for names in _STOP.values() for name in names]
    found = _STOP.get(package)
    if not found:
        return []
    return list(found)
