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

from coda.as_mcmc import as_mcmc
from coda.geweke_plot import geweke_plot, proof_values
from coda.mcmc_list import mcmc_list

root = Path(__file__).resolve().parent
package = root.parent


def build():
    n = 2000
    i = np.arange(1, n + 1, dtype=np.float64)
    x = np.column_stack(
        (np.sin(i / 3) + 0.2 * np.cos(i), np.cos(i / 5) + 0.01 * i)
    )
    y = np.column_stack(
        (np.sin(i / 4) + 0.15 * np.cos(i / 2), np.cos(i / 6) + 0.005 * i)
    )
    names = ["alpha", "beta"]
    c1 = as_mcmc(x)
    c1.colnames = names
    c2 = as_mcmc(y)
    c2.colnames = names
    return mcmc_list(c1, c2)


def one(save=False):
    plt.close("all")
    result = geweke_plot(build())
    values = proof_values(result)
    if save and result["figures"]:
        out = package / "docs" / "output"
        out.mkdir(parents=True, exist_ok=True)
        result["figures"][0].savefig(out / "geweke.plot-python.svg")
    plt.close("all")
    return values


def encode(values):
    out = []
    for number in values:
        if number != number:
            out.append(None)
        else:
            out.append(float(number))
    return out


value = one(True)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one(False)
    elapsed.append((time.perf_counter() - started) * 1000)

payload = {"value": encode(value), "median_ms": statistics.median(elapsed)}
print(json.dumps(payload))
(root / "geweke.plot-py.txt").write_text(json.dumps(payload) + "\n")
