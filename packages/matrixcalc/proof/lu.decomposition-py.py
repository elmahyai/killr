import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.lu_decomposition import lu_decomposition


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def flatten_lu(lu):
    return np.concatenate(
        [
            np.asarray(lu["L"], dtype=float).reshape(-1, order="F"),
            np.asarray(lu["U"], dtype=float).reshape(-1, order="F"),
        ]
    )


def one():
    a = np.array([[1, 2], [2, 1]], dtype=float)
    b = np.array([[2, -1, -2], [-4, 6, 3], [-4, -2, 8]], dtype=float)
    c_int = np.arange(1, 5, dtype=int).reshape(2, 2, order="F")
    d = np.array([[7]], dtype=float)
    parts = [
        flatten_lu(lu_decomposition(a)),
        flatten_lu(lu_decomposition(b)),
        flatten_lu(lu_decomposition(c_int)),
        flatten_lu(lu_decomposition(d)),
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
