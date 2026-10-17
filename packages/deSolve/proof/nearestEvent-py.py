import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.nearestEvent import nearestEvent

events = np.sort(
    np.array(
        [
            0,
            2,
            3,
            4 + 1e-10,
            5,
            7 - 1e-10,
            7 + 6e-15,
            7.5,
            9,
            24.9999,
            25,
            80,
            1001,
            1e300,
        ],
        dtype=float,
    )
)
times = np.sort(
    np.array(
        [
            0,
            *range(1, 8),
            4.5,
            6.75,
            7.5,
            9.2,
            9.0001,
            25,
            879,
            1e3,
            1e300 + 5,
        ],
        dtype=float,
    )
)


def one():
    return nearestEvent(times, events)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    json.dumps(
        {"value": [float(item) for item in value], "median_ms": statistics.median(elapsed)}
    )
)
