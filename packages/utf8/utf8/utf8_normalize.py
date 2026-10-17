"""Unicode normalization with the maps utf8_normalize applies before NFC."""

from __future__ import annotations

from typing import Any

from utf8._text import normalize_text
from utf8.as_utf8 import as_utf8


def utf8_normalize(
    x: Any,
    *,
    map_case: bool = False,
    map_compat: bool = False,
    map_quote: bool = False,
    remove_ignorable: bool = False,
) -> Any:
    """Compose text to NFC after the requested case, compatibility, quote, and ignorable maps."""

    converted = as_utf8(x, normalize=False)
    if converted is None:
        return None

    def one(text: str) -> str:
        return normalize_text(
            text,
            map_case=map_case,
            map_compat=map_compat,
            map_quote=map_quote,
            remove_ignorable=remove_ignorable,
        )

    if isinstance(converted, str):
        return one(converted)
    return [one(item) for item in converted]
