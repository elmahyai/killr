"""Simulate protanomaly color vision deficiency."""

from colorspace.interpolate_cvd_transform import interpolate_cvd_transform
from colorspace.protanomaly_cvd import protanomaly_cvd
from colorspace.simulate_cvd import simulate_cvd


def protan(col, severity=1, linear=True):
    """Simulate protanomaly by severity in ``[0, 1]``."""
    transform = interpolate_cvd_transform(protanomaly_cvd(), severity)
    return simulate_cvd(col, transform, linear=linear)
