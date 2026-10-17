import json
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.is_negative_definite import is_negative_definite


def one():
    i3 = np.eye(3, dtype=float)
    a = np.array([[2, -1, 0], [-1, 2, -1], [0, -1, 2]], dtype=float)
    b = np.array([[2, -1, 2], [-1, 2, -1], [2, -1, 2]], dtype=float)
    c_mat = np.array([[-2, 1, 0], [1, -2, 1], [0, 1, -2]], dtype=float)
    d = np.array([[-2, 1, -2], [1, -2, 1], [-2, 1, -2]], dtype=float)
    e = np.array([[1, 2, 0], [2, 1, 2], [0, 2, 1]], dtype=float)
    bad2 = np.array([[1, 2], [2, 1]], dtype=float)
    tiny_ev = np.array([[-1, 0], [0, -1e-9]], dtype=float)
    above_tol = np.array([[-1, 0], [0, -1e-7]], dtype=float)
    base = np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9]], dtype=float)
    custom_tol = base + base.T
    return [
        is_negative_definite(i3),
        is_negative_definite(a),
        is_negative_definite(b),
        is_negative_definite(c_mat),
        is_negative_definite(d),
        is_negative_definite(e),
        is_negative_definite(bad2),
        is_negative_definite(tiny_ev),
        is_negative_definite(above_tol),
        is_negative_definite(np.array([[-2.5]], dtype=float)),
        is_negative_definite(np.array([[1]], dtype=int)),
        is_negative_definite(-custom_tol, tol=1e-6),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": [statistics.median(elapsed)]}))
