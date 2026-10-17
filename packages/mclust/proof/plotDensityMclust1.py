import pathlib
import statistics
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from mclust.plot_density_mclust import plotDensityMclust1

root = pathlib.Path(__file__).with_name("plot_density_input")
data = np.loadtxt(root / "data1.csv", delimiter=",").reshape(-1, 1)
mean = np.loadtxt(root / "mean1.csv", delimiter=",").reshape(1, -1)
pro = np.loadtxt(root / "pro1.csv", delimiter=",").reshape(-1)
sigmasq = np.loadtxt(root / "sigmasq1.csv", delimiter=",").reshape(-1)
obj = {"data": data, "modelName": "V",
       "parameters": {"mean": mean, "pro": pro,
                      "variance": {"G": len(pro), "sigmasq": sigmasq}}}
expected = np.loadtxt(root / "r1.csv", delimiter=",")
fig, ax = plt.subplots()
got = plotDensityMclust1(obj, ax=ax)
diff = float(np.max(np.abs(np.column_stack((got["x"], got["density"])) - expected)))
plot_path = pathlib.Path(__file__).parents[1] / "docs/output/plotDensityMclust1-python.svg"
fig.savefig(plot_path)
def one():
    plotDensityMclust1(obj)
one()
times = []
for _ in range(20):
    t0 = time.perf_counter(); one(); times.append((time.perf_counter()-t0)*1000)
print(f"max_abs_diff={diff:.17g}")
print(f"translated_ms={statistics.median(times):.17g}")
