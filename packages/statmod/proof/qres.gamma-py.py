import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qres_gamma import qres_gamma


def _glm(fitted, y, df_residual, prior_weights=None):
    obj = {
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
        "df_residual": int(df_residual),
    }
    if prior_weights is not None:
        obj["prior_weights"] = np.array(
            [float(x) for x in prior_weights.split(",")], dtype=float
        )
    return obj


FIT_G = _glm(
    "1.42929219017665,1.60794841449244,1.42929219017665,1.80893600443532,1.60794841449244,2.03504629790958",
    "1.2,2.1,0.9,1.8,2.4,1.5",
    4,
)
FIT2 = _glm(
    "2.99557888150871,3.93039402710984,2.99557888150871,5.15693220555768,3.93039402710984",
    "3.1,4.2,2.8,5.0,3.9",
    3,
)
FIT3 = _glm(
    "2.42857142857365,2.42857142857365,2.42857142857365,2.42857142857365",
    "2.0,3.5,1.8,4.1",
    3,
    "2,1,3,1",
)


def one():
    set_seed(42)
    r1 = qres_gamma(FIT_G)
    set_seed(42)
    r2 = qres_gamma(FIT2, dispersion=0.05)
    set_seed(42)
    r3 = qres_gamma(FIT3)
    return np.concatenate([np.asarray(r1).reshape(-1), np.asarray(r2).reshape(-1), np.asarray(r3).reshape(-1)])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append(time.perf_counter() - t0)

print(",".join(f"{x:.17g}" for x in value))
print("MS")
print(f"{statistics.median(elapsed) * 1000:.17g}")
