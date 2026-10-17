import statistics
import time
from pathlib import Path

import numpy as np

from survival.royston import royston

_PROOF = Path(__file__).resolve().parent


def _load_fit():
    y = np.loadtxt(_PROOF / "royston_y.csv", delimiter=",", skiprows=1, ndmin=2)
    lp = np.loadtxt(_PROOF / "royston_lp.csv", delimiter=",", skiprows=1)
    loglik = np.loadtxt(_PROOF / "royston_loglik.csv", delimiter=",", skiprows=1)
    meta = np.loadtxt(_PROOF / "royston_meta.csv", delimiter=",", skiprows=1)
    coef = np.loadtxt(_PROOF / "royston_coef.csv", delimiter=",", skiprows=1)
    return {
        "class_": ("coxph",),
        "y": y,
        "linear.predictors": lp,
        "loglik": loglik,
        "nevent": float(meta[0]),
        "n": float(meta[1]),
        "coefficients": coef,
        "terms": {"specials": {}},
    }


def one():
    out = royston(_load_fit())
    keys = ["D", "se(D)", "R.D", "R.KO", "R.N", "C.GH"]
    return [f"{float(out[k]):.17g}" for k in keys]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
