import statistics
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from mclust.plot_mclust_bootstrap_lrt import plot_data, plot_mclustBootstrapLRT

x = {
    "G": [1, 2, 3],
    "modelName": "EEE",
    "obs": [12.3456789, 3.2, 0.000123],
    "boot": np.arange(0.5, 15.25 + 0.125, 0.25).reshape((20, 3), order="F"),
}


def one():
    d = plot_data(x, G=1)
    return np.concatenate((d["breaks"], d["density"], [d["obs"], *d["xlim"]]))


value = one()
fig, ax = plt.subplots()
plot_mclustBootstrapLRT(x, G=1, ax=ax)
fig.savefig(ROOT / "docs" / "output" / "plot.mclustBootstrapLRT-python.svg")
plt.close(fig)
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - started) * 1000)
for item in value:
    print("%.17g" % item)
print("%.17g" % statistics.median(elapsed))
