import json
import statistics
import sys
import time

import numpy as np

sys.path[:0] = [
    "/home/ahmed/killr_projects/killr/packages/e1071",
    "/home/ahmed/killr_projects/killr/packages/boot",
    "/home/ahmed/killr_projects/killr/packages/MASS",
    "/home/ahmed/killr_projects/killr/packages/zoo",
]
from boot.rng import set_seed
from e1071.rwiener import rwiener


def one():
    set_seed(4242)
    series = rwiener(end=1, frequency=100)
    return np.asarray(series.data, dtype=float).reshape(-1).tolist()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
