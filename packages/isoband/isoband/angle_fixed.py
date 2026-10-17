"""Fixed label angles, as R's ``angle_fixed()`` in isoband 0.3.0.

``angle_fixed(theta=0)`` returns an adjuster. Calling the adjuster with ``x``
gives ``theta`` recycled to ``len(x)``, the same as R's ``rep_len()``.
"""

from __future__ import annotations

import numpy as np


def angle_fixed(theta=0.0):
    theta_arr = np.asarray(theta, dtype=np.float64).reshape(-1)

    def adjust(x) -> np.ndarray:
        n = np.asarray(x).size
        if theta_arr.size == 0:
            return np.full(n, np.nan)  # R's rep_len() of nothing gives NA
        if theta_arr.size == 1:
            return np.full(n, theta_arr[0])
        return theta_arr[np.arange(n) % theta_arr.size]

    return adjust
