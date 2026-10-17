import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/zoo")
from zoo.as_date import as_date_numeric


def one():
    a = np.asarray(as_date_numeric([0, 1, -1], origin="2000-01-01"), dtype=float).reshape(-1)
    b = np.asarray(as_date_numeric(0, origin="0000-00-00"), dtype=float).reshape(-1)
    c = np.asarray(
        as_date_numeric(1, origin="01/02/2000", fmt="%d/%m/%Y"), dtype=float
    ).reshape(-1)
    d = np.asarray(as_date_numeric(0), dtype=float).reshape(-1)
    big = np.asarray(as_date_numeric(np.arange(100000, dtype=float)), dtype=float)
    return np.concatenate([a, b, c, d, [float(np.sum(big))]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(v) for v in value], "median_ms": statistics.median(elapsed)}))
