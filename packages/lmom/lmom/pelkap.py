"""Kappa distribution parameters from L-moments."""

from ._pel import call


def pelkap(xmom):
    """Return ``(location, scale, kappa, h)`` for a Kappa fit."""
    return call("pel_kap", xmom, 4)
