"""OSC 8 hyperlinks."""

from __future__ import annotations

from typing import Any

from crayon._detect import has_hyperlink
from crayon._text import character_vector, one_or_many, paste0


def hyperlink(text: Any, url: Any) -> Any:
    if not has_hyperlink():
        values = character_vector(text)
        return one_or_many(values)
    opened = paste0("\x1b]8;;", url, "\x07", text, "\x1b]8;;\x07")
    return opened
