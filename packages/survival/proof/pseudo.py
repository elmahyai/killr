import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.pseudo import pseudo, survfit_from_y

_Y_PATH = Path(__file__).with_name("basehaz_lung_y.csv")


def _load_y():
    rows = list(csv.DictReader(_Y_PATH.open()))
    return np.column_stack(
        [
            [float(row["x.time"]) for row in rows],
            [float(row["x.status"]) for row in rows],
        ]
    )


def one():
    fit1 = survfit_from_y(_load_y())
    yhat = pseudo(fit1, times=[365, 730])
    flat = np.asarray(yhat, dtype=float).reshape(-1, order="F")
    out = [f"{int(yhat.shape[0])}", f"{int(yhat.shape[1])}"]
    out.extend(f"{value:.17g}" for value in flat)
    return out


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
