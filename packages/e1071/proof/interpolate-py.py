import json
import math
import statistics
import sys
import time

sys.path[:0] = ["/home/ahmed/killr_projects/killr/packages/e1071"]
from e1071.interpolate import interpolate


def _outer_z(x):
    z = [[math.sin(x[i] * x[j]) for j in range(len(x))] for i in range(len(x))]
    flat = []
    ncol = len(x)
    nrow = len(x)
    for j in range(ncol):
        for i in range(nrow):
            flat.append(z[i][j])
    return {"data": flat, "dim": (nrow, ncol), "dimnames": [x, x]}


def one():
    x = [i * 0.2 for i in range(16)]
    z = _outer_z(x)
    return list(interpolate([1.1, 2.1], z))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
