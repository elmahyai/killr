import statistics
import time

import numpy as np

from mass.sammon import sammon


def one():
    pts = np.array(
        [
            [0, 1, 0.5],
            [3, 1, 1.5],
            [1, 2, 0.2],
            [4, 2, 1.1],
            [2, 0, 0.8],
            [5, 3, 1.2],
        ],
        dtype=float,
    )
    d = np.zeros((6, 6))
    for i in range(6):
        for j in range(i + 1, 6):
            diff = pts[i] - pts[j]
            dist = float(np.sqrt(np.dot(diff, diff)))
            d[i, j] = d[j, i] = dist
    y0 = np.array(
        [
            [-1.2, 0.5],
            [0.3, -0.8],
            [0.9, 0.2],
            [-0.4, 1.0],
            [1.1, -0.3],
            [-0.7, 0.6],
        ],
        dtype=float,
    )
    fit = sammon(d, y=y0, k=2, niter=100, trace=False)
    flat = np.asarray(fit["points"], dtype=float).reshape(-1, order="F")
    return np.concatenate([flat, [fit["stress"]]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
