import json
import statistics
import sys
import time
import warnings
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coda.as_mcmc import as_mcmc
from coda.crosscorr_plot import crosscorr_plot, proof_values
import numpy as np

root = Path(__file__).resolve().parent
package = root.parent


def build():
    n = 200
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (
            np.sin(i / 3) + 0.2 * np.cos(i),
            np.cos(i / 5) + 0.01 * i,
            np.full(n, 2.0),
        )
    )
    chain = as_mcmc(x)
    chain.colnames = ["alpha", "beta", "gamma"]
    return chain


def one(save=False):
    plt.close("all")
    result = crosscorr_plot(build())
    values = proof_values(result)
    if save:
        out = package / "docs" / "output"
        out.mkdir(parents=True, exist_ok=True)
        result["figure"].savefig(out / "crosscorr.plot-python.svg")
    plt.close("all")
    return values


value = one(True)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(False)
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {"value": value, "median_ms": statistics.median(elapsed)}
print(json.dumps(payload))
(root / "crosscorr.plot-py.txt").write_text(json.dumps(payload) + "\n")
