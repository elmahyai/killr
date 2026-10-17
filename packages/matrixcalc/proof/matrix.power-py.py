import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.matrix_power import matrix_power


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
    big = np.zeros((48, 48), dtype=float)
    np.fill_diagonal(big, np.arange(1, 49, dtype=float) / 7)
    parts = [
        flatten(matrix_power(a, -2)),
        flatten(matrix_power(a, -1)),
        flatten(matrix_power(a, 0)),
        flatten(matrix_power(a, 1)),
        flatten(matrix_power(a, 2)),
        flatten(matrix_power(a, 3)),
        flatten(matrix_power(b, 4)),
        flatten(matrix_power(b, -1)),
        flatten(matrix_power(big, 2)),
    ]
    return np.concatenate(parts)


value = clean(one().tolist())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
