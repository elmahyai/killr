import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.combinations import combinations


def flat(x):
    array = np.asarray(x)
    if array.size == 0:
        return []
    if array.ndim == 2:
        return array.reshape(-1, order="F").astype(float).tolist()
    return array.reshape(-1).astype(float).tolist()


def one():
    out = []
    out.extend(flat(combinations(15, 4)))
    out.extend(flat(combinations(6, 3, repeats_allowed=True)))
    out.extend(flat(combinations(10, 3)))
    return out


one()
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
