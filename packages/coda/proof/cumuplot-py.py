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
from coda.cumuplot import cumuplot, proof_values
from coda.mcmc_list import mcmc_list

root = Path(__file__).resolve().parent
package = root.parent

n = 80
i = np.arange(1, n + 1, dtype=np.float64)
alpha = np.sin(i / 3) + 0.2 * np.cos(i)
beta = np.cos(i / 5) + 0.01 * i
chain = as_mcmc(np.column_stack((alpha, beta)), start=11, thin=2)
chain.colnames = ["alpha", "beta"]
obj = mcmc_list(chain)
obj.chain_names = ["north"]


def one():
    plt.close("all")
    result = cumuplot(obj, ask=False)
    values = proof_values(result)
    figures = result.figures
    return values, figures


value, figures = one()
output = package / "docs" / "output"
output.mkdir(parents=True, exist_ok=True)
for index, figure in enumerate(figures):
    name = "cumuplot-python.svg" if index == 0 else f"cumuplot-python-{index + 1}.svg"
    figure.savefig(output / name, format="svg")
plt.close("all")

elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
plt.close("all")

out_path = root / "cumuplot-py.txt"
out_path.write_text(
    json.dumps({"value": value, "median_ms": statistics.median(elapsed)}) + "\n"
)
