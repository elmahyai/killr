import csv
import statistics
import time
from pathlib import Path

import numpy as np

from ordinal.clmm import clmm
from ordinal.ranef import ranef

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


def one():
    fit = clmm("rating ~ contact + temp + (1 | judge)", data, levels=levels)
    return [frame.to_numpy() for frame in ranef(fit).values()]


value = np.concatenate([np.ravel(m, order="F") for m in one()])
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(
    '{"value":[%s],"median_ms":%.17g}'
    % (",".join("%.17g" % float(x) for x in value), statistics.median(elapsed))
)
