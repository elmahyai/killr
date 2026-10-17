"""Whittaker smoothing with a difference penalty."""

from __future__ import annotations

import numpy as np

from pracma.arrays import eye
from pracma.num_helpers import r_diff


def whittaker(y, lambda_=1600, d=2):
    series = np.asarray(y, dtype=float).reshape(-1)
    size = series.size
    identity = eye(size)
    penalty = r_diff(identity, differences=int(d))
    system = identity + float(lambda_) * (penalty.T @ penalty)
    return np.linalg.solve(system, series)
