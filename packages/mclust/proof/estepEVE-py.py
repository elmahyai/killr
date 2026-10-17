import statistics
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from mclust.estep_vee_eve_vve import estep_eve

i = np.arange(1, 13, dtype=float)
x = np.column_stack([np.sin(i), 0.7 * np.cos(i) + 0.1 * i])
mu = np.array([[0.2, -0.4], [1.1, 0.9]])
O = np.array([[np.cos(np.pi / 6), -np.sin(np.pi / 6)], [np.sin(np.pi / 6), np.cos(np.pi / 6)]])
SHAPE = np.array([[1.5, 0.8], [0.6, 1.4]])


def pars(pro, scale, shape):
    return {"pro": np.asarray(pro, dtype=float), "mean": mu, "variance": {"scale": scale, "shape": np.asarray(shape, dtype=float), "orientation": O}}


def one():
    a = estep_eve(x, pars([0.4, 0.6], 0.9, SHAPE))
    b = estep_eve(x, pars([0.3, 0.45, 0.25], 0.9, SHAPE))
    return np.concatenate([a["z"].ravel(order="F"), [a["loglik"]], b["z"].ravel(order="F"), [b["loglik"]]])


value = one()
elapsed = []
for _ in range(20):
    t0 = time.perf_counter()
    one()
    elapsed.append((time.perf_counter() - t0) * 1000)
print("\n".join("%.17g" % v for v in value))
print("%.17g" % statistics.median(elapsed))
