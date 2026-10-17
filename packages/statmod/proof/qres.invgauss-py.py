import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.qres_invgauss import qres_invgauss


def _glm(fitted, y, df_residual):
    return {
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
        "df_residual": int(df_residual),
    }


FIT1 = _glm(
    "1.7383800544651,1.89872824879056,2.11360038871959,2.42309425832876,2.92619704969599",
    "1.5,2.2,1.8,3.1,2.5",
    3,
)
FIT2 = _glm(
    "2.04774840442988,2.65450319607442,2.04774840442988,4.69549680549042,2.65450319607442",
    "2.0,3.5,1.6,4.2,2.8",
    3,
)


def one():
    r1 = qres_invgauss(FIT1)
    r2 = qres_invgauss(FIT2, dispersion=0.05)
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
