import json
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.is_indefinite import is_indefinite


def one():
    i3 = np.eye(3, dtype=float)
    a = np.array([[2, -1, 0], [-1, 2, -1], [0, -1, 2]], dtype=float)
    b = np.array([[2, -1, 2], [-1, 2, -1], [2, -1, 2]], dtype=float)
    c_mat = np.array([[-2, 1, 0], [1, -2, 1], [0, 1, -2]], dtype=float)
    d = np.array([[-2, 1, -2], [1, -2, 1], [-2, 1, -2]], dtype=float)
    e = np.array([[1, 2, 0], [2, 1, 2], [0, 2, 1]], dtype=float)
    bad2 = np.array([[1, 2], [2, 1]], dtype=float)
    mixed2 = np.array([[1, 0], [0, -1]], dtype=float)
    tiny_pos = np.array([[1e-9, 0], [0, -1]], dtype=float)
    above_tol = np.array([[1e-7, 0], [0, -1]], dtype=float)
    return [
        is_indefinite(i3),
        is_indefinite(a),
        is_indefinite(b),
        is_indefinite(c_mat),
        is_indefinite(d),
        is_indefinite(e),
        is_indefinite(bad2),
        is_indefinite(mixed2),
        is_indefinite(tiny_pos),
        is_indefinite(above_tol),
        is_indefinite(np.array([[2.5]], dtype=float)),
        is_indefinite(np.array([[1]], dtype=int)),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
if not isinstance(value, list):
    value = [value]
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
