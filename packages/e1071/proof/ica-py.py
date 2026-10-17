import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/packages/MASS",
]
from boot.rng import set_seed
from e1071.ica import ica


def one():
    set_seed(4242)
    x = np.array(
        [
            [0.2, 1.1, -0.4],
            [0.9, 0.5, -0.2],
            [1.3, 0.7, -0.8],
            [0.3, -0.1, 0.6],
        ],
        dtype=float,
    )
    fit = ica(x, lrate=0.05, epochs=15, ncomp=2, fun="negative")
    weights = np.asarray(fit["weights"], dtype=float).reshape(-1, order="F")
    projection = np.asarray(fit["projection"], dtype=float).reshape(-1, order="F")
    return list(weights) + list(projection)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
