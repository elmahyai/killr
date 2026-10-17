import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qres_tweedie import qres_tweedie


def _glm(fitted, y, var_power, df_residual, prior_weights=None):
    obj = {
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
        "var_power": float(var_power),
        "df_residual": int(df_residual),
    }
    if prior_weights is not None:
        obj["prior_weights"] = np.array(
            [float(x) for x in prior_weights.split(",")], dtype=float
        )
    return obj


FIT1 = _glm(
    "0.336328133922803,0.573289176453289,0.336328133922803,1.18887449230167,0.573289176453289,3.79189088772939",
    "0,1.2,0,2.1,0.5,3",
    1.5,
    4,
)
FIT2 = _glm(
    "1.48203805097292,1.61087919851054,1.48203805097292,1.76425490012034,1.61087919851054,1.94991060091274",
    "1.2,2.1,0.9,1.8,2.4,1.5",
    2,
    4,
)


def one():
    set_seed(42)
    r1 = qres_tweedie(FIT1)
    set_seed(42)
    r2 = qres_tweedie(FIT2, dispersion=0.05)
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
