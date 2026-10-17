import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qres_pois import qres_pois


def _glm(fitted, y):
    return {
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
    }


FIT = _glm(
    "3.0000000000000617,7.0000000000000133,3.0000000000000617,7.0000000000000133,7.0000000000000133,3.0000000000000617",
    "3,7,2,9,5,4",
)
FIT2 = _glm(
    "0.39895020348162274,0.62722090299462296,0.98610317207548981,1.5503301330275963,2.4373955884500145",
    "0,1,2,0,3",
)
FIT3 = _glm(
    "15.000000000000412,15.000000000000412,15.000000000000412",
    "10,20,15",
)


def one():
    set_seed(42)
    r1 = qres_pois(FIT)
    set_seed(42)
    r2 = qres_pois(FIT2)
    set_seed(42)
    r3 = qres_pois(FIT3)
    return np.concatenate(
        [np.asarray(r1, dtype=float), np.asarray(r2, dtype=float), np.asarray(r3, dtype=float)]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
