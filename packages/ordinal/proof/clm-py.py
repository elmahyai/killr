import csv
import json
import statistics
import time
from pathlib import Path

import numpy as np

from ordinal.clm import clm

HERE = Path(__file__).resolve().parent

with open(HERE / "clm.fit-wine.csv", newline="") as fh:
    rows = list(csv.DictReader(fh))

data = {
    "rating": [r["rating"] for r in rows],
    "contact": [r["contact"] for r in rows],
    "temp": [r["temp"] for r in rows],
}
levels = {"rating": ["1", "2", "3", "4", "5"], "contact": ["no", "yes"], "temp": ["cold", "warm"]}


def pack(fit):
    return np.concatenate([
        np.asarray(fit["coefficients"], dtype=float).ravel(order="F"),
        [fit["logLik"], fit["edf"], fit["nobs"], fit["maxGradient"]],
        np.asarray(fit["niter"], dtype=float),
        [float(fit["convergence"]["code"][0]), fit["cond.H"]],
        np.asarray(fit["vcov"], dtype=float).ravel(order="F"),
        np.asarray(fit["gradient"], dtype=float).ravel(order="F"),
        np.asarray(fit["Theta"], dtype=float).ravel(order="F"),
    ])


def one():
    return np.concatenate([
        pack(clm("rating ~ contact + temp", data, levels=levels)),
        pack(clm("rating ~ contact", data, scale="~ temp", levels=levels)),
        pack(clm("rating ~ temp", data, nominal="~ contact", levels=levels)),
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
