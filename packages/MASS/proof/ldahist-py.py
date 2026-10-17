import statistics
import sys
import time
import types
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
pkg = types.ModuleType("mass")
pkg.__path__ = [str(root / "mass")]
sys.modules["mass"] = pkg
from mass.lda import lda
from mass.ldahist import ldahist, ldahist_data

n = 90
s = 123
u = np.empty(2 * n)
for k in range(2 * n):
    s = (16807 * s) % 2147483647
    u[k] = s / 2147483647
g = np.repeat(np.array(["A", "B", "C"]), 30)
gi = np.array([{"A": 1, "B": 2, "C": 3}[item] for item in g])
X = np.column_stack([u[:n] * 10 + 2 * gi, u[n:] * 6 - gi]).astype(float)
z = lda(X, g)
proj = (X - z.means.mean(axis=0)) @ z.scaling
data = proj[:, 0].copy()
groups = ["A", "B", "C"]


def real_call():
    res = ldahist(data, g, type="both")
    fig = res["figure"]
    fig.savefig(root / "docs/output/ldahist-python.svg")
    xlim = np.asarray(res["xlim"])
    breaks = res["breaks"]
    est = np.concatenate([res["est"][grp] for grp in groups])
    dens = np.concatenate([np.concatenate([res["density"][grp][0], res["density"][grp][1]]) for grp in groups])
    last = res["axes"][-1]
    usr_x = np.asarray(last.get_xlim())
    usr_y = np.asarray(last.get_ylim())
    value = np.concatenate([xlim, [res["ymax"]], breaks, est, dens, usr_x, usr_y])
    plt.close(fig)
    return value


value = real_call()
elapsed = []
for _ in range(20):
    started = time.perf_counter()
    ldahist_data(data, g, type="both")
    elapsed.append((time.perf_counter() - started) * 1000)
print("\n".join("%.17g" % item for item in np.asarray(value, dtype=float).reshape(-1)))
print("%.17g" % statistics.median(elapsed))
