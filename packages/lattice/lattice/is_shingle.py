"""Test for lattice shingle objects (lattice 0.23-1 ``is.shingle``)."""

from __future__ import annotations

from lattice.as_shingle import Shingle


def is_shingle(x):
    """Return whether ``x`` has R class ``shingle``."""
    return isinstance(x, Shingle)
