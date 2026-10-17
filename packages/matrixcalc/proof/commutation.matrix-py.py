import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.commutation_matrix import commutation_matrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def _vec(array):
    return np.asarray(array, dtype=float).reshape(-1, order="F")


def one():
    k34 = commutation_matrix(3, 4)
    k22 = commutation_matrix(2, 2)
    k33 = commutation_matrix(3)
    a = np.arange(1, 13, dtype=float).reshape(3, 4, order="C")
    vec_a = _vec(a)
    vec_at = _vec(a.T)
    parts = [
        k34.reshape(-1, order="F"),
        k22.reshape(-1, order="F"),
        k33.reshape(-1, order="F"),
        k34 @ vec_a,
        vec_at,
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
