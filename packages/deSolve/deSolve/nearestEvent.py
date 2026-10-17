"""Closest event time for each output time."""

from __future__ import annotations

import numpy as np


def nearestEvent(times, eventtimes) -> np.ndarray:
    """Return the closest event for each time.

    Matches ``nearestEvent`` in deSolve 1.42. Times and event times are
    sorted, and missing values are dropped the way R's ``sort`` drops them.
    Duplicate event times collapse to one value. An equal distance selects
    the later event, because the comparison is strict.
    """
    times = np.asarray(times, dtype=float).reshape(-1)
    times = np.sort(times[~np.isnan(times)])
    eventtimes = np.asarray(eventtimes, dtype=float).reshape(-1)
    eventtimes = np.unique(eventtimes[~np.isnan(eventtimes)])
    if times.size == 0 or eventtimes.size == 0:
        return np.array([], dtype=float)
    # findInterval: last event at or before each time, clamped to the ends.
    inearest = np.searchsorted(eventtimes, times, side="right") - 1
    lower = eventtimes[np.maximum(inearest, 0)]
    upper = eventtimes[np.minimum(inearest + 1, eventtimes.size - 1)]
    choose_lower = (times - lower) < (upper - times)
    return np.where(choose_lower, lower, upper)
