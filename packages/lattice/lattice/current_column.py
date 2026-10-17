"""Return the active panel column index (``current.column`` in lattice 0.23-1)."""

from __future__ import annotations

from typing import Any

from lattice.lattice_status import lattice_get_status


def current_column(*, prefix: str | None = None) -> Any:
    """Column index of the panel currently being drawn (1-based)."""
    if prefix is None:
        prefix = lattice_get_status("current.prefix")
    return lattice_get_status("current.focus.column", prefix=prefix)
