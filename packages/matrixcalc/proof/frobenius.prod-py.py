import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.frobenius_prod import frobenius_prod


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    return value


def one():
    ex_x = np.array([[1, 2], [3, 4]], dtype=float)
    ex_y = np.array([[2, 4], [6, 8]], dtype=float)
    x = np.arange(1, 5, dtype=float).reshape(4, 1)
    y = np.arange(5, 9, dtype=float).reshape(4, 1)
    a = np.arange(1, 7, dtype=float).reshape(2, 3, order="C")
    b = np.arange(11, 17, dtype=float).reshape(2, 3, order="C")
    u = np.array([0.25, -1.5, 2], dtype=float)
    v = np.array([4, 0.5, -0.125], dtype=float)
    return [
        frobenius_prod(ex_x, ex_y),
        frobenius_prod(x, y),
        frobenius_prod(a, b),
        frobenius_prod(u, v),
        frobenius_prod(np.array([[1, 2]], dtype=float), np.array([[3, 4]], dtype=float)),
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
