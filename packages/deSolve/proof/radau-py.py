import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.radau import radau


def robertson(t, y, parms):
    dy1 = -0.04 * y[0] + 1e4 * y[1] * y[2]
    dy2 = 0.04 * y[0] - 1e4 * y[1] * y[2] - 3e7 * y[1] ** 2
    dy3 = 3e7 * y[1] ** 2
    return [[dy1, dy2, dy3]]


def one():
    return radau([1.0, 0.0, 0.0], [0.0, 10.0, 20.0, 30.0, 40.0], robertson, None)


value = np.ravel(one().data, order="F")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {
            "value": [float(item) for item in value],
            "median_ms": statistics.median(elapsed),
        }
    )
)
