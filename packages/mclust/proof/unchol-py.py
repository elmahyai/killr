import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/mclust")
from mclust.unchol import unchol


def flat(*parts):
    out = []
    for part in parts:
        out.extend(np.asarray(part, dtype=float).ravel(order="F").tolist())
    return out


def one():
    U = np.array([2, 0, 0, 0.5, 1.5, 0, -0.3, 0.4, 1.2], dtype=float).reshape(3, 3, order="F")
    L = np.array([2, 0.5, -0.3, 0, 1.5, 0.4, 0, 0, 1.2], dtype=float).reshape(3, 3, order="F")
    D = np.diag([2.0, 3.0, 4.0])
    return flat(
        unchol(U, upper=True),
        unchol(L, upper=False),
        unchol(U),
        unchol(L),
        unchol(D),
        unchol(np.array([[2.0]])),
        unchol(np.array([[1.5]])),
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
