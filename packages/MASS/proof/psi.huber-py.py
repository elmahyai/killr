import statistics
import time

import numpy as np

from mass.psi_huber import psi_huber


def one():
    u = np.array([-4.0, -1.345, -0.5, 0.0, 0.5, 1.345, 4.0])
    return np.concatenate(
        [
            np.asarray(psi_huber(u), dtype=float).reshape(-1),
            np.asarray(psi_huber(u, deriv=1), dtype=float).reshape(-1),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
