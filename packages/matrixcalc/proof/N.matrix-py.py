import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.n_matrix import n_matrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def _vec(array):
    return np.asarray(array, dtype=float).reshape(-1, order="F")


def one():
    n3 = n_matrix(3)
    n4 = n_matrix(4)
    a = np.arange(1, 10, dtype=float).reshape(3, 3, order="C")
    vec_a = _vec(a)
    y = n3 @ vec_a
    parts = [
        n3.reshape(-1, order="F"),
        n4.reshape(-1, order="F"),
        y.reshape(-1, order="F"),
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
