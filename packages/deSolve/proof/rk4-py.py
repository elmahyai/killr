import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.rk4 import rk4


def logist(t, x, parms):
    r = parms["r"]
    k = parms["K"]
    dx = r * x[0] * (1.0 - x[0] / k)
    return [dx]


def one():
    out = rk4({"N": 0.1}, list(range(0, 101, 2)), logist, {"r": 0.5, "K": 100})
    return np.ravel(out.data, order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(item) for item in value], "median_ms": statistics.median(elapsed)}))
