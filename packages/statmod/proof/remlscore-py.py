import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.remlscore import remlscore


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
            out["cov.beta"].reshape(-1, order="F"),
            out["cov.gam"].reshape(-1, order="F"),
            [out["iter"]],
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
    x = np.column_stack(
        [
            np.ones(16),
            np.array([0, 0, 1, 1, 1, 1, 0, 0, 1, 1, 0, 0, 0, 0, 1, 1]),
            np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0]),
        ]
    )
    z = np.column_stack(
        [
            np.ones(16),
            np.array([0, 1, 1, 0, 1, 0, 0, 1, 1, 0, 0, 1, 0, 1, 1, 0]),
            np.array([0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1, 0, 0, 1, 1]),
            np.array([0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 1, 0, 0, 1, 0, 1]),
        ]
    )
    out1 = remlscore(y, x, z)
    y2 = np.array([2.1, 3.4, 1.8, 4.2, 2.9, 3.1, 2.5, 3.8])
    x2 = np.column_stack([np.ones(8), [0, 1, 0, 1, 0, 1, 0, 1]])
    z2 = np.column_stack([np.ones(8), [1, 1, 0, 0, 1, 1, 0, 0]])
    out2 = remlscore(y2, x2, z2)
    return np.concatenate([_collect(out1), _collect(out2)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
