import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qres_binom import qres_binom


def _glm(fitted, y, prior_weights=None):
    obj = {
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
    }
    if prior_weights is not None:
        obj["prior_weights"] = np.array(
            [float(x) for x in prior_weights.split(",")], dtype=float
        )
    return obj


FIT_B = _glm(
    "0.4,0.6,0.4,0.6,0.6,0.4",
    "0.4,0.6,0.25,0.75,0.45,0.55",
    "20,20,20,20,20,20",
)
FIT2 = _glm(
    "0.392825542632621,0.501012152405756,0.60910407211275,0.707453228026552,0.789605004821599",
    "0,1,1,0,1",
)
FIT_W = _glm(
    "0.454575106466694,0.476328816984391,0.498172715328127,0.520023591190338,0.541798127993503",
    "0,1,1,0,1",
    "2,3,1,4,2",
)


def one():
    set_seed(42)
    r1 = qres_binom(FIT_B)
    set_seed(42)
    r2 = qres_binom(FIT2)
    set_seed(42)
    r3 = qres_binom(FIT_W)
    return np.concatenate([np.asarray(r1, dtype=float), np.asarray(r2, dtype=float), np.asarray(r3, dtype=float)])


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(",".join("%.17g" % float(v) for v in np.asarray(value, dtype=float)))
print("MS")
print("%.17g" % statistics.median(elapsed))
