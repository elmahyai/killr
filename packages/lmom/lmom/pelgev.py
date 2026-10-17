"""Generalized extreme-value parameters from L-moments."""

from ._pel import call


def pelgev(xmom):
    """Return ``(location, scale, shape)`` for a GEV fit."""
    return call("pel_gev", xmom, 3)
