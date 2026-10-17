"""Pearson type III parameters from L-moments."""

from ._pel import call


def pelpe3(xmom):
    """Return ``(location, scale, skew)`` for a Pearson III fit."""
    return call("pel_pe3", xmom, 3)
