"""Label angles in (-pi/2, pi/2], as R's ``angle_halfcircle_bottom()`` in isoband 0.3.0.

The returned adjuster maps each angle to the equivalent angle in (-pi/2, pi/2].
"""

from __future__ import annotations

import numpy as np


def angle_halfcircle_bottom():
    def adjust(theta) -> np.ndarray:
        t = np.asarray(theta, dtype=np.float64)
        return np.where(t <= -np.pi / 2, t + np.pi, np.where(t > np.pi / 2, t - np.pi, t))

    return adjust
