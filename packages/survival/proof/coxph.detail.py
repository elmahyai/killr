import statistics
import time
from pathlib import Path

import numpy as np

from survival.coxph_detail import coxph_detail

_PROOF = Path(__file__).resolve().parent


def _load_fit():
    y = np.loadtxt(_PROOF / "coxph.detail_y.csv", delimiter=",", skiprows=1, ndmin=2)
    x = np.loadtxt(_PROOF / "coxph.detail_x.csv", delimiter=",", skiprows=1)
    lp = np.loadtxt(_PROOF / "coxph.detail_lp.csv", delimiter=",", skiprows=1)
    means = np.loadtxt(_PROOF / "coxph.detail_means.csv", delimiter=",", skiprows=1)
    resid = np.loadtxt(_PROOF / "coxph.detail_resid.csv", delimiter=",", skiprows=1)
    return {
        "class_": ("coxph",),
        "y": y,
        "x": x,
        "linear.predictors": lp,
        "means": means,
        "residuals": resid,
        "method": "efron",
        "terms": {"class_": ("terms",)},
    }


def one():
    fitd = coxph_detail(_load_fit())
    return [
        f"{float(np.sum(fitd['time'])):.17g}",
        f"{float(np.sum(fitd['nevent'])):.17g}",
        f"{float(np.sum(fitd['nrisk'])):.17g}",
        f"{float(np.sum(fitd['means'])):.17g}",
        f"{float(np.sum(fitd['score'])):.17g}",
        f"{float(np.sum(fitd['imat'])):.17g}",
        f"{float(np.sum(fitd['hazard'])):.17g}",
        f"{float(np.sum(fitd['varhaz'])):.17g}",
        f"{float(np.sum(fitd['wtrisk'])):.17g}",
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
