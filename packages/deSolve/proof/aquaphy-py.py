import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.aquaphy import aquaphy_derivative_pack

parameters = np.array(
    [
        0.125,
        0.001,
        -0.125 / 150,
        0.0,
        0.136,
        1.0,
        0.05,
        0.15,
        0.075,
        0.23,
        0.0001,
        0.4,
        0.06,
        0.01,
        0.2,
        10.0,
        1.0,
        250.0,
        15.0,
    ],
    dtype=np.float64,
)

state = np.array([6.0, 20.0, 5.0, 1.0], dtype=np.float64)
eval_times = np.array([i * 0.5 for i in range(int(48 / 0.5) + 1)], dtype=np.float64)


def one():
    return aquaphy_derivative_pack(eval_times, state, parameters)


value = one()
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
