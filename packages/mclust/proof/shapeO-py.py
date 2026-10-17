import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.shape_o import shapeO


def flat(*parts):
    out = []
    for part in parts:
        out.extend(np.asarray(part, dtype=float).ravel(order="F").tolist())
    return out


def one():
    values = np.array(
        [
            0.2, 0.5, 0.1,
            0.3, 0.4, 0.6,
            0.7, 0.2, 0.8,
            0.1, 0.9, 0.3,
            0.4, 0.2, 0.5,
            0.6, 0.7, 0.1,
        ],
        dtype=float,
    )
    orientation = values.reshape(3, 3, 2, order="F")
    matrix = values[:9].reshape(3, 3, order="F")
    shape = np.array([1.5, 0.5, 2.0])
    return flat(
        shapeO(shape, orientation, transpose=False),
        shapeO(shape, orientation, transpose=True),
        shapeO(shape, matrix, transpose=False),
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
