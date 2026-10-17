import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.cdens_v_vei_vev_vii_vvi_vvv import cdensVEV

n = 40
p = 3
G = 3
i = np.arange(1, n + 1, dtype=float)
x = np.column_stack([np.sin(0.7 * i), 0.7 * np.cos(1.3 * i) + 0.1 * i / n, np.sin(0.4 * i + 1) - 0.5 * i / n])
mu = np.array([[-0.5, 0.2, 0.1], [0.4, -0.3, 0.6], [0.0, 0.9, -0.8]])
pro = np.array([0.3, 0.45, 0.25])
sc = np.array([0.6, 1.4, 0.9])
sh = np.array([1.5, 0.7, 1.1])


def orient(k):
    a = 0.3 * k
    b = 0.5 * k
    Rz = np.array([[np.cos(a), -np.sin(a), 0.0], [np.sin(a), np.cos(a), 0.0], [0.0, 0.0, 1.0]])
    Rx = np.array([[1.0, 0.0, 0.0], [0.0, np.cos(b), -np.sin(b)], [0.0, np.sin(b), np.cos(b)]])
    return Rz @ Rx


O = np.zeros((p, p, G))
for k in range(1, G + 1):
    O[:, :, k - 1] = orient(k)
pars = {"pro": pro, "mean": mu, "variance": {"scale": sc, "shape": sh, "orientation": O}}


def one():
    a = cdensVEV(x, logarithm=True, parameters=pars)
    b = cdensVEV(x, logarithm=False, parameters=pars)
    return np.concatenate([np.asarray(a).ravel(order="F"), np.asarray(b).ravel(order="F")])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
