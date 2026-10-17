import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.d_matrix import d_matrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def _vec(array):
    return np.asarray(array, dtype=float).reshape(-1, order="F")


def _vech(array):
    array = np.asarray(array, dtype=float)
    n = array.shape[0]
    parts = []
    for j in range(n):
        for i in range(j, n):
            parts.append(array[i, j])
    return np.asarray(parts, dtype=float)


def one():
    d3 = d_matrix(3)
    a = np.array(
        [[1, 2, 3], [2, 3, 4], [3, 4, 5]],
        dtype=float,
    )
    vec_a = _vec(a)
    vech_a = _vech(a)
    y = d3 @ vech_a
    d4 = d_matrix(4)
    parts = [
        d3.reshape(-1, order="F"),
        y.reshape(-1, order="F"),
        vec_a.reshape(-1, order="F"),
        d4.reshape(-1, order="F"),
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
