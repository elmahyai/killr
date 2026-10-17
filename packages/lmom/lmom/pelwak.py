"""Wakeby distribution parameters from L-moments."""

from ._pel import call


def pelwak(xmom):
    """Return ``(location, a, b, c, d)`` for a Wakeby fit."""
    return call("pel_wak", xmom, 5)
