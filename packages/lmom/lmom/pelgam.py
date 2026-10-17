"""Gamma distribution parameters from L-moments."""

from ._pel import call


def pelgam(xmom):
    """Return ``(shape, scale)`` for a gamma fit."""
    return call("pel_gam", xmom, 2)
