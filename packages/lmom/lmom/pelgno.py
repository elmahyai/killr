"""Generalized normal parameters from L-moments."""

from ._pel import call


def pelgno(xmom):
    """Return ``(location, scale, shape)`` for a generalized normal fit."""
    return call("pel_gno", xmom, 3)
