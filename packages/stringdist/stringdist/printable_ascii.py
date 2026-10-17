"""Detect printable ASCII from stringdist ``printable_ascii``."""

from __future__ import annotations

from stringdist.stringdist import _as_character, _printable

__all__ = ["printable_ascii"]


def printable_ascii(x):
    """Whether each element consists solely of printable ASCII characters."""
    warn = [False]
    strings = _as_character(x, warn)
    return [_printable(text) for text in strings]
