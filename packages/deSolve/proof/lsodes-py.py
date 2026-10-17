import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/deSolve")
from deSolve.lsodes import lsodes


def logist(t, x, parms):
    r = parms["r"]
    k = parms["K"]
    return [r * x[0] * (1 - x[0] / k)]


def one():
    out = lsodes(
        {"N": 0.1},
        list(range(0, 11, 2)),
        logist,
        {"r": 0.5, "K": 100.0},
        rtol=1e-8,
        atol=1e-8,
    )
    return np.ravel(out.data, order="F")


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
