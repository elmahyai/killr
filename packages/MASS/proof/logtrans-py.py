import statistics
import sys
import time

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/MASS")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")

import numpy as np

from mass.boxcox import BoxcoxLm
from mass.logtrans import logtrans


def one():
    d = {
        "y": np.array([5.2, 3.1, 8.4, 4.2, 6.7]),
        "x1": np.array([1.0, 2, 3, 4, 5]),
        "x2": np.array([0.5, 1, 0.8, 1, 1]),
    }
    n = 5
    x = np.column_stack([np.ones(n), d["x1"], d["x2"]])
    fit = BoxcoxLm(y=d["y"], x=x)
    r = logtrans(
        fit,
        alpha=np.linspace(0.1, 2, 5),
        plotit=False,
        interp=False,
    )
    return np.concatenate([r["x"], r["y"]])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
flat = np.asarray(value, dtype=float).reshape(-1)
print("\n".join("%.17g" % item for item in flat))
print("%.17g" % statistics.median(elapsed))
