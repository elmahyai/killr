import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_zoo import as_zoo_default


def one():
    x = as_zoo_default([4, 5])
    m = as_zoo_default(np.arange(1, 5, dtype=np.int32).reshape((2, 2), order="F"), frequency=1)
    q = as_zoo_default(np.arange(1, 5), frequency=4)
    big = as_zoo_default(np.arange(1, 100001, dtype=np.int32))
    parts = [
        np.asarray(x.data, dtype=float).reshape(-1),
        np.asarray(x.index, dtype=float).reshape(-1),
        np.asarray(m.data, dtype=float).reshape(-1, order="F"),
        np.asarray(m.index, dtype=float).reshape(-1),
        [m.frequency],
        np.asarray(q.index, dtype=float).reshape(-1),
        [q.frequency],
        [float(np.sum(np.asarray(big.data, dtype=np.float64)))],
    ]
    return np.concatenate([np.asarray(p, dtype=float).reshape(-1) for p in parts])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
