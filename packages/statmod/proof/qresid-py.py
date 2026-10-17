import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qresid import qresid


def _poisson(fitted, y):
    return {
        "family": {"family": "poisson"},
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
    }


def _gaussian(deviance, working, weights, df_residual):
    return {
        "family": {"family": "gaussian"},
        "deviance_residuals": np.array([float(x) for x in deviance.split(",")], dtype=float),
        "working_residuals": np.array([float(x) for x in working.split(",")], dtype=float),
        "weights": np.array([float(x) for x in weights.split(",")], dtype=float),
        "df_residual": int(df_residual),
    }


FIT_P = _poisson(
    "3.0000000000000617,7.0000000000000133,3.0000000000000617,7.0000000000000133,7.0000000000000133,3.0000000000000617",
    "3,7,2,9,5,4",
)
FIT_G = _gaussian(
    "-0.48,0.57,-0.28,0.77,-0.58",
    "-0.48,0.57,-0.28,0.77,-0.58",
    "1,1,1,1,1",
    3,
)


def one():
    set_seed(42)
    r1 = qresid(FIT_P)
    r2 = qresid(FIT_G)
    return np.concatenate([np.asarray(r1).reshape(-1), np.asarray(r2).reshape(-1)])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append(time.perf_counter() - t0)

print(",".join(f"{x:.17g}" for x in value))
print("MS")
print(f"{statistics.median(elapsed) * 1000:.17g}")
