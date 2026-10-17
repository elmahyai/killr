import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.pyears import pyears

_CSV = Path(__file__).with_name("pyears_hearta.csv")


def _load():
    rows = list(csv.DictReader(_CSV.open()))
    data = {}
    for key in rows[0].keys():
        col = []
        for row in rows:
            text = row[key]
            if text == "NA" or text == "":
                col.append(float("nan"))
            else:
                try:
                    col.append(float(text))
                except ValueError:
                    col.append(text)
        data[key] = np.asarray(col, dtype=float) if all(isinstance(v, float) for v in col) else col
    return data


def _serialize(fit):
    py = np.asarray(fit["pyears"], dtype=float).reshape(-1, order="F")
    n = np.asarray(fit["n"], dtype=float).reshape(-1, order="F")
    event = np.asarray(fit["event"], dtype=float).reshape(-1, order="F")
    lines = [*(f"{v:.17g}" for v in py), *(f"{v:.17g}" for v in n), *(f"{v:.17g}" for v in event)]
    lines.append(f"{float(fit['offtable']):.17g}")
    lines.append(f"{float(fit['observations']):.17g}")
    return lines


def one():
    data = _load()
    fit = pyears(
        "Surv(stop / 365.25, event) ~ cut(age + 48, c(0, 50, 60, 70, 100)) + surgery",
        data=data,
        scale=1,
    )
    return _serialize(fit)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
