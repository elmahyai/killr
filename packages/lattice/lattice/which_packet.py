"""Return conditioning levels for the active panel (``which.packet`` in lattice 0.23-1)."""

from __future__ import annotations

from typing import Any

from lattice.lattice_status import lattice_get_status


def which_packet(*, prefix: str | None = None) -> Any:
    """Numeric level indices for the conditioning variables at the current focus."""
    if prefix is None:
        prefix = lattice_get_status("current.prefix")
    cond_levels = lattice_get_status("current.cond.levels", prefix=prefix)
    row = int(lattice_get_status("current.focus.row", prefix=prefix) or 0)
    column = int(lattice_get_status("current.focus.column", prefix=prefix) or 0)
    if not cond_levels or row < 1 or column < 1:
        return None
    return cond_levels[row - 1][column - 1]
