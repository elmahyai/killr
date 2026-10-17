"""Clear the system clipboard."""

from __future__ import annotations

from typing import Any

from clipr.write_clip import write_clip


def clear_clip(**options: Any) -> Any:
    """Clear the clipboard by writing an empty string."""

    return write_clip("", **options)
