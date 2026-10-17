import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.matvec import matvec


def one():
    a = np.arange(1, 13, dtype=float).reshape(3, 4, order="F")
    rows = np.repeat(np.arange(1, 101, dtype=float), 50)
    cols = np.tile(np.arange(1, 51, dtype=float), 100)
    m = (rows + cols / 100.0).reshape(100, 50, order="F")
    v = np.arange(1, 51, dtype=float) / 7.0
    return np.concatenate(
        [
            matvec(a, [1, 2, 3, 4]).reshape(-1, order="F"),
            matvec(m, v).reshape(-1, order="F"),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(x) for x in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
