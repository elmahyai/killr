import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.basehaz import basehaz

_Y_PATH = Path(__file__).with_name("basehaz_lung_y.csv")


def _load_fit_y():
    rows = list(csv.DictReader(_Y_PATH.open()))
    keys = rows[0].keys()
    key_list = list(keys)
    time_key = next(k for k in key_list if "time" in k)
    status_key = next(k for k in key_list if "status" in k)
    y = np.column_stack(
        [
            [float(row[time_key]) for row in rows],
            [float(row[status_key]) for row in rows],
        ]
    )
    return y


def _fit():
    return {
        "class_": ("coxph",),
        "y": _load_fit_y(),
        "method": "efron",
        "means": np.array([], dtype=float),
        "coefficients": np.array([], dtype=float),
    }


def one():
    bh = basehaz(_fit())
    hazard = np.asarray(bh["hazard"], dtype=float)
    times = np.asarray(bh["time"], dtype=float)
    return [*(f"{value:.17g}" for value in hazard), *(f"{value:.17g}" for value in times)]


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
