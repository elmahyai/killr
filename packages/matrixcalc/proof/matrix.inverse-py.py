import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.matrix_inverse import matrix_inverse


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def flatten(matrix):
    return np.asarray(matrix, dtype=float).reshape(-1, order="F")


def one():
    a = np.array([[1, 2], [2, 1]], dtype=float)
    b = np.array([[2, -1, -2], [-4, 6, 3], [-4, -2, 8]], dtype=float)
    c_int = np.arange(1, 5, dtype=int).reshape(2, 2, order="F")
    d = np.array([[7]], dtype=float)
    e = np.array([[True, True], [False, True]])
    big = np.zeros((64, 64), dtype=float)
    np.fill_diagonal(big, np.arange(1, 65, dtype=float) / 7)
    parts = [
        flatten(matrix_inverse(a)),
        flatten(matrix_inverse(b)),
        flatten(matrix_inverse(c_int)),
        flatten(matrix_inverse(d)),
        flatten(matrix_inverse(e)),
        flatten(matrix_inverse(big)),
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
