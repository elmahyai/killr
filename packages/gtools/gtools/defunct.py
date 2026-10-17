"""Defunct gtools exports (gtools 3.9.5)."""

from __future__ import annotations

from typing import Any


def _assert(*_args: Any, **_kwargs: Any) -> None:
    """Defunct synonym for R ``stopifnot``; the call always fails."""
    raise RuntimeError(
        "'assert' is defunct.\n"
        "Use 'stopifnot' instead.\n"
        'See help("Defunct") and help("base-defunct").'
    )


def __getattr__(name: str):
    if name == "assert":
        return _assert
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
