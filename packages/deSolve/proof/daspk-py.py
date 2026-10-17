import json
import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")

import numpy as np

from deSolve.daspk import daspk


def decay(t, y, parms):
    return [float(-0.5 * y[0])]


def one():
    return daspk(
        np.array([10.0]),
        np.arange(0, 6, 1, dtype=np.float64),
        {},
        func=decay,
        rtol=1e-8,
        atol=1e-8,
    )


value = np.ravel(np.asarray(one().data, dtype=np.float64), order="F").tolist()

elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append(time.perf_counter() - t0)

print(
    json.dumps(
        {
            "value": value,
            "median_ms": statistics.median(elapsed) * 1000,
        }
    )
)
