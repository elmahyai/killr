import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.as_shingle import as_shingle


def one():
    x = np.asarray([4.5, 2.1, 4.5, 7.8, 2.1], dtype=float)
    s = as_shingle(x)
    s2 = as_shingle(s)
    levels = np.asarray(s.levels, dtype=float).reshape(-1, order="C")
    flag = 1.0 if s2 is s else 0.0
    return np.concatenate(
        [
            np.asarray(s.values, dtype=float).reshape(-1),
            levels.reshape(-1, order="C"),
            np.asarray(s2.values, dtype=float).reshape(-1),
            np.asarray([flag], dtype=float),
        ]
    )


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
