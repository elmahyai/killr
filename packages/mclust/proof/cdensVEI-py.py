import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.cdens_v_vei_vev_vii_vvi_vvv import cdensVEI

n = 40
p = 3
G = 3
i = np.arange(1, n + 1, dtype=float)
x = np.column_stack([np.sin(0.7 * i), 0.7 * np.cos(1.3 * i) + 0.1 * i / n, np.sin(0.4 * i + 1) - 0.5 * i / n])
mu = np.array([[-0.5, 0.2, 0.1], [0.4, -0.3, 0.6], [0.0, 0.9, -0.8]])
pro = np.array([0.3, 0.45, 0.25])
sc = np.array([0.6, 1.4, 0.9])
sh = np.array([1.5, 0.7, 1.1])
pars = {"pro": pro, "mean": mu, "variance": {"scale": sc, "shape": sh}}


def one():
    a = cdensVEI(x, logarithm=True, parameters=pars)
    b = cdensVEI(x, logarithm=False, parameters=pars)
    return np.concatenate([np.asarray(a).ravel(order="F"), np.asarray(b).ravel(order="F")])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
