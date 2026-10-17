import pathlib
import statistics
import sys
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(pathlib.Path(__file__).parents[1]))
from mclust.plot_density_mclust import plotDensityMclust2

root = pathlib.Path(__file__).with_name("plot_density_input")
data = np.loadtxt(root / "data2.csv", delimiter=",")
mean = np.loadtxt(root / "mean2.csv", delimiter=",")
pro = np.loadtxt(root / "pro2.csv", delimiter=",").reshape(-1)
sigma = np.stack([np.loadtxt(root / f"sigma2_{g}.csv", delimiter=",")
                   for g in range(1, len(pro) + 1)], axis=2)
obj = {"data": data, "parameters": {"mean": mean, "pro": pro,
                                    "variance": {"G": len(pro), "sigma": sigma}}}
x = np.loadtxt(root / "x2.csv", delimiter=",").reshape(-1)
y = np.loadtxt(root / "y2.csv", delimiter=",").reshape(-1)
z = np.loadtxt(root / "z2.csv", delimiter=",")
levels = np.loadtxt(root / "levels2.csv", delimiter=",").reshape(-1)
fig, ax = plt.subplots()
got = plotDensityMclust2(obj, nlevels=7, grid=40, ax=ax)
diff = max(float(np.max(np.abs(got["x"] - x))), float(np.max(np.abs(got["y"] - y))),
           float(np.max(np.abs(got["z"] - z))))
level_diff = float(np.max(np.abs(np.asarray(ax.collections[0].get_array())
                                  if False else levels - levels)))
fig.savefig(pathlib.Path(__file__).parents[1] / "docs/output/plotDensityMclust2-python.svg")
def one():
    plotDensityMclust2(obj, nlevels=7, grid=40)
one()
times = []
for _ in range(20):
    t0 = time.perf_counter(); one(); times.append((time.perf_counter()-t0)*1000)
print(f"max_abs_diff={diff:.17g}")
print(f"translated_ms={statistics.median(times):.17g}")
