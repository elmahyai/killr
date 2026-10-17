import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.s_op import s_op


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    x = np.arange(1, 5, dtype=float).reshape(-1, 1)
    y = np.arange(5, 9, dtype=float).reshape(-1, 1)
    a = np.arange(1, 7, dtype=float).reshape(2, 3)
    b = np.arange(11, 17, dtype=float).reshape(2, 3)
    u = np.array([0.25, -1.5, 2], dtype=float)
    v = np.array([4, 0.5, -0.125], dtype=float)
    m = np.array([[0.1, -1.5], [2.25, 4], [0.5, -0.25]], dtype=float)
    w = np.array([9, 8, 7, 6], dtype=float)
    s = np.array([[1, 2], [3, 4]], dtype=float)
    parts = [
        s_op(x, y),
        s_op(a, b),
        s_op(u, v),
        s_op(np.array([[1, 2]], dtype=float), np.array([[3, 4]], dtype=float)),
        s_op(m, w),
        s_op(2.5, s),
    ]
    return np.concatenate([part.reshape(-1, order="F") for part in parts])


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
