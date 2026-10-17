import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.is_singular_matrix import is_singular_matrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.eye(3, dtype=float)
    b = np.array([[0, 0], [3, 4]], dtype=float)
    full = np.array([[1, 2], [3, 4]], dtype=float)
    singular = np.array([[1, 2], [2, 4]], dtype=float)
    tiny_det = np.array([[1e-9, 0], [0, 1]], dtype=float)
    above_tol = np.array([[1e-7, 0], [0, 1]], dtype=float)
    empty = np.empty((0, 0), dtype=float)
    na_case = np.array([[1, np.nan], [0, 2]], dtype=float)
    return [
        is_singular_matrix(a),
        is_singular_matrix(b),
        is_singular_matrix(full),
        is_singular_matrix(singular),
        is_singular_matrix(tiny_det),
        is_singular_matrix(above_tol),
        is_singular_matrix(empty),
        is_singular_matrix(np.array([[3.5]], dtype=float)),
        is_singular_matrix(np.array([[1, 2], [3, 4]], dtype=int)),
        is_singular_matrix(tiny_det, tol=1e-10),
        is_singular_matrix(na_case),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": clean(value), "median_ms": [statistics.median(elapsed)]}))
