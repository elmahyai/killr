"""Generalized logistic parameters from L-moments."""

from ._pel import call


def pelglo(xmom):
    """Return ``(location, scale, shape)`` for a generalized logistic fit."""
    return call("pel_glo", xmom, 3)
