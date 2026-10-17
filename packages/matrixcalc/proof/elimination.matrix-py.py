import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.elimination_matrix import elimination_matrix


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


def _lower_triangle(array):
    array = np.asarray(array, dtype=float).copy()
    n = array.shape[0]
    for i in range(n):
        for j in range(i + 1, n):
            array[i, j] = 0.0
    return array


def one():
    l3 = elimination_matrix(3)
    a = _lower_triangle(np.arange(1, 10, dtype=float).reshape(3, 3, order="C"))
    vec_a = _vec(a)
    vech_a = _vech(a)
    y = l3 @ vec_a
    l4 = elimination_matrix(4)
    parts = [
        l3.reshape(-1, order="F"),
        y.reshape(-1, order="F"),
        vec_a.reshape(-1, order="F"),
        vech_a.reshape(-1, order="F"),
        l4.reshape(-1, order="F"),
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
