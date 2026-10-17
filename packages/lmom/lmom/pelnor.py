"""Normal distribution parameters from L-moments."""

from ._pel import call


def pelnor(xmom):
    """Return ``(mean, standard deviation)`` for a normal fit."""
    return call("pel_nor", xmom, 2)
