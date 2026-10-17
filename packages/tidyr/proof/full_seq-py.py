import json
import statistics
import sys
import time

import numpy as np

sys.path.insert(0, "/home/ahmed/killr_projects/killr/packages/tidyr")
from tidyr.full_seq import Date, POSIXct, full_seq

days = Date([11323.0, 11325.0, 11329.0])
clock = POSIXct([978307200.0, 978480000.0], tzone="UTC")


def one():
    gaps = full_seq(np.array([1, 2, 4, 5, 10], dtype=float), 1.0)
    tol = full_seq(np.array([0, 10, 20], dtype=float), 11.0, tol=2.0)
    short = full_seq(np.array([0, 10, 16], dtype=float), 11.0, tol=5.0)
    frac = full_seq(np.array([0.1, 0.3, 0.7]), 0.2)
    grid = full_seq(np.array([0.0, 0.3, 0.6, 1.0]), 0.1)
    neg = full_seq(np.array([-4.0, -1.0, 2.0]), 1.5)
    dated = full_seq(days, 2.0)
    clocked = full_seq(clock, 86400.0)
    if dated.classes != ("Date",):
        raise RuntimeError("Date class was not restored")
    if clocked.tzone != "UTC" or clocked.classes != ("POSIXct", "POSIXt"):
        raise RuntimeError("POSIXct tzone was not restored")
    return np.concatenate(
        [
            np.asarray(gaps, dtype=float),
            np.asarray(tol, dtype=float),
            np.asarray(short, dtype=float),
            np.asarray(frac, dtype=float),
            np.asarray(grid, dtype=float),
            np.asarray(neg, dtype=float),
            np.asarray(dated.days, dtype=float),
            np.asarray(clocked.seconds, dtype=float),
        ]
    )


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": [float(item) for item in value], "median_ms": statistics.median(elapsed)}))
