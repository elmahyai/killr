"""Simulate tritanomaly color vision deficiency (colorspace 2.1-4)."""

from __future__ import annotations

from colorspace.interpolate_cvd_transform import interpolate_cvd_transform
from colorspace.simulate_cvd import simulate_cvd
from colorspace.tritanomaly_cvd import tritanomaly_cvd


def tritan(col, severity=1, linear=True):
    """Simulate tritanomaly by severity in ``[0, 1]`` (default dichromacy)."""
    transform = interpolate_cvd_transform(tritanomaly_cvd(), severity)
    return simulate_cvd(col, transform, linear=linear)
