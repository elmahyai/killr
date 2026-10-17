import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

from mass.glm_convert import glm_convert, proof_vector
from mass.glm_nb import glm_nb


def one():
    y = np.array(
        [
            7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6, 7, 10, 6, 12,
            6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5, 3, 3, 4,
        ],
        dtype=float,
    )
    lag1 = np.array(
        [
            0, 7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6, 7, 10,
            6, 12, 6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5, 3, 3,
        ],
        dtype=float,
    )
    lag2 = np.array(
        [
            0, 0, 7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6, 7,
            10, 6, 12, 6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5, 3,
        ],
        dtype=float,
    )
    lag3 = np.array(
        [
            0, 0, 0, 7, 5, 4, 7, 5, 2, 11, 5, 5, 4, 2, 3, 4, 3, 5, 9, 6,
            7, 10, 6, 12, 6, 3, 5, 3, 9, 13, 0, 6, 1, 2, 0, 1, 0, 0, 4, 5, 1, 5,
        ],
        dtype=float,
    )
    data = {"y": y, "lag1": lag1, "lag2": lag2, "lag3": lag3}
    fit = glm_nb(
        "y ~ lag1 + lag2 + lag3",
        data,
        link="identity",
        start=np.array([2, 0.1, 0.1, 0.1], dtype=float),
    )
    return proof_vector(glm_convert(fit))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
