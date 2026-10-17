import csv
import statistics
import time
from pathlib import Path

import numpy as np

from survival.yates import lm_fit, yates

_CSV = Path(__file__).with_name("yates_solder.csv")


def _load():
    rows = list(csv.DictReader(_CSV.open()))
    data: dict = {}
    for key in rows[0].keys():
        col = []
        for row in rows:
            text = row[key].strip()
            if key == "skips":
                col.append(float(text))
            else:
                col.append(text)
        data[key] = col
    return data


def _serialize(result) -> list[str]:
    opening = result.estimate["Opening"]
    pmm = np.asarray(result.estimate["pmm"], dtype=float)
    std = np.asarray(result.estimate["std"], dtype=float)
    test = np.asarray(result.test, dtype=float).reshape(-1)
    lines = [str(v) for v in opening]
    lines.extend(f"{v:.17g}" for v in pmm)
    lines.extend(f"{v:.17g}" for v in std)
    lines.extend(f"{v:.17g}" for v in test)
    return lines


def one():
    data = _load()
    fit = lm_fit("skips ~ Solder*Opening + Mask", data)
    result = yates(fit, "~Opening", population="factorial")
    return _serialize(result)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join(value))
print("MS")
print(f"{statistics.median(elapsed):.17g}")
