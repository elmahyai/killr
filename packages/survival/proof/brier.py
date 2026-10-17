import statistics
import time
from pathlib import Path

import numpy as np

from survival.brier import brier

_PROOF = Path(__file__).resolve().parent


def _load_fit():
    y = np.loadtxt(_PROOF / "brier_y.csv", delimiter=",", skiprows=1)
    x = np.loadtxt(_PROOF / "brier_x.csv", delimiter=",", skiprows=1)
    lp = np.loadtxt(_PROOF / "brier_lp.csv", delimiter=",", skiprows=1)
    coef = np.loadtxt(_PROOF / "brier_coef.csv", delimiter=",", skiprows=1)
    means = np.loadtxt(_PROOF / "brier_means.csv", delimiter=",", skiprows=1)
    return {
        "class_": ("coxph",),
        "y": y,
        "x": x,
        "linear.predictors": lp,
        "coefficients": coef,
        "means": means,
        "method": "efron",
    }


def one():
    br = brier(_load_fit(), times=np.array([4, 6]) * 365.25)
    return [
        *[f"{value:.17g}" for value in br["rsquared"]],
        *[f"{value:.17g}" for value in br["brier"]],
        *[f"{value:.17g}" for value in br["times"]],
    ]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
