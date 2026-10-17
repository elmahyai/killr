import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_date import as_date
from zoo.as_zoo import Ts


def one():
    d0 = np.asarray(as_date(0), dtype=float).reshape(-1)
    dv = np.asarray(as_date([0, 1, -1]), dtype=float).reshape(-1)
    ch = np.asarray(as_date("2000-01-01"), dtype=float).reshape(-1)
    dts = np.asarray(as_date(Ts(np.arange(1, 5), start=2000, frequency=4)), dtype=float).reshape(-1)
    big = np.asarray(as_date(np.arange(100000, dtype=float)), dtype=float)
    return np.concatenate([d0, dv, ch, dts, [float(np.sum(big))]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
