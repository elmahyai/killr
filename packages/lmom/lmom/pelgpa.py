"""Generalized Pareto parameters from L-moments."""

from ._pel import call


def pelgpa(xmom):
    """Return ``(location, scale, shape)`` for a generalized Pareto fit."""
    return call("pel_gpa", xmom, 3)
