"""Exponential distribution parameters from L-moments."""

from ._pel import call


def pelexp(xmom):
    """Return ``(location, scale)`` for an exponential fit."""
    return call("pel_exp", xmom, 2)
