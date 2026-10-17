import statistics
import time
from collections import OrderedDict
from pathlib import Path

import numpy as np

from survival.cox_zph import cox_zph

_PROOF = Path(__file__).resolve().parent


def _load_fit():
    y = np.loadtxt(_PROOF / "cox.zph_y.csv", delimiter=",", skiprows=1)
    x = np.loadtxt(_PROOF / "cox.zph_x.csv", delimiter=",", skiprows=1)
    lp = np.loadtxt(_PROOF / "cox.zph_lp.csv", delimiter=",", skiprows=1)
    coef = np.loadtxt(_PROOF / "cox.zph_coef.csv", delimiter=",", skiprows=1)
    return {
        "class_": ("coxph",),
        "y": y,
        "x": x,
        "linear.predictors": lp,
        "coefficients": coef,
        "method": "efron",
        "assign": OrderedDict([("age", [1]), ("ecog.ps", [2])]),
    }


def one():
    zp = cox_zph(_load_fit())
    tbl = zp["table"]["data"]
    ysum = float(np.sum(zp["y"]))
    varsum = float(np.sum(zp["var"]))
    return [
        *[f"{value:.17g}" for value in tbl[:, 0]],
        *[f"{value:.17g}" for value in tbl[:, 1]],
        *[f"{value:.17g}" for value in tbl[:, 2]],
        f"{ysum:.17g}",
        f"{varsum:.17g}",
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
