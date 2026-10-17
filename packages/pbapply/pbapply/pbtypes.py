"""Return supported progress bar type names."""

from __future__ import annotations

import sys


def pbtypes() -> list[str]:
    """Mirror pbapply::pbtypes."""
    types = ["timer", "txt", "tk", "none", "shiny"]
    if sys.platform == "win32":
        return [*types, "win"]
    return types
