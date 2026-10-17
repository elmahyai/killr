import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/lattice")
from lattice.as_shingle import as_shingle
from lattice.is_shingle import is_shingle


def one():
    x = np.asarray([4.5, 2.1, 4.5, 7.8, 2.1], dtype=float)
    s = as_shingle(x)
    return np.asarray([float(is_shingle(s)), float(is_shingle(x))], dtype=float)


value = one().tolist()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
