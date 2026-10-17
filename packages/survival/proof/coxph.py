import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.coxph import coxph


def _load():
    csv_path = Path(__file__).with_name("lung.csv")
    if not csv_path.is_file():
        raise FileNotFoundError("proof/lung.csv missing")
    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    data = {}
    for name in rows[0]:
        data[name] = np.array(
            [float(r[name]) if r[name] != "" else np.nan for r in rows], dtype=float
        )
    data["status"] = data["status"] - 1.0
    data["ph_ecog"] = data.pop("ph_ecog")
    return data


def one(data):
    fit = coxph("Surv(time, status) ~ age + sex + ph_ecog + strata(inst)", data)
    coef = np.asarray(list(fit["coefficients"].values()), dtype=float)
    vals = np.concatenate(
        [
            coef,
            np.ravel(np.asarray(fit["var"], dtype=float), order="F"),
            np.asarray(fit["loglik"], dtype=float),
            np.array([fit["score"]], dtype=float),
            np.array([fit["wald.test"]], dtype=float),
            np.asarray(fit["means"], dtype=float),
            np.asarray(fit["residuals"], dtype=float),
            np.asarray(fit["linear.predictors"], dtype=float),
        ]
    )
    return ["NA" if v != v else f"{v:.17g}" for v in vals]


if __name__ == "__main__":
    data = _load()
    value = one(data)
    elapsed = []
    for _ in range(20):
        started = time.perf_counter()
        one(data)
        elapsed.append((time.perf_counter() - started) * 1000)
    print("\n".join(value))
    print("MS")
    print(f"{statistics.median(elapsed):.17g}")
