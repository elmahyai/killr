"""Trim indentation the way glue trims a template."""

from __future__ import annotations

from typing import Any

from glue._text import Glue, character_vector
from glue._trim import trim_text


def trim(x: Any) -> Any:
    """Trim one string, or each string of a vector, using glue's indent rules."""

    if isinstance(x, str):
        return trim_text(x)
    values = character_vector(x)
    if values is None:
        return Glue(())
    return Glue(tuple(trim_text("" if item is None else str(item)) for item in values))
