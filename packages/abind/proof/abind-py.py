import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/abind")
from abind.abind import abind


def one():
    x = np.arange(1, 241).reshape((15, 16), order="F")
    y = np.arange(241, 481).reshape((15, 16), order="F")
    parts = [
        abind(x, y, along=1.5),
        abind(x, y, along=1),
        abind(x, y, along=2),
        abind(x, y, along=0),
    ]
    dims = []
    values = []
    for part in parts:
        data = np.asarray(part.data, dtype=float)
        dims.extend(float(size) for size in data.shape)
        values.extend(float(value) for value in np.ravel(data, order="F"))
    return dims + values


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
