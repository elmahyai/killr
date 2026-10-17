import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/gtools")
from gtools.baseof import baseOf


def flat(x):
    array = np.asarray(x, dtype=np.int32)
    if array.size == 0:
        return []
    if array.ndim == 2:
        return array.reshape(-1, order="F").astype(float).tolist()
    return array.reshape(-1).astype(float).tolist()


def one():
    out = []
    out.extend(flat(baseOf(123)))
    out.extend(flat(baseOf(123, base=2)))
    out.extend(flat(baseOf(123, base=8)))
    out.extend(flat(baseOf(123, base=16)))
    out.extend(flat(baseOf(123, len=5)))
    out.extend(flat(baseOf([0, 1, 255, 256], base=2, len=4)))
    out.extend(flat(baseOf([5, 123, 4096], base=16)))
    out.extend(flat(baseOf([10, 1000], base=10)))
    out.extend(flat(baseOf(np.array([], dtype=np.int32))))
    return out


one()
value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
