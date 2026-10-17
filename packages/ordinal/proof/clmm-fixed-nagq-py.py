import csv
import json
import statistics
import time
from pathlib import Path

import numpy as np

from ordinal.clmm import clmm

HERE = Path(__file__).resolve().parent

with open(HERE / "clmm-wine.csv", newline="") as fh:
    rows = list(csv.DictReader(fh))

data = {k: [r[k] for r in rows] for k in rows[0]}
levels = {
    "rating": ["1", "2", "3", "4", "5"],
    "contact": ["no", "yes"],
    "temp": ["cold", "warm"],
    "judge": [str(i) for i in range(1, 10)],
}

# Fixed start (thresholds, contact, temp, log sd), the same numbers as clmm-r.R.
START = [-1.3, 1.2, 3.5, 5.0, 1.5, 2.5, 0.0]


def pack(fit):
    return np.concatenate([
        np.asarray(fit["coefficients"], dtype=float).ravel(),
        [fit["logLik"]],
        np.asarray(fit["ST"], dtype=float).ravel(),
        np.asarray(fit["ranef"], dtype=float).ravel(),
        np.asarray(fit["condVar"], dtype=float).ravel(),
        np.asarray(fit["gradient"], dtype=float).ravel(),
        np.asarray(fit["Hessian"], dtype=float).ravel(order="F"),
    ])


def one():
    return pack(clmm("rating ~ contact + temp + (1 | judge)", data, levels=levels, nAGQ=10, start=START))


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("null" if np.isnan(x) else "%.17g" % float(x) for x in value), statistics.median(elapsed))
)
