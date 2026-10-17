import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.coxph_fit import coxph_fit
from survival.control import coxph_control


def _load():
    csv_path = Path(__file__).with_name("lung.csv")
    if not csv_path.is_file():
        raise FileNotFoundError("proof/lung.csv missing")
    with csv_path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    names = ["inst", "time", "status", "age", "sex", "ph_ecog"]
    table = {}
    for name in names:
        table[name] = np.array(
            [float(r[name]) if r[name] != "" else np.nan for r in rows], dtype=float
        )
    keep = np.all(np.isfinite(np.column_stack([table[n] for n in names])), axis=1)
    data = {name: table[name][keep] for name in names}
    data["status"] = data["status"] - 1.0
    return data


def one(data):
    x = np.column_stack([data["age"], data["sex"], data["ph_ecog"]])
    y = np.column_stack([data["time"], data["status"]])
    fit = coxph_fit(
        x,
        y,
        data["inst"],
        None,
        None,
        coxph_control(),
        None,
        "efron",
        None,
        True,
        (-1, 0, 1),
    )
    vals = np.concatenate(
        [
            np.asarray(fit["coefficients"], dtype=float),
            np.ravel(np.asarray(fit["var"], dtype=float), order="F"),
            np.asarray(fit["loglik"], dtype=float),
            np.array([fit["score"]], dtype=float),
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
