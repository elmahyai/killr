import json
import math
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.as_shingle import as_shingle
from lattice.equal_count import equal_count
from lattice.is_shingle import is_shingle


def one():
    x = np.asarray([-1.2, 0.5, 0.5, 1.8, 3.1, 3.1, 5.0, -1.2, 2.4], dtype=float)
    z = equal_count(x, number=5, overlap=0.4)
    levels = np.asarray(z.levels, dtype=float).reshape(-1, order="C")
    same = 1.0 if as_shingle(z) is z else 0.0
    flag = 1.0 if is_shingle(z) else 0.0
    return np.concatenate(
        [
            np.asarray(z.values, dtype=float).reshape(-1),
            levels.reshape(-1, order="C"),
            np.asarray([flag, same], dtype=float),
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
