"""Read one lattice option, matching ``lattice.getOption`` in lattice 0.23-1."""

from __future__ import annotations

from typing import Any

from lattice.lattice_options import lattice_options


def lattice_get_option(name: str) -> Any:
    """Return a single named lattice option (``lattice.getOption`` in R)."""
    selected = lattice_options(name)
    return selected.get(name)
