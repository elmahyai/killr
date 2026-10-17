import json
import statistics
import sys
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.acfplot import acfplot, proof_values
from coda.as_mcmc import as_mcmc

n = 200
i = np.arange(1, n + 1, dtype=np.float64)
x = np.column_stack(
    (
        np.sin(i / 3) + 0.2 * np.cos(i),
        np.cos(i / 5) + 0.01 * i,
        np.full(n, 2.0),
    )
)
m = as_mcmc(x)


def one():
    plt.close("all")
    result = acfplot(m, lag_max=10, draw=True)
    return proof_values(result)


value = one()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
def encode(number):
    if number != number:
        return None
    if number == float("inf"):
        return 1e300
    if number == float("-inf"):
        return -1e300
    return number


print(json.dumps({"value": [encode(v) for v in value], "median_ms": statistics.median(elapsed)}))
