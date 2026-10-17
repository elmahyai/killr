import json
import statistics
import sys
import time
import warnings

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/matrixcalc")
warnings.simplefilter("ignore")

from matrixcalc.is_square_matrix import is_square_matrix


def one():
    a = np.arange(1, 13, dtype=float).reshape(3, 4)
    b = np.arange(1, 17, dtype=float).reshape(4, 4)
    return [
        is_square_matrix(a),
        is_square_matrix(b),
        is_square_matrix(np.array([[3.5]])),
        is_square_matrix(np.zeros((0, 0))),
        is_square_matrix(np.zeros((2, 3))),
        is_square_matrix(np.array([[1, 3], [2, 4]])),
        is_square_matrix(np.array([[True, True], [False, True]])),
        is_square_matrix(np.zeros((64, 64))),
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
