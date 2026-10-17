import csv
import json
import statistics
import time
from pathlib import Path

import numpy as np

from ordinal.clm_fit import clm_fit

HERE = Path(__file__).resolve().parent

with open(HERE / "clm.fit-wine.csv", newline="") as fh:
    rows = list(csv.DictReader(fh))

y = [r["rating"] for r in rows]
levels = ["1", "2", "3", "4", "5"]
contacts = [r["contact"] for r in rows]
temps = [r["temp"] for r in rows]
# model.matrix(~ contact + temp) with treatment contrasts: no/yes and cold/warm.
X = np.column_stack([
    np.ones(len(rows)),
    np.array([1.0 if c == "yes" else 0.0 for c in contacts]),
    np.array([1.0 if t == "warm" else 0.0 for t in temps]),
])
X_names = ["(Intercept)", "contactyes", "tempwarm"]


def one():
    fit = clm_fit(y, X, levels=levels, X_names=X_names)
    return np.concatenate([
        np.asarray(fit["coefficients"], dtype=float).ravel(order="F"),
        [fit["logLik"], fit["edf"], fit["nobs"], fit["maxGradient"]],
        np.asarray(fit["niter"], dtype=float),
        [float(fit["convergence"]["code"][0]), fit["cond.H"]],
        np.asarray(fit["vcov"], dtype=float).ravel(order="F"),
        np.asarray(fit["gradient"], dtype=float).ravel(order="F"),
        np.asarray(fit["Theta"], dtype=float).ravel(order="F"),
    ])


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
