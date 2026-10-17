"""Add lines to an L-moment ratio diagram (lmom::lmrdlines)."""

from __future__ import annotations

from .lmrdpoints import lmrdpoints


def lmrdlines(x, y=None, type="l", ax=None, **kwargs):
    """Same as ``lmrdpoints`` with ``type = "l"``, as in R."""
    return lmrdpoints(x, y, type=type, ax=ax, **kwargs)
