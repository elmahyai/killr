import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.remlscoregamma import remlscoregamma


def _collect(out):
    return np.concatenate(
        [
            out["beta"],
            out["se.beta"],
            out["gamma"],
            out["se.gam"],
            out["mu"],
            out["phi"],
            [out["deviance"]],
            out["h"],
        ]
    )


def one():
    y = np.array(
        [
            43.7,
            40.2,
            42.4,
            44.7,
            42.4,
            45.9,
            42.2,
            40.6,
            42.4,
            45.5,
            43.6,
            40.6,
            44,
            40.2,
            42.5,
            46.5,
        ]
    )
    drying = np.array([-1, -1, 1, 1, 1, 1, -1, -1, 1, 1, -1, -1, -1, -1, 1, 1])
    material = np.array([-1, 1, 1, -1, 1, -1, -1, 1, 1, -1, -1, 1, -1, 1, 1, -1])
    method = np.array([-1, -1, 1, 1, -1, -1, 1, 1, -1, -1, 1, 1, -1, -1, 1, 1])
    preheating = np.array([-1, 1, -1, 1, 1, -1, 1, -1, 1, -1, 1, -1, -1, 1, -1, 1])
    x = np.column_stack([np.ones(16), (drying + 1) / 2, (material + 1) / 2])
    z = np.column_stack(
        [np.ones(16), (material + 1) / 2, (method + 1) / 2, (preheating + 1) / 2]
    )
    return _collect(remlscoregamma(y, x, z))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
