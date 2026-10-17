import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.as_mcmc_list import as_mcmc_list
from coda.crosscorr import crosscorr

n = 2000
i = np.arange(1, n + 1, dtype=float)
x = np.column_stack(
    (np.sin(i / 3) + 0.2 * np.cos(i), np.cos(i / 5) + 0.01 * i, np.full(n, 2.0))
)
y = np.column_stack(
    (
        np.sin(i / 4) + 0.15 * np.cos(i / 2),
        np.cos(i / 6) + 0.005 * i,
        np.full(n, 1.0),
    )
)


def one():
    result = crosscorr(as_mcmc_list([as_mcmc(x), as_mcmc(y)]))
    return np.ravel(np.asarray(result, dtype=np.float64), order="F").tolist()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

root = Path(__file__).resolve().parent
out = json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
(root / "crosscorr-py.txt").write_text(out + "\n")
print(out)
