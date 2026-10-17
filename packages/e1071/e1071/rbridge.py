"""Simulated Brownian bridge (e1071 ``rbridge``)."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

from zoo.as_zoo import Ts, ts_time


def _norm_rand():
    try:
        from mass._r_rng import norm_rand
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "MASS"))
        from mass._r_rng import norm_rand
    return norm_rand()


def _rwiener(end=1, frequency=1000):
    count = int(end * frequency)
    scale = 1.0 / float(frequency) ** 0.5
    increments = np.array([_norm_rand() * scale for _ in range(count)], dtype=float)
    values = np.cumsum(increments)
    start = 1.0 / float(frequency)
    return Ts(values, start=start, frequency=frequency)


def rbridge(end=1, frequency=1000):
    """Simulate a Brownian bridge on ``[0, end]`` as a time series."""
    path = _rwiener(end=end, frequency=frequency)
    times = ts_time(path)
    series = np.asarray(path.data, dtype=float).reshape(-1)
    terminal = float(series[int(frequency) - 1])
    bridge = series - times * terminal
    start = 1.0 / float(frequency)
    return Ts(bridge, start=start, frequency=frequency)
