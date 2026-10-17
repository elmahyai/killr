import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.is_skew_symmetric_matrix import is_skew_symmetric_matrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.eye(3, dtype=float)
    b = np.array([[0, -2, -1], [-2, 0, -4], [1, 4, 0]], dtype=float)
    c = np.array([[0, 2, 1], [2, 0, 4], [1, 4, 0]], dtype=float)
    d = np.array([[1, 2], [3, 4]], dtype=float)
    near = np.array([[0, -1 + 1e-9], [1, 0]], dtype=float)
    far = np.array([[0, -1 + 1e-7], [1, 0]], dtype=float)
    empty = np.zeros((0, 0), dtype=float)
    na_case = np.array([[0, np.nan], [0, 0]], dtype=float)
    nan_case = np.array([[0, np.nan], [0, 0]], dtype=float)
    inf_case = np.array([[0, np.inf], [-np.inf, 0]], dtype=float)
    return [
        is_skew_symmetric_matrix(a),
        is_skew_symmetric_matrix(b),
        is_skew_symmetric_matrix(c),
        is_skew_symmetric_matrix(d),
        is_skew_symmetric_matrix(near),
        is_skew_symmetric_matrix(far),
        is_skew_symmetric_matrix(empty),
        is_skew_symmetric_matrix(np.array([[3.5]], dtype=float)),
        is_skew_symmetric_matrix(na_case),
        is_skew_symmetric_matrix(nan_case),
        is_skew_symmetric_matrix(inf_case),
        is_skew_symmetric_matrix(np.zeros((64, 64), dtype=float)),
        is_skew_symmetric_matrix(np.array([[0, -1], [1, 0]], dtype=int)),
    ]


value = clean(one())
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
