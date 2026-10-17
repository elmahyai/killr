"""Defunct gtools ``sprint`` export (gtools 3.9.5)."""

from __future__ import annotations

from typing import Any


def sprint(x: Any, *args: Any, **kwargs: Any) -> None:
    """Defunct printer wrapper; the call always fails like R ``.Defunct``."""
    raise RuntimeError(
        "'sprint' is defunct.\n"
        "Use 'capture.output' instead.\n"
        'See help("Defunct") and help("base-defunct").'
    )
