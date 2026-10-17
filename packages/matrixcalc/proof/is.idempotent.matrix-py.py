import json
import math
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.is_idempotent_matrix import is_idempotent_matrix


def clean(value):
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, list):
        return [clean(item) for item in value]
    return value


def one():
    a = np.eye(3, dtype=float)
    b = np.array([[1, 2], [3, 4]], dtype=float)
    c = np.array([[1, 0], [0, 0]], dtype=float)
    near = np.array([[1, 0], [0, 1e-9]], dtype=float)
    far = np.array([[1, 0], [0, 1e-7]], dtype=float)
    empty = np.zeros((0, 0), dtype=float)
    na_case = np.array([[1, np.nan], [0, 2]], dtype=float)
    nan_case = np.array([[1, np.nan], [np.nan, 2]], dtype=float)
    inf_case = np.array([[1, np.inf], [0, 2]], dtype=float)
    return [
        is_idempotent_matrix(a),
        is_idempotent_matrix(b),
        is_idempotent_matrix(c),
        is_idempotent_matrix(near),
        is_idempotent_matrix(far),
        is_idempotent_matrix(empty),
        is_idempotent_matrix(np.array([[3.5]], dtype=float)),
        is_idempotent_matrix(na_case),
        is_idempotent_matrix(nan_case),
        is_idempotent_matrix(inf_case),
        is_idempotent_matrix(np.array([[1, 2], [3, 4]], dtype=int)),
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
