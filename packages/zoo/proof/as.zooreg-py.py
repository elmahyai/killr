import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_zoo import Ts, as_zooreg, zoo_create


def one():
    tser = as_zooreg(Ts(np.arange(1, 9), start=(2000, 1), frequency=4))
    over = as_zooreg(Ts(np.arange(1, 5), start=2000, frequency=4), frequency=2)
    z = as_zooreg(zoo_create([1, 2, 4], order_by=[0, 2, 5]))
    big = as_zooreg(Ts(np.arange(1, 20001), start=1, frequency=1))
    parts = [
        np.asarray(tser.data, dtype=float).reshape(-1),
        np.asarray(tser.index, dtype=float).reshape(-1),
        [tser.frequency],
        np.asarray(over.index, dtype=float).reshape(-1),
        [over.frequency],
        np.asarray(z.data, dtype=float).reshape(-1),
        np.asarray(z.index, dtype=float).reshape(-1),
        [z.frequency],
        [float(np.sum(np.asarray(big.index, dtype=np.float64)))],
    ]
    return np.concatenate([np.asarray(p, dtype=float).reshape(-1) for p in parts])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
