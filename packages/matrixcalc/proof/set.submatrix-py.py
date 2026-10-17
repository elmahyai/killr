import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.set_submatrix import set_submatrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    x = np.arange(1, 17, dtype=float).reshape(4, 4)
    y = np.arange(1, 5, dtype=float).reshape(2, 2)
    a = np.arange(1, 25, dtype=float).reshape(6, 4)
    b = np.array([[0.1, -1.5, 2.25], [4, 0.5, -0.25]], dtype=float)
    cmat = np.arange(1, 26, dtype=float).reshape(5, 5)
    d = np.array([[7.125]], dtype=float)
    e = np.arange(1, 19, dtype=float).reshape(3, 6)
    f = np.array([[9, 8], [7, 6]], dtype=float)
    parts = [
        set_submatrix(x, y, 3, 3),
        set_submatrix(a, b, 1, 1),
        set_submatrix(cmat, d, 5, 5),
        set_submatrix(e, f, 2, 4),
    ]
    return np.concatenate([part.reshape(-1, order="F") for part in parts])


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
