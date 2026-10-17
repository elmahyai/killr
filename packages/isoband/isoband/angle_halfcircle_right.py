"""Label angles in (0, pi], as R's ``angle_halfcircle_right()`` in isoband 0.3.0.

The returned adjuster maps each angle to the equivalent angle in (0, pi].
"""

from __future__ import annotations

import numpy as np


def angle_halfcircle_right():
    def adjust(theta) -> np.ndarray:
        t = np.asarray(theta, dtype=np.float64)
        return np.where(t <= 0, t + np.pi, np.where(t > np.pi, t - np.pi, t))

    return adjust
