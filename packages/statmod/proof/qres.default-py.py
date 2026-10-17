import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.qres_default import qres_default


def _glm(deviance, working, weights, df_residual):
    return {
        "deviance_residuals": np.array([float(x) for x in deviance.split(",")], dtype=float),
        "working_residuals": np.array([float(x) for x in working.split(",")], dtype=float),
        "weights": np.array([float(x) for x in weights.split(",")], dtype=float),
        "df_residual": int(df_residual),
    }


FIT1 = _glm(
    "-0.48,0.57,-0.28,0.77,-0.58",
    "-0.48,0.57,-0.28,0.77,-0.58",
    "1,1,1,1,1",
    3,
)
FIT2 = _glm(
    "-1.01015254455221,-0.214285714285714,0.494871659305395,0.785714285714286",
    "-0.714285714285714,-0.214285714285714,0.285714285714286,0.785714285714286",
    "2,1,3,1",
    3,
)


def one():
    r1 = qres_default(FIT1)
    r2 = qres_default(FIT2, dispersion=0.25)
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
