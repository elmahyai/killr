import json
import statistics
import sys
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.mcmc_list import mcmc_list
from coda.traceplot import proof_values, traceplot

root = Path(__file__).resolve().parent
package = root.parent


def build():
    n = 2000
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (
            np.sin(i / 3) + 0.2 * np.cos(i),
            np.cos(i / 5) + 0.01 * i,
            np.full(n, 2.0),
        )
    )
    y = np.column_stack(
        (
            np.sin(i / 4) + 0.15 * np.cos(i / 2),
            np.cos(i / 6) + 0.005 * i,
            np.full(n, 1.0),
        )
    )
    first = as_mcmc(x, start=11, thin=2)
    second = as_mcmc(y, start=11, thin=2)
    names = ["alpha", "beta", "gamma"]
    first.colnames = names
    second.colnames = names
    chains = mcmc_list(first, second)
    nv = 200
    iv = np.arange(1, nv + 1, dtype=np.float64)
    vector = as_mcmc(np.sin(iv / 9) + 0.1 * iv, start=5, thin=3)
    return chains, vector


def one(path=None):
    chains, vector = build()
    drawn = traceplot(chains)
    smoothed = traceplot(vector, smooth=True)
    if path is not None:
        drawn["figure"].savefig(path, format="svg")
    plt.close(drawn["figure"])
    plt.close(smoothed["figure"])
    return proof_values(drawn) + proof_values(smoothed)


value = one(package / "docs" / "output" / "traceplot-python.svg")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

(root / "traceplot-py.txt").write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
