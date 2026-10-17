import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")

from mass.iso_mds import iso_mds, mass_dist


def one():
    pts = np.array([[1, 2], [2, 3], [5, 1], [4, 2], [3, 5]], dtype=float)
    d = mass_dist(pts)
    y0 = np.array(
        [[-0.5, 0.2], [0.1, -0.3], [0.4, 0.3], [-0.1, 0.5], [-0.2, 0.0]],
        dtype=float,
    )
    res = iso_mds(d, y=y0, trace=False, maxit=50)
    return np.concatenate([res["points"].reshape(-1, order="F"), [res["stress"]]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
