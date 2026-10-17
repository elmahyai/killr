import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.entrywise_norm import entrywise_norm


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.array([[3, 5, 7], [2, 6, 4], [0, 2, 8]], dtype=float)
    b = np.arange(1, 13, dtype=float).reshape(3, 4, order="C")
    u = np.array([0.25, -1.5, 2.75, 4.0], dtype=float)
    v = np.arange(1, 7, dtype=float).reshape(2, 3, order="C")
    return [
        entrywise_norm(a, 2),
        entrywise_norm(a, float("inf")),
        entrywise_norm(b, 1),
        entrywise_norm(u, 3),
        entrywise_norm(v, 1.5),
        entrywise_norm(np.arange(1, 5, dtype=float), 1),
        entrywise_norm(np.zeros((0, 0), dtype=float), 2),
        entrywise_norm(np.array([], dtype=float), 4),
    ]


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
