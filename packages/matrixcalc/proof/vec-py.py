import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.vec import vec


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.arange(1, 17, dtype=float).reshape(4, 4, order="C")
    b = np.array(
        [[0.1, -1.5, 2.25], [4, 0.5, -0.25], [8, 3, 1.125]],
        dtype=float,
    )
    c = np.arange(1, 13, dtype=int).reshape(3, 4, order="F")
    d = np.zeros((5, 7), dtype=float)
    np.fill_diagonal(d, np.arange(1, 6, dtype=float) / 3)
    e = np.zeros((0, 4), dtype=float)
    f = np.array([[3.5]], dtype=float)
    parts = [vec(a), vec(b), vec(c), vec(d), vec(e), vec(f)]
    return np.concatenate([part.reshape(-1, order="F") for part in parts])


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
