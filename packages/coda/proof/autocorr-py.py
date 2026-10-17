import json
import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.autocorr import autocorr

n = 2000
i = np.arange(1, n + 1, dtype=float)
x = np.column_stack(
    (np.sin(i / 3) + 0.2 * np.cos(i), np.cos(i / 5) + 0.01 * i, np.full(n, 2.0))
)


def one():
    result = autocorr(as_mcmc(x))
    return np.ravel(np.asarray(result, dtype=np.float64), order="F").tolist()


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
print(json.dumps({"value": value, "median_ms": statistics.median(elapsed)}))
