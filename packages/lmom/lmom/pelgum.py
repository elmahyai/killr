"""Gumbel distribution parameters from L-moments."""

from ._pel import call


def pelgum(xmom):
    """Return ``(location, scale)`` for a Gumbel fit."""
    return call("pel_gum", xmom, 2)
