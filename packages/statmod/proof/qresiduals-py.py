import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/extraDistr")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/boot")
sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/statmod")
from statmod.power_fisher_test import set_seed
from statmod.qresid import qresiduals


def _binom(fitted, y, prior_weights):
    return {
        "family": {"family": "binomial"},
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
        "prior_weights": np.array([float(x) for x in prior_weights.split(",")], dtype=float),
    }


def _gamma(fitted, y, df_residual):
    return {
        "family": {"family": "Gamma"},
        "fitted_values": np.array([float(x) for x in fitted.split(",")], dtype=float),
        "y": np.array([float(x) for x in y.split(",")], dtype=float),
        "df_residual": int(df_residual),
    }


FIT_B = _binom(
    "0.4,0.6,0.4,0.6,0.6,0.4",
    "0.4,0.6,0.25,0.75,0.45,0.55",
    "20,20,20,20,20,20",
)
FIT_G = _gamma(
    "1.42929219017665,1.60794841449244,1.42929219017665,1.80893600443532,1.60794841449244,2.03504629790958",
    "1.2,2.1,0.9,1.8,2.4,1.5",
    4,
)


def one():
    set_seed(42)
    r1 = qresiduals(FIT_B)
    set_seed(42)
    r2 = qresiduals(FIT_G, dispersion=0.05)
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
