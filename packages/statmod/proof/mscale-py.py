import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.mscale import mscale


def one():
    u1 = np.array(
        [
            -2.1,
            -1.4,
            -0.9,
            -0.3,
            0.05,
            0.2,
            0.55,
            0.9,
            1.3,
            1.8,
            -0.7,
            0.1,
            0.4,
            0.75,
            12,
            -9,
            0.25,
            -0.15,
            0.6,
            2.2,
        ],
        dtype=float,
    )
    u2 = np.array([-1.1, 0.3, np.nan, 0.8, -0.4, 1.5, -2.0, 0.0, 0.2, np.nan], dtype=float)
    u3 = np.array([0, 0, 0, 0, 0, 1.2, -0.5], dtype=float)
    u4 = np.array([np.nan, np.nan], dtype=float)
    return np.array(
        [
            mscale(u1),
            mscale(u2),
            mscale(u2, na_rm=True),
            mscale(u3),
            mscale(u4),
            mscale(u4, na_rm=True),
        ],
        dtype=float,
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
