"""Remove output times that are numerically too close to an event."""

from __future__ import annotations

import numpy as np


def _nearest_event(times: np.ndarray, eventtimes: np.ndarray) -> np.ndarray:
    """Closest event time for each entry in ``times`` (internal helper)."""
    eventtimes = np.unique(eventtimes)
    times = np.sort(times)
    eventtimes = np.sort(eventtimes)
    if eventtimes.size == 0:
        return np.full(times.shape, np.nan, dtype=float)
    inearest = np.searchsorted(eventtimes, times, side="right") - 1
    lower_idx = np.maximum(inearest, 0)
    upper_idx = np.minimum(inearest + 1, eventtimes.size - 1)
    lower = eventtimes[lower_idx]
    upper = eventtimes[upper_idx]
    choose_lower = (times - lower) < (upper - times)
    return np.where(choose_lower, lower, upper)


def cleanEventTimes(
    times,
    eventtimes,
    eps: float | None = None,
):
    """Drop output times that are relatively closer than ``eps`` to an event."""
    if eps is None:
        eps = np.finfo(float).eps * 10.0
    times = np.sort(np.asarray(times, dtype=float).reshape(-1))
    nearest = _nearest_event(times, np.asarray(eventtimes, dtype=float).reshape(-1))
    div = np.maximum(times, nearest)
    div = np.where(div == 0.0, 1.0, div)
    reldiff = np.abs(times - nearest) / div
    too_close = reldiff < eps
    return times[~too_close]
