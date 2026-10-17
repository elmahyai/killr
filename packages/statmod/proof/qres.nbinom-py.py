import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qres_nbinom import qres_nbinom


def _glm(fitted, y, family_size, df_residual=999):
    return {
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
        "family_size": float(family_size),
        "df_residual": int(df_residual),
    }


FIT1 = _glm(
    "5,11.6666666666667,5,11.6666666666667,11.6666666666667,5",
    "5,12,3,8,15,7",
    3,
)
FIT2 = _glm(
    "0.806799924309391,1.4054760714682,2.44839262864406,4.26519283087927,7.43012769755756",
    "0,2,5,1,8",
    2,
)


def one():
    set_seed(42)
    r1 = qres_nbinom(FIT1)
    set_seed(42)
    r2 = qres_nbinom(FIT2)
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
