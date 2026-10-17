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
from coda.densplot import densplot, proof_values

root = Path(__file__).resolve().parents[1]
out_dir = root / "docs" / "output"
out_dir.mkdir(parents=True, exist_ok=True)

n = 400
i = np.arange(1, n + 1, dtype=np.float64)
data = np.column_stack(
    (
        np.sin(i / 3) + 0.2 * np.cos(i),
        (np.sin(i / 5) + 1) / 2,
        np.arange(n) % 6,
    )
)
chain = as_mcmc(data)
chain.colnames = ["alpha", "beta", "gamma"]


def one(svg_path=None):
    result = densplot(chain)
    values = proof_values(result)
    figure = result.get("figure")
    if svg_path is not None and figure is not None:
        figure.savefig(svg_path)
    plt.close("all")
    return values


value = one(out_dir / "densplot-python.svg")
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)

out = json.dumps({"value": value, "median_ms": statistics.median(elapsed)})
(root / "proof" / "densplot-py.txt").write_text(out + "\n")
print(out)
