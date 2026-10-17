"""Read the system clipboard into a list of strings."""

from __future__ import annotations

import warnings
from typing import Any

from clipr._clipboard import EMPTY_MESSAGE, read_clipboard, require_access


def read_clip(allow_non_interactive: Any = None) -> list[str] | None:
    """Read the clipboard into a list of strings.

    Returns None when the clipboard has no readable text. A non-interactive
    session is refused unless allow_non_interactive is True or CLIPR_ALLOW is
    the string TRUE.
    """

    require_access(allow_non_interactive)
    content = read_clipboard()
    if len(content) == 0:
        warnings.warn(EMPTY_MESSAGE, stacklevel=2)
        return None
    return content
